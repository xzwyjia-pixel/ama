"""Tests for worker implementations."""

import asyncio
import pytest

from ama.workers.base import TaskInput, TaskOutput, WorkerInfo, BaseWorker
from ama.workers.registry import WorkerRegistry


# ── Test Helpers ─────────────────────────────────────────────

class MockWorker(BaseWorker):
    """Mock worker for testing."""
    worker_type = "mock"

    async def execute(self, task: TaskInput) -> TaskOutput:
        return self._build_output(
            task_id=task.task_id,
            result=f"Mock result: {task.description}",
            success=True,
            model_used="mock/model",
            tokens_used=100,
            cost_yuan=0.001,
        )

    async def health_check(self) -> bool:
        return True


class FailingWorker(BaseWorker):
    """Mock worker that always fails."""
    worker_type = "failing"

    async def execute(self, task: TaskInput) -> TaskOutput:
        return self._build_output(
            task_id=task.task_id,
            result=None,
            success=False,
            model_used="mock/model",
            error="Simulated failure",
            needs_human=True,
        )

    async def health_check(self) -> bool:
        return False


# ── Tests ────────────────────────────────────────────────────

class TestBaseWorker:
    """BaseWorker interface tests."""

    @pytest.mark.asyncio
    async def test_mock_worker_execute(self):
        info = WorkerInfo(
            worker_type="mock",
            description="Test mock worker",
            supported_task_types=["writing", "coding"],
            default_model="mock/model",
            fallback_model=None,
        )
        worker = MockWorker(info)
        task = TaskInput(
            task_type="writing",
            description="Hello world",
            complexity=5,
        )
        output = await worker.execute(task)
        assert output.success
        assert output.task_id == task.task_id
        assert "Hello world" in str(output.result)

    @pytest.mark.asyncio
    async def test_failing_worker(self):
        info = WorkerInfo(
            worker_type="failing",
            description="Always fails",
            supported_task_types=["coding"],
            default_model="mock/model",
            fallback_model=None,
        )
        worker = FailingWorker(info)
        task = TaskInput(
            task_type="coding",
            description="Write code",
            complexity=5,
        )
        output = await worker.execute(task)
        assert not output.success
        assert output.error == "Simulated failure"
        assert output.needs_human

    def test_can_handle(self):
        info = WorkerInfo(
            worker_type="mock",
            description="Test",
            supported_task_types=["writing", "translation"],
            default_model="mock/model",
            fallback_model=None,
        )
        worker = MockWorker(info)
        assert worker.can_handle("writing")
        assert worker.can_handle("translation")
        assert not worker.can_handle("coding")

    def test_estimate_cost(self):
        info = WorkerInfo(
            worker_type="mock",
            description="Test",
            supported_task_types=["writing"],
            default_model="deepseek/flash",
            fallback_model=None,
        )
        worker = MockWorker(info)
        task = TaskInput(task_type="writing", description="test", complexity=8)
        cost = worker.estimate_cost(task)
        assert cost > 0.0

    def test_stats_tracking(self):
        info = WorkerInfo(
            worker_type="mock",
            description="Test",
            supported_task_types=["writing"],
            default_model="mock/model",
            fallback_model=None,
        )
        worker = MockWorker(info)
        assert worker.stats["total_tasks"] == 0
        assert worker.stats["total_cost_yuan"] == 0.0


class TestWorkerRegistry:
    """WorkerRegistry tests."""

    def test_register_and_lookup(self):
        registry = WorkerRegistry()
        info = WorkerInfo(
            worker_type="content",
            description="Content worker",
            supported_task_types=["writing", "translation", "summary"],
            default_model="deepseek/flash",
            fallback_model="ollama/qwen2.5:14b",
        )
        worker = MockWorker(info)
        worker.worker_type = "content"

        registry.register("content", worker)
        assert registry.worker_count == 1

        found = registry.get_worker("writing")
        assert found is not None
        assert found.worker_type == "content"

        found2 = registry.get_worker("translation")
        assert found2 is not None

        not_found = registry.get_worker("coding")
        assert not_found is None

    def test_unregister(self):
        registry = WorkerRegistry()
        info = WorkerInfo(
            worker_type="content",
            description="Content",
            supported_task_types=["writing"],
            default_model="deepseek/flash",
            fallback_model=None,
        )
        worker = MockWorker(info)
        worker.worker_type = "content"
        registry.register("content", worker)
        assert registry.worker_count == 1

        removed = registry.unregister("content")
        assert removed
        assert registry.worker_count == 0
        assert registry.get_worker("writing") is None

    def test_list_workers(self):
        registry = WorkerRegistry()
        info = WorkerInfo(
            worker_type="content", description="C",
            supported_task_types=["writing"],
            default_model="m", fallback_model=None,
        )
        registry.register("content", MockWorker(info))

        workers = registry.list_workers()
        assert len(workers) == 1


class TestTaskInputOutput:
    """Data model tests."""

    def test_task_input_defaults(self):
        task = TaskInput(
            task_type="writing",
            description="Test task",
        )
        assert task.task_id.startswith("ama-")
        assert task.complexity == 5  # default
        assert task.budget_yuan == 5.0
        assert task.priority.value == 3  # NORMAL

    def test_task_output_creation(self):
        output = TaskOutput(
            task_id="test-123",
            result="Result text",
            success=True,
            model_used="deepseek/flash",
            tokens_used=1500,
            cost_yuan=0.003,
            duration_ms=2000,
        )
        assert output.success
        assert output.model_used == "deepseek/flash"
        assert output.cost_yuan == 0.003
        assert output.confidence == 1.0
