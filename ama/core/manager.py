"""Manager Agent — central orchestration engine for the AMA system.

The Manager is the brain of the architecture:
  1. Receives tasks → enqueues with priority
  2. Decomposes complex tasks into subtask DAGs
  3. Routes each subtask: model selection → worker dispatch
  4. Reviews outputs → retry on failure (up to max_retries)
  5. Tracks all costs → produces reports

Reference patterns:
  - GenericAgent agentmain.py: GenericAgent class with task queue + LLM rotation
  - GenericAgent frontends/conductor.py: subagent orchestration via conductor_loop()
  - Pi Agent AGENTS.md: FSM routing + subagent dispatch strategies
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Any

from ama.config import get_settings
from ama.core.debate import DebateManager, DebateResult
from ama.core.decomposer import SubTask, TaskDecomposer
from ama.core.reviewer import QualityReviewer, ReviewResult
from ama.core.task_queue import TaskQueue
from ama.router.cost_tracker import CostRecord, CostTracker, DailyReport
from ama.router.model_router import ModelRouter, RouteResult
from ama.workers.base import BaseWorker, TaskInput, TaskOutput, TaskPriority, TaskStatus
from ama.workers.registry import WorkerRegistry

logger = logging.getLogger(__name__)


class ManagerAgent:
    """Central orchestrator for the AMA system.

    Usage:
        manager = ManagerAgent()
        manager.register_workers(registry)

        # Submit a task
        task_id = await manager.submit(
            task_type="writing",
            description="写一篇AI Agent的博客",
            complexity=4,
        )

        # Wait for result
        output = await manager.wait(task_id)

        # Or run interactively
        manager.run_cli()
    """

    def __init__(
        self,
        settings: dict[str, Any] | None = None,
        llm_call=None,
    ) -> None:
        """Initialize the Manager Agent.

        Args:
            settings: Override settings dict. Loads from config/settings.json if None.
            llm_call: Async function for LLM API calls. Used by decomposer.
        """
        self._settings = settings or get_settings()
        mgr_cfg = self._settings.get("manager", {})
        cost_cfg = self._settings.get("cost_control", {})

        # Core components
        self.task_queue = TaskQueue(
            max_size=mgr_cfg.get("task_queue_max_size", 100),
        )
        self.model_router = ModelRouter()
        self.cost_tracker = CostTracker(
            db_path=self._settings.get("database", {}).get(
                "path", "data/ama.db",
            ),
            daily_budget_yuan=cost_cfg.get("daily_budget_yuan", 50.0),
            alert_threshold_yuan=cost_cfg.get("alert_threshold_yuan", 30.0),
        )
        self.decomposer = TaskDecomposer(llm_call=llm_call)
        self.reviewer = QualityReviewer(
            confidence_threshold=mgr_cfg.get("review_confidence_threshold", 0.7),
        )

        # Debate engine (lazy init — created on first debate task)
        self._debate_manager: DebateManager | None = None

        # Worker management
        self.registry: WorkerRegistry | None = None
        self._max_concurrent = mgr_cfg.get("max_concurrent_tasks", 5)
        self._max_retries = mgr_cfg.get("max_retries_per_task", 3)
        self._default_timeout = mgr_cfg.get("default_timeout_seconds", 300)

        # State
        self._running = False
        self._semaphore = asyncio.Semaphore(self._max_concurrent)
        self._results: dict[str, TaskOutput] = {}
        self._futures: dict[str, asyncio.Future] = {}

        logger.info("ManagerAgent initialized (max_concurrent=%d)", self._max_concurrent)

    # ── Public API ──────────────────────────────────────────────

    def register_workers(self, registry: WorkerRegistry) -> None:
        """Register a worker registry with the manager."""
        self.registry = registry
        logger.info("Registered %d workers", len(registry.list_workers()))

    async def submit(
        self,
        task_type: str,
        description: str,
        complexity: int = 5,
        budget_yuan: float = 5.0,
        priority: TaskPriority = TaskPriority.NORMAL,
        context: dict[str, Any] | None = None,
        deadline: datetime | None = None,
    ) -> str:
        """Submit a task to the AMA system. Returns task_id.

        Args:
            task_type: content/code/trading/data/media/commerce
            description: What to do (Chinese or English)
            complexity: 1-10 difficulty estimate
            budget_yuan: Max CNY cost for this task
            priority: CRITICAL/HIGH/NORMAL/LOW/BACKGROUND
            context: Optional extra context for the worker
            deadline: Optional deadline

        Returns:
            task_id for tracking and result retrieval
        """
        task = TaskInput(
            task_type=task_type,
            description=description,
            complexity=complexity,
            budget_yuan=budget_yuan,
            priority=priority,
            context=context or {},
            deadline=deadline,
        )
        task_id = await self.task_queue.put(task)
        logger.info("Task submitted: id=%s type=%s complexity=%d", task_id, task_type, complexity)

        # If manager is running, task will be picked up automatically
        # Otherwise, caller can use process_one() or run()
        return task_id

    async def process_one(self) -> TaskOutput | None:
        """Process a single task from the queue. Returns output or None if empty."""
        task = await self.task_queue.get()
        if task is None:
            return None

        output = await self._execute_task(task)
        self._results[task.task_id] = output
        return output

    async def wait(self, task_id: str, timeout: float = 300) -> TaskOutput:
        """Wait for a task to complete. Raises TimeoutError if exceeded."""
        if task_id in self._results:
            return self._results[task_id]

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._futures[task_id] = future
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._futures.pop(task_id, None)
            raise

    async def run(self, continuous: bool = True) -> None:
        """Run the manager processing loop.

        Args:
            continuous: If True, keep processing until stopped.
                        If False, process all pending tasks and return.
        """
        self._running = True
        logger.info("Manager loop started (continuous=%s)", continuous)

        while self._running:
            task = self.task_queue.get_nowait()
            if task is None:
                if not continuous:
                    break
                await asyncio.sleep(0.1)
                continue

            async with self._semaphore:
                asyncio.create_task(self._process_and_store(task))

        logger.info("Manager loop stopped")

    def stop(self) -> None:
        """Signal the manager to stop processing."""
        self._running = False
        logger.info("Manager stop signal sent")

    # ── Reporting ───────────────────────────────────────────────

    def daily_report(self) -> DailyReport:
        """Get today's cost and performance report."""
        return self.cost_tracker.daily_summary()

    def worker_stats(self, worker_type: str) -> dict[str, Any]:
        """Get stats for a specific worker."""
        return self.cost_tracker.worker_stats(worker_type)

    def queue_status(self) -> dict[str, Any]:
        """Get current queue status."""
        return {
            "pending": self.task_queue.pending,
            "total": self.task_queue.size,
            "is_full": self.task_queue.is_full,
        }

    def system_status(self) -> dict[str, Any]:
        """Get full system status snapshot."""
        budget = self.cost_tracker.check_budget()
        router_stats = {
            "total_routes": self.model_router.stats.total_routes,
            "fallbacks": self.model_router.stats.fallback_triggered,
            "by_model": self.model_router.stats.by_model,
        }
        workers = self.registry.list_workers() if self.registry else []
        return {
            "version": "0.1.0",
            "running": self._running,
            "queue": self.queue_status(),
            "budget": {
                "daily": budget.daily_budget_yuan,
                "spent": budget.spent_today_yuan,
                "remaining": budget.remaining_yuan,
                "percent": budget.percent_used,
                "alert": budget.alert_triggered,
                "downgrade": budget.auto_downgrade,
            },
            "router": router_stats,
            "workers": [w.worker_type for w in workers],
            "models": list(self.model_router.models.keys()),
        }

    def recent_activity(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent task execution records."""
        return self.cost_tracker.all_records(limit=limit)

    # ── Internal: Task Execution Pipeline ────────────────────────

    async def _process_and_store(self, task: TaskInput) -> None:
        """Process a task and store the result."""
        try:
            output = await self._execute_task(task)
        except Exception as exc:
            output = TaskOutput(
                task_id=task.task_id,
                result=None,
                success=False,
                model_used="none",
                error=str(exc),
                needs_human=True,
            )

        self._results[task.task_id] = output
        # Resolve any waiting futures
        future = self._futures.pop(task.task_id, None)
        if future and not future.done():
            future.set_result(output)

    async def _execute_task(self, task: TaskInput) -> TaskOutput:
        """Full execution pipeline for a single task."""
        t0 = time.monotonic()

        # ── Debate task: 特殊路径, 不走 decompose → worker dispatch ──
        if task.task_type == "debate":
            return await self._run_debate(task, t0)

        # 1. Decompose
        subtasks = await self.decomposer.decompose(task)
        logger.info("Task %s decomposed into %d subtasks", task.task_id, len(subtasks))

        # 2. Execute subtasks (respecting dependency order)
        sub_results: dict[int, TaskOutput] = {}
        total_cost = 0.0
        total_tokens = 0

        for subtask in subtasks:
            # Wait for dependencies
            for dep_idx in subtask.depends_on:
                while dep_idx not in sub_results:
                    await asyncio.sleep(0.05)

            # Build context from dependency results
            dep_context = {
                **task.context,
                "_dep_results": {
                    str(d): sub_results[d].result
                    for d in subtask.depends_on
                },
            }

            sub_task = TaskInput(
                task_type=subtask.task_type,
                description=subtask.description,
                complexity=subtask.complexity,
                budget_yuan=task.budget_yuan / max(len(subtasks), 1),
                priority=task.priority,
                context=dep_context,
                deadline=task.deadline,
                task_id=f"{task.task_id}-s{subtask.index}",
            )

            # Execute with retry
            sub_output = await self._execute_with_retry(sub_task)
            sub_results[subtask.index] = sub_output
            total_cost += sub_output.cost_yuan
            total_tokens += sub_output.tokens_used

            if not sub_output.success:
                # A critical subtask failed — fail the whole task
                return TaskOutput(
                    task_id=task.task_id,
                    result={i: r.result for i, r in sub_results.items()},
                    success=False,
                    model_used=sub_output.model_used,
                    tokens_used=total_tokens,
                    cost_yuan=total_cost,
                    duration_ms=int((time.monotonic() - t0) * 1000),
                    confidence=0.0,
                    needs_human=True,
                    error=f"Subtask {subtask.index} failed: {sub_output.error}",
                    metadata={"subtask_results": len(sub_results)},
                )

        # 3. Aggregate results
        agg_result = {
            "subtasks": {
                str(i): {
                    "description": s.description,
                    "result": sub_results[i].result,
                    "success": sub_results[i].success,
                }
                for i, s in enumerate(subtasks)
            },
            "summary": (
                sub_results[0].result
                if len(subtasks) == 1
                else "\n\n".join(
                    str(sub_results[i].result)
                    for i in sorted(sub_results)
                )
            ),
        }

        return TaskOutput(
            task_id=task.task_id,
            result=agg_result,
            success=True,
            model_used=sub_results[0].model_used if subtasks else "none",
            tokens_used=total_tokens,
            cost_yuan=round(total_cost, 6),
            duration_ms=int((time.monotonic() - t0) * 1000),
            confidence=min(
                (r.confidence for r in sub_results.values()),
                default=1.0,
            ),
            needs_human=any(r.needs_human for r in sub_results.values()),
            metadata={"subtask_count": len(subtasks)},
        )

    async def _run_debate(self, task: TaskInput, t0: float) -> TaskOutput:
        """Execute a debate task using the Agent Debate Protocol.

        Task context should contain:
            - topic (str): 辩论议题
            - domain (str): 业务域 (默认 "douyin_compliance")
            - external_data (dict|None): Douyin MCP 等外部数据
            - extra_context (str, optional): 附加上下文

        Returns a TaskOutput with:
            - result: DebateResult (可直接 .to_obsidian_frontmatter())
            - tokens_used: 总 Token 消耗
            - cost_yuan: 总成本 (CNY)
            - metadata: 包含 verdict 摘要和辩论日志路径
        """
        if self._debate_manager is None:
            self._debate_manager = DebateManager(call_llm=self.decomposer._llm_call)
            logger.info("[debate] DebateManager lazy-initialized")

        ctx = task.context or {}
        topic = ctx.get("topic", task.description)
        domain = ctx.get("domain", "douyin_compliance")
        external_data = ctx.get("external_data", None)
        extra_context = ctx.get("extra_context", "")

        logger.info(
            "[debate] Starting debate task %s: domain=%s, topic=%.80s...",
            task.task_id, domain, topic,
        )

        try:
            debate_result: DebateResult = await self._debate_manager.debate(
                topic=topic,
                external_data=external_data,
                domain=domain,
                extra_context=extra_context,
            )
        except Exception as exc:
            logger.exception("[debate] Debate task %s failed", task.task_id)
            return TaskOutput(
                task_id=task.task_id,
                result=None,
                success=False,
                model_used="debate-protocol",
                tokens_used=0,
                cost_yuan=0.0,
                duration_ms=int((time.monotonic() - t0) * 1000),
                confidence=0.0,
                needs_human=True,
                error=str(exc),
                metadata={"debate_error": True},
            )

        verdict_summary = debate_result.verdict.get("final_verdict", "UNKNOWN")
        confidence = debate_result.verdict.get("confidence", 0.0)

        # Record cost in cost tracker
        # Estimate input/output split from all_arguments (total_tokens is aggregate)
        tokens_in = sum(
            a.token_cost.tokens_input for a in debate_result.all_arguments
        )
        tokens_out = debate_result.total_tokens - tokens_in

        self.cost_tracker.record(CostRecord(
            timestamp=datetime.now(),
            task_id=task.task_id,
            worker_type="debate",
            model="debate-protocol",
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            cost_yuan=debate_result.total_cost_yuan,
            duration_ms=int(debate_result.duration_seconds * 1000),
            success=True,
            metadata={
                "verdict": verdict_summary,
                "confidence": confidence,
                "log_path": debate_result.debate_log_path,
            },
        ))

        return TaskOutput(
            task_id=task.task_id,
            result=debate_result,
            success=True,
            model_used="debate-protocol",
            tokens_used=debate_result.total_tokens,
            cost_yuan=debate_result.total_cost_yuan,
            duration_ms=int((time.monotonic() - t0) * 1000),
            confidence=confidence,
            needs_human=debate_result.verdict.get("human_review_required", False),
            metadata={
                "verdict": verdict_summary,
                "risk_level": debate_result.verdict.get("risk_level", "UNKNOWN"),
                "cost_usd": debate_result.total_cost_usd,
                "debate_log_path": debate_result.debate_log_path,
                "obsidian_frontmatter": debate_result.to_obsidian_frontmatter(),
            },
        )

    async def _execute_with_retry(self, task: TaskInput) -> TaskOutput:
        """Execute a single subtask with retry logic."""
        last_output: TaskOutput | None = None

        for attempt in range(1, self._max_retries + 1):
            output = await self._dispatch(task, attempt=attempt)

            # Record cost regardless of success
            self.cost_tracker.record(CostRecord(
                timestamp=datetime.now(),
                task_id=task.task_id,
                worker_type=task.task_type,
                model=output.model_used,
                tokens_input=output.tokens_used // 2,  # estimate
                tokens_output=output.tokens_used // 2,
                cost_yuan=output.cost_yuan,
                duration_ms=output.duration_ms,
                success=output.success,
            ))

            # Review
            review = self.reviewer.review(task, output)
            if review.passed:
                return output

            if not self.reviewer.should_retry(review, attempt, self._max_retries):
                # Escalate to human
                logger.warning(
                    "Task %s needs human review after %d attempts: %s",
                    task.task_id, attempt, review.reason,
                )
                output.needs_human = True
                return output

            logger.info(
                "Retrying task %s (attempt %d/%d): %s",
                task.task_id, attempt + 1, self._max_retries, review.reason,
            )
            last_output = output

        return last_output or TaskOutput(
            task_id=task.task_id,
            result=None,
            success=False,
            model_used="none",
            error="Max retries exceeded",
            needs_human=True,
        )

    async def _dispatch(self, task: TaskInput, attempt: int = 1) -> TaskOutput:
        """Route task to the right model and worker, then execute.

        This is the core dispatch logic:
          1. ModelRouter selects the best model
          2. If budget is tight, force cheap model
          3. WorkerRegistry finds the right worker
          4. Worker executes the task
          5. On failure, try fallback model
        """
        # Check budget before routing
        budget_status = self.cost_tracker.check_budget()
        force_cheap = budget_status.auto_downgrade

        # Route model selection
        if force_cheap:
            route = self.model_router.route(
                task, preferred_model="ollama/qwen2.5:14b",
            )
        else:
            route = self.model_router.route(task)

        # Find worker
        if self.registry is None:
            return TaskOutput(
                task_id=task.task_id,
                result=None,
                success=False,
                model_used=route.model.model_id,
                error="No worker registry registered",
                needs_human=True,
            )

        worker = self.registry.get_worker(task.task_type)
        if worker is None:
            return TaskOutput(
                task_id=task.task_id,
                result=None,
                success=False,
                model_used=route.model.model_id,
                error=f"No worker found for task_type={task.task_type}",
                needs_human=True,
            )

        # Try primary model, then fallback chain
        models_to_try = [route.model.model_id] + route.fallback_chain
        for model_id in models_to_try:
            task.context["_model_id"] = model_id
            task.context["_attempt"] = attempt

            try:
                output = await asyncio.wait_for(
                    worker.execute(task),
                    timeout=self._default_timeout,
                )
                if output.success:
                    return output
                # Worker returned failure — try next model
                logger.warning(
                    "Model %s failed for task %s: %s, trying next",
                    model_id, task.task_id, output.error,
                )
                self.model_router.stats.fallback_triggered += 1
            except asyncio.TimeoutError:
                logger.error("Task %s timed out with model %s", task.task_id, model_id)
                continue
            except Exception as exc:
                logger.error("Task %s error with model %s: %s", task.task_id, model_id, exc)
                continue

        # All models exhausted
        return TaskOutput(
            task_id=task.task_id,
            result=None,
            success=False,
            model_used=route.model.model_id,
            error="All models exhausted",
            needs_human=True,
        )
