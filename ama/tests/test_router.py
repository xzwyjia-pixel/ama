"""Tests for model router and cost tracker."""

import pytest
from datetime import datetime, date

from ama.router.model_router import ModelRouter, RouteResult
from ama.router.cost_tracker import CostTracker, CostRecord, DailyReport
from ama.workers.base import TaskInput, TaskPriority


class TestModelRouter:
    """Model router tests."""

    def test_initialization(self):
        router = ModelRouter()
        assert len(router.models) >= 2
        assert "ollama/qwen2.5:14b" in router.models
        assert "deepseek/pro-1m" in router.models

    def test_simple_task_routes_to_cheapest(self):
        router = ModelRouter()
        task = TaskInput(
            task_type="writing",
            description="简单翻译任务",
            complexity=2,  # simple → should route to Ollama
        )
        result = router.route(task)
        assert result.model.model_id == "ollama/qwen2.5:14b"
        assert result.estimated_cost_yuan == 0.0

    def test_complex_task_routes_to_capable(self):
        router = ModelRouter()
        task = TaskInput(
            task_type="coding",
            description="复杂系统架构设计",
            complexity=9,  # complex → need Pro 1M
        )
        result = router.route(task)
        assert result.model.model_id == "deepseek/pro-1m"
        assert result.estimated_cost_yuan > 0.0

    def test_medium_task_routes_to_flash(self):
        router = ModelRouter()
        task = TaskInput(
            task_type="writing",
            description="中等复杂度文章写作",
            complexity=5,
        )
        result = router.route(task)
        # Should route to flash (capable enough, cheaper than pro)
        assert "flash" in result.model.model_id or "ollama" in result.model.model_id

    def test_preferred_model_override(self):
        router = ModelRouter()
        task = TaskInput(
            task_type="writing",
            description="test",
            complexity=2,
        )
        result = router.route(task, preferred_model="deepseek/pro-1m")
        assert result.model.model_id == "deepseek/pro-1m"

    def test_fallback_chain(self):
        router = ModelRouter()
        task = TaskInput(
            task_type="writing",
            description="test",
            complexity=5,
        )
        result = router.route(task)
        assert len(result.fallback_chain) > 0

    def test_get_model(self):
        router = ModelRouter()
        model = router.get_model("ollama/qwen2.5:14b")
        assert model is not None
        assert model.model_type == "local"
        assert model.cost_per_1k_input == 0.0


class TestCostTracker:
    """Cost tracker tests."""

    def test_record_and_retrieve(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        tracker = CostTracker(db_path=db_path)

        record = CostRecord(
            timestamp=datetime.now(),
            task_id="test-001",
            worker_type="content",
            model="deepseek/flash",
            tokens_input=1000,
            tokens_output=500,
            cost_yuan=0.003,
            duration_ms=1500,
            success=True,
        )
        tracker.record(record)

        cost = tracker.task_cost("test-001")
        assert cost == 0.003

    def test_daily_summary(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        tracker = CostTracker(db_path=db_path)

        tracker.record(CostRecord(
            timestamp=datetime.now(), task_id="t1", worker_type="content",
            model="deepseek/flash", tokens_input=500, tokens_output=500,
            cost_yuan=0.002, duration_ms=1000, success=True,
        ))
        tracker.record(CostRecord(
            timestamp=datetime.now(), task_id="t2", worker_type="code",
            model="deepseek/pro-1m", tokens_input=2000, tokens_output=3000,
            cost_yuan=0.075, duration_ms=3000, success=True,
        ))

        report = tracker.daily_summary()
        assert report.total_tasks == 2
        assert report.successful_tasks == 2
        assert report.total_cost_yuan == 0.077
        assert "content" in report.by_worker
        assert "code" in report.by_worker

    def test_budget_check(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        tracker = CostTracker(
            db_path=db_path,
            daily_budget_yuan=10.0,
            alert_threshold_yuan=5.0,
        )

        # Under threshold
        status = tracker.check_budget()
        assert not status.alert_triggered
        assert not status.auto_downgrade

        # Record enough to trigger alert
        tracker.record(CostRecord(
            timestamp=datetime.now(), task_id="t1", worker_type="code",
            model="deepseek/pro-1m", tokens_input=100000, tokens_output=100000,
            cost_yuan=6.0, duration_ms=1000, success=True,
        ))

        status = tracker.check_budget()
        assert status.alert_triggered
        assert status.percent_used >= 50.0

    def test_all_records(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        tracker = CostTracker(db_path=db_path)

        for i in range(5):
            tracker.record(CostRecord(
                timestamp=datetime.now(), task_id=f"t{i}",
                worker_type="content", model="deepseek/flash",
                tokens_input=100, tokens_output=100,
                cost_yuan=0.001, duration_ms=500, success=True,
            ))

        records = tracker.all_records(limit=3)
        assert len(records) == 3
