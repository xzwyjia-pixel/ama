"""Tests for Manager Agent core engine."""

import asyncio
import pytest

from ama.core.manager import ManagerAgent
from ama.core.task_queue import TaskQueue
from ama.workers.base import TaskInput, TaskPriority, TaskStatus


class TestTaskQueue:
    """Task queue tests."""

    @pytest.mark.asyncio
    async def test_put_get(self):
        queue = TaskQueue(max_size=10)
        task = TaskInput(
            task_type="writing",
            description="测试任务",
            complexity=3,
        )
        task_id = await queue.put(task)
        assert task_id.startswith("ama-")

        retrieved = await queue.get()
        assert retrieved is not None
        assert retrieved.task_type == "writing"
        assert retrieved.description == "测试任务"

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        queue = TaskQueue(max_size=10)
        low = TaskInput(task_type="writing", description="low",
                        priority=TaskPriority.LOW, complexity=1)
        high = TaskInput(task_type="coding", description="high",
                         priority=TaskPriority.HIGH, complexity=5)
        critical = TaskInput(task_type="trading", description="critical",
                            priority=TaskPriority.CRITICAL, complexity=8)

        await queue.put(low)
        await queue.put(high)
        await queue.put(critical)

        # Should get critical first
        first = await queue.get()
        assert first is not None
        assert first.priority == TaskPriority.CRITICAL

    @pytest.mark.asyncio
    async def test_status_tracking(self):
        queue = TaskQueue(max_size=10)
        task = TaskInput(task_type="writing", description="test", complexity=1)
        task_id = await queue.put(task)
        assert queue.get_status(task_id) == TaskStatus.PENDING

        retrieved = await queue.get()
        assert retrieved is not None
        assert queue.get_status(task_id) == TaskStatus.EXECUTING

    @pytest.mark.asyncio
    async def test_max_size(self):
        queue = TaskQueue(max_size=3)
        for i in range(3):
            await queue.put(TaskInput(
                task_type="writing", description=f"task-{i}", complexity=1,
            ))
        assert queue.is_full
        # Getting one should make room
        await queue.get()
        assert not queue.is_full


class TestManager:
    """Manager integration tests."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        manager = ManagerAgent()
        assert manager.task_queue is not None
        assert manager.model_router is not None
        assert manager.cost_tracker is not None
        assert manager.reviewer is not None

    @pytest.mark.asyncio
    async def test_system_status(self):
        manager = ManagerAgent()
        status = manager.system_status()
        assert status["version"] == "0.1.0"
        assert "queue" in status
        assert "budget" in status
        assert "router" in status

    @pytest.mark.asyncio
    async def test_submit_task(self):
        manager = ManagerAgent()
        from ama.workers.registry import WorkerRegistry
        from ama.workers.base import WorkerInfo

        # Register a dummy worker
        registry = WorkerRegistry()

        task_id = await manager.submit(
            task_type="writing",
            description="测试任务提交",
            complexity=3,
        )
        assert task_id.startswith("ama-")
        assert manager.task_queue.pending == 1
