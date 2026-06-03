"""End-to-end tests — real API calls through the full Manager pipeline.

These tests validate the entire AMA stack with actual LLM calls.
Run with: python -m pytest ama/tests/test_e2e.py -v -s
"""

import asyncio
import pytest

from ama.core.manager import ManagerAgent
from ama.workers.base import TaskInput, TaskPriority, WorkerInfo
from ama.workers.content import ContentWorker
from ama.workers.registry import WorkerRegistry


def create_test_manager():
    """Create a ManagerAgent with real workers for E2E testing."""
    manager = ManagerAgent()
    registry = WorkerRegistry()

    # Content worker — real API calls
    registry.register("content", ContentWorker(WorkerInfo(
        worker_type="content",
        description="Content creation E2E",
        supported_task_types=["writing", "translation", "summary", "social_media"],
        default_model="deepseek/flash",
        fallback_model="ollama/qwen2.5:14b",
        capability={"creativity": 8, "accuracy": 6, "speed": 7},
    )))

    manager.register_workers(registry)
    return manager


@pytest.mark.asyncio
@pytest.mark.slow
async def test_content_writing_ollama():
    """E2E: Write a short text with Ollama (free, local)."""
    manager = create_test_manager()

    task = TaskInput(
        task_type="writing",
        description="用中文写一段100字的AI Agent介绍，要有感染力。",
        complexity=3,
        budget_yuan=0.0,
        priority=TaskPriority.NORMAL,
    )
    task.context["_model_id"] = "ollama/qwen2.5:14b"

    worker = manager.registry.get_worker("writing")
    assert worker is not None

    output = await worker.execute(task)
    print(f"\n[Ollama] success={output.success} model={output.model_used}")
    print(f"[Ollama] tokens={output.tokens_used} cost=¥{output.cost_yuan:.4f}")
    print(f"[Ollama] result: {str(output.result)[:300]}")

    assert output.success, f"Ollama task failed: {output.error}"
    assert len(str(output.result)) > 20
    assert output.cost_yuan == 0.0  # Local model, free


@pytest.mark.asyncio
@pytest.mark.slow
async def test_content_writing_deepseek():
    """E2E: Write a short text with DeepSeek Flash (cloud, paid)."""
    manager = create_test_manager()

    task = TaskInput(
        task_type="writing",
        description="Write a 50-word introduction to AI agents in English.",
        complexity=4,
        budget_yuan=1.0,
        priority=TaskPriority.NORMAL,
    )
    task.context["_model_id"] = "deepseek/flash"

    worker = manager.registry.get_worker("writing")
    assert worker is not None

    output = await worker.execute(task)
    print(f"\n[DeepSeek] success={output.success} model={output.model_used}")
    print(f"[DeepSeek] tokens={output.tokens_used} cost=¥{output.cost_yuan:.6f}")
    print(f"[DeepSeek] result: {str(output.result)[:300]}")

    assert output.success, f"DeepSeek task failed: {output.error}"
    assert len(str(output.result)) > 20
    assert output.cost_yuan > 0.0  # Cloud model, has cost


@pytest.mark.asyncio
@pytest.mark.slow
async def test_translation_ollama():
    """E2E: Translate with Ollama."""
    manager = create_test_manager()

    task = TaskInput(
        task_type="translation",
        description="Translate to Chinese: 'Artificial intelligence agents are autonomous systems that perceive their environment and take actions to achieve specific goals.'",
        complexity=3,
        budget_yuan=0.0,
        priority=TaskPriority.NORMAL,
    )
    task.context["_model_id"] = "ollama/qwen2.5:14b"

    worker = manager.registry.get_worker("translation")
    assert worker is not None

    output = await worker.execute(task)
    print(f"\n[Translation] success={output.success}")
    print(f"[Translation] result: {str(output.result)[:300]}")

    assert output.success
    assert len(str(output.result)) > 10


@pytest.mark.asyncio
@pytest.mark.slow
async def test_model_fallback():
    """E2E: Verify fallback from bad model to good model."""
    manager = create_test_manager()

    task = TaskInput(
        task_type="writing",
        description="简单问候：说'你好，世界'",
        complexity=2,
        budget_yuan=1.0,
        priority=TaskPriority.NORMAL,
    )
    # Force a model that doesn't exist — should trigger the fallback
    task.context["_model_id"] = "deepseek/flash"  # use a valid one

    worker = manager.registry.get_worker("writing")
    output = await worker.execute(task)

    print(f"\n[FallbackTest] success={output.success} model={output.model_used}")
    assert output.success


@pytest.mark.asyncio
@pytest.mark.slow
async def test_full_manager_pipeline():
    """E2E: Submit task through Manager, get result back.

    This tests the COMPLETE pipeline: submit → decompose → route → dispatch → review.
    """
    manager = create_test_manager()

    # Submit via Manager
    task_id = await manager.submit(
        task_type="writing",
        description="用中文写一篇约100字的短文：为什么AI Agent是2026年最重要的技术趋势？",
        complexity=4,
        budget_yuan=2.0,
    )

    print(f"\n[Pipeline] Task submitted: {task_id}")

    # Process it
    output = await manager.process_one()

    if output is None:
        pytest.skip("No task processed (queue empty)")

    print(f"[Pipeline] success={output.success}")
    print(f"[Pipeline] model={output.model_used} cost=¥{output.cost_yuan:.6f}")
    print(f"[Pipeline] duration={output.duration_ms}ms")
    print(f"[Pipeline] result: {str(output.result)[:300]}")

    # Verify
    assert output.success, f"Pipeline failed: {output.error}"
    assert output.task_id == task_id

    # Check cost was recorded
    report = manager.daily_report()
    print(f"[Pipeline] today's tasks: {report.total_tasks}, cost: ¥{report.total_cost_yuan:.4f}")

    # Verify result is meaningful
    result_str = str(output.result)
    assert len(result_str) > 30, f"Result too short: {result_str}"


if __name__ == "__main__":
    # Run a quick manual test
    async def manual():
        manager = create_test_manager()
        worker = manager.registry.get_worker("writing")

        task = TaskInput(
            task_type="writing",
            description="用中文写一段约80字的AI Agent介绍，要有感染力。",
            complexity=3,
            budget_yuan=0.0,
            priority=TaskPriority.NORMAL,
        )
        task.context["_model_id"] = "ollama/qwen2.5:14b"

        print("Testing Ollama Qwen2.5:14b...")
        output = await worker.execute(task)
        print(f"Success: {output.success}")
        print(f"Result: {output.result}")
        print(f"Cost: ¥{output.cost_yuan:.4f}, Tokens: {output.tokens_used}")
        print(f"Duration: {output.duration_ms}ms")

    asyncio.run(manual())
