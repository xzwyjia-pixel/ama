"""Cost Tracker — per-task, per-worker, daily cost aggregation.

Reference patterns:
  - GenericAgent frontends/cost_tracker.py — token usage tracking via llmcore patches
  - Pi Agent settings.json — cost_control settings (daily_budget, alert_threshold)

Features:
  - Token counting per task
  - CNY cost conversion based on model pricing
  - Per-task, per-worker, daily aggregation
  - Budget alerts and auto-downgrade signals
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CostRecord:
    """Single cost entry for one task execution."""

    timestamp: datetime
    task_id: str
    worker_type: str
    model: str
    tokens_input: int
    tokens_output: int
    cost_yuan: float
    duration_ms: int
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DailyReport:
    """Daily cost summary."""

    date: str
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    total_tokens: int
    total_cost_yuan: float
    by_worker: dict[str, dict[str, Any]]  # worker_type → {tasks, cost, tokens}
    by_model: dict[str, dict[str, Any]]  # model → {tasks, cost, tokens}


@dataclass
class BudgetStatus:
    """Current budget consumption status."""

    daily_budget_yuan: float
    spent_today_yuan: float
    remaining_yuan: float
    percent_used: float
    alert_triggered: bool
    auto_downgrade: bool  # whether to force local/cheap models


class CostTracker:
    """Token and cost tracking with SQLite persistence.

    Usage:
        tracker = CostTracker(db_path="data/ama.db")
        tracker.record(task_id="...", worker_type="content",
                       model="deepseek/flash", tokens_in=1000, tokens_out=500)
        report = tracker.daily_summary()
    """

    def __init__(
        self,
        db_path: str = "c:/Users/25454/业务中控台/ama/data/ama.db",
        daily_budget_yuan: float = 50.0,
        alert_threshold_yuan: float = 30.0,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.daily_budget = daily_budget_yuan
        self.alert_threshold = alert_threshold_yuan
        self._init_db()

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cost_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    worker_type TEXT NOT NULL,
                    model TEXT NOT NULL,
                    tokens_input INTEGER DEFAULT 0,
                    tokens_output INTEGER DEFAULT 0,
                    cost_yuan REAL DEFAULT 0.0,
                    duration_ms INTEGER DEFAULT 0,
                    success INTEGER DEFAULT 1,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cost_task_id ON cost_records(task_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cost_date ON cost_records(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cost_worker ON cost_records(worker_type)
            """)
            conn.commit()

    def record(self, record: CostRecord) -> None:
        """Persist a cost record to the database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """INSERT INTO cost_records
                   (timestamp, task_id, worker_type, model, tokens_input,
                    tokens_output, cost_yuan, duration_ms, success, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.timestamp.isoformat(),
                    record.task_id,
                    record.worker_type,
                    record.model,
                    record.tokens_input,
                    record.tokens_output,
                    record.cost_yuan,
                    record.duration_ms,
                    1 if record.success else 0,
                    json.dumps(record.metadata, ensure_ascii=False),
                ),
            )
            conn.commit()
        logger.debug(
            "Cost record: task=%s worker=%s model=%s ¥%.4f (%d tokens)",
            record.task_id, record.worker_type, record.model,
            record.cost_yuan, record.tokens_input + record.tokens_output,
        )

    def task_cost(self, task_id: str) -> float:
        """Get total cost for a specific task."""
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT SUM(cost_yuan) FROM cost_records WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            return row[0] or 0.0

    def daily_summary(self, target_date: date | None = None) -> DailyReport:
        """Aggregate costs for a given day (default: today)."""
        if target_date is None:
            target_date = date.today()
        date_str = target_date.isoformat()

        with sqlite3.connect(str(self.db_path)) as conn:
            # Totals
            row = conn.execute(
                """SELECT COUNT(*),
                          SUM(CASE WHEN success=1 THEN 1 ELSE 0 END),
                          SUM(CASE WHEN success=0 THEN 1 ELSE 0 END),
                          SUM(tokens_input + tokens_output),
                          SUM(cost_yuan)
                   FROM cost_records
                   WHERE date(timestamp) = ?""",
                (date_str,),
            ).fetchone()

            # By worker
            worker_rows = conn.execute(
                """SELECT worker_type,
                          COUNT(*), SUM(cost_yuan),
                          SUM(tokens_input + tokens_output)
                   FROM cost_records
                   WHERE date(timestamp) = ?
                   GROUP BY worker_type""",
                (date_str,),
            ).fetchall()

            # By model
            model_rows = conn.execute(
                """SELECT model,
                          COUNT(*), SUM(cost_yuan),
                          SUM(tokens_input + tokens_output)
                   FROM cost_records
                   WHERE date(timestamp) = ?
                   GROUP BY model""",
                (date_str,),
            ).fetchall()

        by_worker = {}
        for w_type, tasks, cost, tokens in worker_rows:
            by_worker[w_type] = {
                "tasks": tasks, "cost_yuan": round(cost or 0, 4),
                "tokens": tokens or 0,
            }

        by_model = {}
        for model, tasks, cost, tokens in model_rows:
            by_model[model] = {
                "tasks": tasks, "cost_yuan": round(cost or 0, 4),
                "tokens": tokens or 0,
            }

        return DailyReport(
            date=date_str,
            total_tasks=row[0] or 0,
            successful_tasks=row[1] or 0,
            failed_tasks=row[2] or 0,
            total_tokens=row[3] or 0,
            total_cost_yuan=round(row[4] or 0, 4),
            by_worker=by_worker,
            by_model=by_model,
        )

    def check_budget(self) -> BudgetStatus:
        """Check current budget consumption and determine if alerts should fire."""
        today = self.daily_summary()
        spent = today.total_cost_yuan
        remaining = max(0, self.daily_budget - spent)
        percent = (spent / self.daily_budget * 100) if self.daily_budget > 0 else 0
        alert = spent >= self.alert_threshold
        downgrade = spent >= self.daily_budget

        return BudgetStatus(
            daily_budget_yuan=self.daily_budget,
            spent_today_yuan=spent,
            remaining_yuan=remaining,
            percent_used=round(percent, 1),
            alert_triggered=alert,
            auto_downgrade=downgrade,
        )

    def worker_stats(self, worker_type: str, days: int = 7) -> dict[str, Any]:
        """Get stats for a specific worker over the last N days."""
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                """SELECT COUNT(*),
                          SUM(CASE WHEN success=1 THEN 1 ELSE 0 END),
                          AVG(cost_yuan), AVG(duration_ms),
                          AVG(tokens_input + tokens_output)
                   FROM cost_records
                   WHERE worker_type = ?
                     AND timestamp >= date('now', ? || ' days')""",
                (worker_type, f"-{days}"),
            ).fetchone()

        return {
            "worker_type": worker_type,
            "total_tasks": row[0] or 0,
            "success_rate": round((row[1] or 0) / max(row[0], 1), 2),
            "avg_cost_yuan": round(row[2] or 0, 4),
            "avg_duration_ms": int(row[3] or 0),
            "avg_tokens": int(row[4] or 0),
        }

    def all_records(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent cost records for display."""
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                """SELECT timestamp, task_id, worker_type, model,
                          tokens_input, tokens_output, cost_yuan, duration_ms, success
                   FROM cost_records
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()

        return [
            {
                "timestamp": r[0], "task_id": r[1], "worker_type": r[2],
                "model": r[3], "tokens_in": r[4], "tokens_out": r[5],
                "cost_yuan": r[6], "duration_ms": r[7], "success": bool(r[8]),
            }
            for r in rows
        ]

    def close(self) -> None:
        """No-op for SQLite (connection is per-operation)."""
        pass
