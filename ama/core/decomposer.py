"""Task Decomposer — LLM-driven breakdown of complex tasks into subtask DAGs.

For simple tasks (complexity <= 3), decomposition is a no-op.
For complex tasks, the decomposer uses a fast LLM call to break the task
into ordered subtasks with dependencies.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from ama.workers.base import TaskInput, TaskPriority

logger = logging.getLogger(__name__)


@dataclass
class SubTask:
    """A single decomposed subtask."""
    index: int
    task_type: str
    description: str
    complexity: int  # 1-10
    depends_on: list[int] = field(default_factory=list)  # indices of prerequisite subtasks
    estimated_tokens: int = 2000
    priority: TaskPriority = TaskPriority.NORMAL


DECOMPOSE_SYSTEM_PROMPT = """You are a task decomposition engine. Break down user requests into ordered subtasks.

Output a JSON array of subtasks. Each subtask:
- "index": sequential number (0-based)
- "task_type": one of [writing, translation, summary, social_media, coding, debugging, testing,
   deployment, market_analysis, trading_signal, risk_assessment, scraping, cleaning, analysis,
   reporting, image_gen, video_gen, audio_gen, customer_service, listing, pricing, order]
- "description": clear Chinese description of what to do
- "complexity": 1-10 (1=trivial, 5=moderate, 10=extremely hard)
- "depends_on": list of subtask indices that must complete first (empty if independent)
- "estimated_tokens": rough token estimate (500-10000)

Rules:
1. Identify the highest-value subtask and put it first
2. Mark independent subtasks with empty depends_on (they can run in parallel)
3. Each subtask should be self-contained and verifiable
4. Total subtasks: 1-5 (don't over-decompose simple tasks)
5. Respond ONLY with the JSON array, no other text."""


class TaskDecomposer:
    """LLM-powered task decomposition.

    Usage:
        decomposer = TaskDecomposer(llm_call=my_llm_func)
        subtasks = await decomposer.decompose(task)
    """

    def __init__(self, llm_call=None) -> None:
        """Initialize with an async LLM call function.

        llm_call(prompt: str, system: str, json_mode: bool) -> str
        """
        self._llm_call = llm_call

    async def decompose(self, task: TaskInput) -> list[SubTask]:
        """Break a task into ordered subtasks.

        Simple tasks (complexity <= 3) return as a single subtask.
        Complex tasks get full LLM-driven decomposition.
        """
        # Simple tasks: no decomposition needed
        if task.complexity <= 3:
            return [
                SubTask(
                    index=0,
                    task_type=task.task_type,
                    description=task.description,
                    complexity=task.complexity,
                    depends_on=[],
                )
            ]

        # Complex tasks: use LLM to decompose
        if self._llm_call is None:
            # No LLM available — treat as single task
            logger.warning("No LLM call configured, treating as single task")
            return [
                SubTask(
                    index=0,
                    task_type=task.task_type,
                    description=task.description,
                    complexity=task.complexity,
                    depends_on=[],
                )
            ]

        try:
            prompt = (
                f"Task type: {task.task_type}\n"
                f"Complexity: {task.complexity}/10\n"
                f"Description: {task.description}\n"
                f"Context: {json.dumps(task.context, ensure_ascii=False) if task.context else 'None'}\n\n"
                f"Decompose this task into subtasks."
            )
            response = await self._llm_call(
                prompt=prompt,
                system=DECOMPOSE_SYSTEM_PROMPT,
                json_mode=True,
            )
            raw = json.loads(response)
            subtasks = [
                SubTask(
                    index=s["index"],
                    task_type=s["task_type"],
                    description=s["description"],
                    complexity=s.get("complexity", 5),
                    depends_on=s.get("depends_on", []),
                    estimated_tokens=s.get("estimated_tokens", 2000),
                )
                for s in raw
            ]
            # Sort by dependencies (topological-ish: index order)
            subtasks.sort(key=lambda s: s.index)
            logger.info(
                "Decomposed task %s into %d subtasks: %s",
                task.task_id, len(subtasks),
                [s.description[:40] for s in subtasks],
            )
            return subtasks

        except Exception as e:
            logger.error("Decomposition failed: %s, treating as single task", e)
            return [
                SubTask(
                    index=0,
                    task_type=task.task_type,
                    description=task.description,
                    complexity=task.complexity,
                    depends_on=[],
                )
            ]

    def simple_decompose(self, task: TaskInput) -> list[SubTask]:
        """Non-LLM decomposition based on task_type heuristics.

        Used as fallback when no LLM is available.
        """
        # For known task types, apply simple heuristic decomposition
        if task.task_type in ("writing", "translation", "summary", "social_media"):
            return [
                SubTask(0, task.task_type, task.description, task.complexity, []),
            ]
        elif task.task_type in ("market_analysis", "trading_signal", "risk_assessment"):
            return [
                SubTask(0, "analysis", f"分析: {task.description}", max(3, task.complexity - 2), []),
                SubTask(1, task.task_type, f"生成: {task.description}", task.complexity, [0]),
            ]
        elif task.task_type in ("coding", "debugging", "testing", "deployment"):
            return [
                SubTask(0, "analysis", f"分析需求: {task.description}", 3, []),
                SubTask(1, task.task_type, f"执行: {task.description}", task.complexity, [0]),
                SubTask(2, "testing", f"验证: {task.description}", 3, [1]),
            ]
        else:
            return [
                SubTask(0, task.task_type, task.description, task.complexity, []),
            ]
