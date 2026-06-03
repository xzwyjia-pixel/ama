"""Task Store — SQLite-backed task persistence and retrieval.

Reference patterns:
  - GenericAgent memory/ L4 session compression
  - Pi Agent AGENTS.md cross-software discovery pattern
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from ama.workers.base import TaskInput, TaskOutput, TaskStatus


class TaskStore:
    """Persistent task storage using SQLite.

    Usage:
        store = TaskStore("data/ama.db")
        store.save_task(task, output)
        history = store.get_history(limit=50)
    """

    def __init__(self, db_path: str = "c:/Users/25454/业务中控台/ama/data/ama.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    complexity INTEGER DEFAULT 5,
                    priority INTEGER DEFAULT 3,
                    status TEXT DEFAULT 'PENDING',
                    model_used TEXT,
                    cost_yuan REAL DEFAULT 0.0,
                    tokens_used INTEGER DEFAULT 0,
                    duration_ms INTEGER DEFAULT 0,
                    confidence REAL DEFAULT 0.0,
                    success INTEGER DEFAULT 0,
                    error TEXT,
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)
            """)
            conn.commit()

    def save_task(self, task: TaskInput, output: TaskOutput) -> None:
        """Save a completed task to the database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO tasks
                   (task_id, task_type, description, complexity, priority, status,
                    model_used, cost_yuan, tokens_used, duration_ms, confidence,
                    success, error, result_json, created_at, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task.task_id,
                    task.task_type,
                    task.description,
                    task.complexity,
                    int(task.priority),
                    TaskStatus.COMPLETED.name if output.success else TaskStatus.FAILED.name,
                    output.model_used,
                    output.cost_yuan,
                    output.tokens_used,
                    output.duration_ms,
                    output.confidence,
                    1 if output.success else 0,
                    output.error,
                    json.dumps(
                        {"result": str(output.result)[:5000]} if output.result else {},
                        ensure_ascii=False,
                    ),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        """Retrieve a single task by ID."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_history(self, limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
        """Get recent task history, optionally filtered by status."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            if status:
                rows = conn.execute(
                    """SELECT task_id, task_type, description, complexity, status,
                              model_used, cost_yuan, duration_ms, success, created_at
                       FROM tasks WHERE status = ?
                       ORDER BY created_at DESC LIMIT ?""",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT task_id, task_type, description, complexity, status,
                              model_used, cost_yuan, duration_ms, success, created_at
                       FROM tasks
                       ORDER BY created_at DESC LIMIT ?""",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]

    def stats(self) -> dict[str, Any]:
        """Get aggregate task statistics."""
        with sqlite3.connect(str(self.db_path)) as conn:
            total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            success = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE success = 1"
            ).fetchone()[0]
            total_cost = conn.execute(
                "SELECT SUM(cost_yuan) FROM tasks"
            ).fetchone()[0] or 0
            avg_duration = conn.execute(
                "SELECT AVG(duration_ms) FROM tasks WHERE success = 1"
            ).fetchone()[0] or 0

        return {
            "total_tasks": total,
            "successful": success,
            "failed": total - success,
            "success_rate": round(success / max(total, 1), 2),
            "total_cost_yuan": round(total_cost, 4),
            "avg_duration_ms": int(avg_duration),
        }
