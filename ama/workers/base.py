"""Base Worker Agent interface — standard contract for all worker implementations.

Reference patterns:
  - GenericAgent's BaseHandler (agent_loop.py) — dispatch/turn_end_callback
  - Pi Agent's subagent YAML frontmatter — declarative model/tool assignment
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any


class TaskPriority(IntEnum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


class TaskStatus(IntEnum):
    PENDING = 0
    DECOMPOSING = 1
    ROUTING = 2
    EXECUTING = 3
    REVIEWING = 4
    COMPLETED = 5
    FAILED = 6
    CANCELLED = 7


@dataclass
class TaskInput:
    """Standard task input contract for all workers.

    Every worker receives this as input — no implementation-specific fields.
    """

    task_type: str  # content/code/trading/data/media/commerce
    description: str
    context: dict[str, Any] = field(default_factory=dict)
    task_id: str = field(default_factory=lambda: f"ama-{uuid.uuid4().hex[:8]}")
    budget_yuan: float = 5.0  # max cost allowed for this task
    deadline: datetime | None = None
    priority: TaskPriority = TaskPriority.NORMAL
    complexity: int = 5  # 1-10, used by model router


@dataclass
class TaskOutput:
    """Standard task output contract from all workers.

    Every worker returns this — the Manager uses these fields for QA and ROI calc.
    """

    task_id: str
    result: Any
    success: bool
    model_used: str
    tokens_used: int = 0
    cost_yuan: float = 0.0
    duration_ms: int = 0
    confidence: float = 1.0  # 0-1, worker's self-assessment
    needs_human: bool = False
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkerInfo:
    """Worker registration metadata — populated from workers.json."""

    worker_type: str
    description: str
    supported_task_types: list[str]
    default_model: str
    fallback_model: str | None
    enabled: bool = True
    capability: dict[str, int] = field(default_factory=dict)
    max_retries: int = 3
    timeout_seconds: int = 120


class BaseWorker(ABC):
    """Abstract base for all Worker Agents.

    Each worker is a specialized agent that handles one domain:
      Content, Code, Trading, Data, Media, Commerce

    Lifecycle: validate → execute → (retry on failure) → return TaskOutput
    """

    worker_type: str = "base"
    info: WorkerInfo

    def __init__(self, info: WorkerInfo) -> None:
        self.info = info
        self._total_tasks: int = 0
        self._total_cost: float = 0.0

    @abstractmethod
    async def execute(self, task: TaskInput) -> TaskOutput:
        """Execute the task and return results.

        This is the main method each worker must implement.
        The Manager calls this after routing.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the worker is operational.

        Returns True if the worker can accept tasks.
        Called periodically by Manager for liveness monitoring.
        """
        ...

    def estimate_cost(self, task: TaskInput) -> float:
        """Estimate the cost of executing this task.

        Default: rough token estimate × model pricing.
        Override for workers with non-LLM costs (e.g., external API fees).
        """
        # Rough estimate: 1K input + 2K output per "unit of complexity"
        est_tokens = task.complexity * 3000
        # Assume default model pricing ~0.002/K output tokens
        return round(est_tokens * 0.000002, 4)

    def can_handle(self, task_type: str) -> bool:
        """Check if this worker can handle the given task type."""
        return task_type in self.info.supported_task_types

    def _build_output(
        self,
        task_id: str,
        result: Any,
        success: bool,
        model_used: str = "",
        tokens_used: int = 0,
        cost_yuan: float = 0.0,
        start_time: float = 0.0,
        confidence: float = 1.0,
        needs_human: bool = False,
        error: str | None = None,
        **metadata: Any,
    ) -> TaskOutput:
        """Helper to build a standard TaskOutput with duration tracking."""
        duration_ms = int((time.monotonic() - start_time) * 1000) if start_time > 0 else 0
        self._total_tasks += 1
        self._total_cost += cost_yuan
        return TaskOutput(
            task_id=task_id,
            result=result,
            success=success,
            model_used=model_used,
            tokens_used=tokens_used,
            cost_yuan=cost_yuan,
            duration_ms=duration_ms,
            confidence=confidence,
            needs_human=needs_human,
            error=error,
            metadata=metadata,
        )

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "worker_type": self.worker_type,
            "total_tasks": self._total_tasks,
            "total_cost_yuan": round(self._total_cost, 4),
            "enabled": self.info.enabled,
        }

    def __repr__(self) -> str:
        return f"<{self.worker_type}Worker tasks={self._total_tasks} cost=¥{self._total_cost:.2f}>"
