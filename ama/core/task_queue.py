"""Priority task queue with asyncio support.

Tasks are ordered by (priority, insertion_time) — critical tasks first.
"""

from __future__ import annotations

import asyncio
import heapq
import itertools
import time
from dataclasses import dataclass, field
from typing import Any

from ama.workers.base import TaskInput, TaskPriority, TaskStatus


@dataclass(order=True)
class _QueueEntry:
    """Internal queue entry with priority ordering."""
    priority: int
    counter: int
    task: TaskInput = field(compare=False)
    status: TaskStatus = field(default=TaskStatus.PENDING, compare=False)
    enqueued_at: float = field(default_factory=time.monotonic, compare=False)
    result: Any = field(default=None, compare=False)
    error: str | None = field(default=None, compare=False)

    @property
    def task_id(self) -> str:
        return self.task.task_id


class TaskQueue:
    """asyncio-compatible priority task queue.

    Usage:
        queue = TaskQueue(max_size=100)
        await queue.put(task)
        task = await queue.get()
        queue.mark_done(task_id, status=TaskStatus.COMPLETED)
    """

    def __init__(self, max_size: int = 100) -> None:
        self.max_size = max_size
        self._heap: list[_QueueEntry] = []
        self._counter = itertools.count()
        self._by_id: dict[str, _QueueEntry] = {}
        self._not_empty = asyncio.Event()
        self._not_full = asyncio.Event()
        self._not_full.set()

    async def put(self, task: TaskInput) -> str:
        """Add a task to the queue. Returns task_id.

        Blocks if the queue is full.
        """
        while len(self._heap) >= self.max_size:
            self._not_full.clear()
            await self._not_full.wait()

        entry = _QueueEntry(
            priority=int(task.priority),
            counter=next(self._counter),
            task=task,
        )
        heapq.heappush(self._heap, entry)
        self._by_id[task.task_id] = entry
        self._not_empty.set()
        return task.task_id

    async def get(self) -> TaskInput | None:
        """Get the next task (highest priority). Blocks if empty."""
        while not self._heap:
            self._not_empty.clear()
            await self._not_empty.wait()

        entry = heapq.heappop(self._heap)
        entry.status = TaskStatus.EXECUTING
        self._not_full.set()
        return entry.task

    def get_nowait(self) -> TaskInput | None:
        """Get next task without blocking. Returns None if empty."""
        if not self._heap:
            return None
        entry = heapq.heappop(self._heap)
        entry.status = TaskStatus.EXECUTING
        self._not_full.set()
        return entry.task

    def update_status(self, task_id: str, status: TaskStatus,
                      result: Any = None, error: str | None = None) -> None:
        """Update the status of a task in the queue."""
        entry = self._by_id.get(task_id)
        if entry:
            entry.status = status
            entry.result = result
            entry.error = error

    def get_status(self, task_id: str) -> TaskStatus | None:
        """Get the current status of a task."""
        entry = self._by_id.get(task_id)
        return entry.status if entry else None

    def get_result(self, task_id: str) -> Any:
        """Get the result of a completed task."""
        entry = self._by_id.get(task_id)
        return entry.result if entry else None

    def remove(self, task_id: str) -> bool:
        """Remove a task from the queue. Returns True if found."""
        entry = self._by_id.pop(task_id, None)
        if entry:
            entry.status = TaskStatus.CANCELLED
            # Rebuild heap without this entry
            self._heap = [e for e in self._heap if e.task.task_id != task_id]
            heapq.heapify(self._heap)
            return True
        return False

    @property
    def size(self) -> int:
        return len(self._heap)

    @property
    def pending(self) -> int:
        return sum(1 for e in self._heap if e.status == TaskStatus.PENDING)

    @property
    def is_empty(self) -> bool:
        return len(self._heap) == 0

    @property
    def is_full(self) -> bool:
        return len(self._heap) >= self.max_size

    def list_tasks(self) -> list[dict[str, Any]]:
        """List all tasks with status."""
        all_entries = list(self._heap) + [
            e for e in self._by_id.values()
            if e.status not in (TaskStatus.PENDING,)
        ]
        return [
            {
                "task_id": e.task_id,
                "task_type": e.task.task_type,
                "description": e.task.description[:80],
                "priority": e.task.priority,
                "status": e.status.name,
                "enqueued_at": e.enqueued_at,
            }
            for e in sorted(all_entries, key=lambda x: x.enqueued_at, reverse=True)
        ]
