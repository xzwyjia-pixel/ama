"""AMA Task Scheduler — autonomous recurring task execution.

Reference: GenericAgent reflect/scheduler.py — cron-like task scheduling
Supports: one-shot, interval, daily, weekly recurring jobs
Persistence: SQLite for schedule config + execution history

Usage:
    python -m ama.main --schedule       # Start scheduler (runs until stopped)
    python -m ama.main --schedule --once  # Run pending tasks once and exit
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    ONCE = "once"
    INTERVAL = "interval"  # every N seconds
    DAILY = "daily"        # at specific HH:MM
    WEEKLY = "weekly"      # on specific weekday at HH:MM


@dataclass
class ScheduledTask:
    """A task scheduled for execution."""
    task_id: str
    name: str
    schedule_type: ScheduleType
    config: dict[str, Any]  # type-specific config
    action: str  # pipeline name or command
    action_params: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    last_run: str | None = None
    next_run: str | None = None
    run_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# Pre-built task definitions
BUILTIN_TASKS = [
    ScheduledTask(
        task_id="daily_cost_report",
        name="每日成本报告",
        schedule_type=ScheduleType.DAILY,
        config={"hour": 20, "minute": 0},
        action="report",
        action_params={},
    ),
    ScheduledTask(
        task_id="weekly_content_batch",
        name="每周内容批量生成",
        schedule_type=ScheduleType.WEEKLY,
        config={"weekday": 0, "hour": 9, "minute": 0},  # Monday 9am
        action="pipeline",
        action_params={"pipeline": "content", "count": 5},
    ),
    ScheduledTask(
        task_id="daily_shop_refresh",
        name="每日商店文案刷新",
        schedule_type=ScheduleType.DAILY,
        config={"hour": 8, "minute": 30},
        action="pipeline",
        action_params={"pipeline": "shop"},
    ),
    ScheduledTask(
        task_id="health_check_every_4h",
        name="系统健康检查(每4小时)",
        schedule_type=ScheduleType.INTERVAL,
        config={"seconds": 14400},  # 4 hours
        action="health",
        action_params={},
    ),
]


class TaskScheduler:
    """Lightweight async task scheduler with SQLite persistence.

    Usage:
        scheduler = TaskScheduler(execute_func=my_handler)
        scheduler.add_task(task)
        await scheduler.start()
        # ... runs until stop()
    """

    def __init__(
        self,
        execute_func: Callable[[ScheduledTask], Coroutine] | None = None,
        db_path: str = "c:/Users/25454/业务中控台/ama/data/ama.db",
    ):
        self.db_path = Path(db_path)
        self._tasks: dict[str, ScheduledTask] = {}
        self._execute = execute_func or self._default_execute
        self._running = False
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    task_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    schedule_type TEXT NOT NULL,
                    config TEXT DEFAULT '{}',
                    action TEXT NOT NULL,
                    action_params TEXT DEFAULT '{}',
                    enabled INTEGER DEFAULT 1,
                    last_run TEXT,
                    next_run TEXT,
                    run_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def add_task(self, task: ScheduledTask) -> None:
        """Add or update a scheduled task."""
        task.next_run = self._calc_next_run(task)
        self._tasks[task.task_id] = task
        self._save_task(task)

    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("DELETE FROM scheduled_tasks WHERE task_id = ?", (task_id,))
                conn.commit()
            return True
        return False

    def load_builtins(self) -> None:
        """Load built-in task definitions (skip if already present)."""
        for task in BUILTIN_TASKS:
            if task.task_id not in self._tasks:
                self.add_task(task)

    def load_from_db(self) -> None:
        """Restore tasks from database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                "SELECT * FROM scheduled_tasks WHERE enabled = 1"
            ).fetchall()
            for row in rows:
                task = ScheduledTask(
                    task_id=row[0], name=row[1],
                    schedule_type=ScheduleType(row[2]),
                    config=json.loads(row[3]), action=row[4],
                    action_params=json.loads(row[5]),
                    enabled=bool(row[6]), last_run=row[7],
                    next_run=row[8], run_count=row[9],
                    created_at=row[10],
                )
                self._tasks[task.task_id] = task
        logger.info("Loaded %d tasks from DB", len(self._tasks))

    async def start(self, run_once: bool = False) -> None:
        """Start the scheduler loop.

        Args:
            run_once: If True, execute all due tasks and exit.
        """
        self._running = True
        logger.info("Scheduler started (run_once=%s)", run_once)

        while self._running:
            now = datetime.now()
            executed = 0

            for task in list(self._tasks.values()):
                if not task.enabled:
                    continue
                if task.next_run and datetime.fromisoformat(task.next_run) <= now:
                    await self._run_task(task)
                    executed += 1

            if run_once and executed == 0:
                # Check if any tasks are actually due
                any_due = any(
                    t.next_run and datetime.fromisoformat(t.next_run) <= now
                    for t in self._tasks.values() if t.enabled
                )
                if not any_due:
                    logger.info("No due tasks, exiting run_once mode")
                    break

            await asyncio.sleep(1)  # Check every second

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        logger.info("Scheduler stopped")

    async def _run_task(self, task: ScheduledTask) -> None:
        """Execute a single scheduled task."""
        logger.info("Running task: %s (%s)", task.name, task.task_id)
        try:
            await self._execute(task)
            task.last_run = datetime.now().isoformat()
            task.run_count += 1
            task.next_run = self._calc_next_run(task)
            self._save_task(task)
            logger.info("Task %s completed (run #%d)", task.name, task.run_count)
        except Exception as exc:
            logger.error("Task %s failed: %s", task.name, exc)

    async def _default_execute(self, task: ScheduledTask) -> None:
        """Default executor — logs the task, override with real logic."""
        logger.info(
            "Default execute: action=%s params=%s",
            task.action, task.action_params,
        )

    def _calc_next_run(self, task: ScheduledTask) -> str:
        """Calculate the next run time based on schedule type."""
        now = datetime.now()
        cfg = task.config

        if task.schedule_type == ScheduleType.ONCE:
            return (now + timedelta(seconds=10)).isoformat()  # Fire soon

        elif task.schedule_type == ScheduleType.INTERVAL:
            seconds = cfg.get("seconds", 3600)
            return (now + timedelta(seconds=seconds)).isoformat()

        elif task.schedule_type == ScheduleType.DAILY:
            hour = cfg.get("hour", 9)
            minute = cfg.get("minute", 0)
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run.isoformat()

        elif task.schedule_type == ScheduleType.WEEKLY:
            weekday = cfg.get("weekday", 0)  # 0=Mon
            hour = cfg.get("hour", 9)
            minute = cfg.get("minute", 0)
            days_ahead = weekday - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_run = (now + timedelta(days=days_ahead)).replace(
                hour=hour, minute=minute, second=0, microsecond=0,
            )
            return next_run.isoformat()

        return (now + timedelta(hours=1)).isoformat()

    def _save_task(self, task: ScheduledTask) -> None:
        """Persist task to database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO scheduled_tasks
                   (task_id, name, schedule_type, config, action, action_params,
                    enabled, last_run, next_run, run_count, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task.task_id, task.name, task.schedule_type.value,
                    json.dumps(task.config), task.action,
                    json.dumps(task.action_params),
                    1 if task.enabled else 0,
                    task.last_run, task.next_run, task.run_count, task.created_at,
                ),
            )
            conn.commit()

    def status(self) -> dict[str, Any]:
        """Get scheduler status."""
        tasks_list = []
        for t in self._tasks.values():
            tasks_list.append({
                "task_id": t.task_id,
                "name": t.name,
                "type": t.schedule_type.value,
                "enabled": t.enabled,
                "next_run": t.next_run,
                "last_run": t.last_run,
                "run_count": t.run_count,
            })
        return {
            "running": self._running,
            "total_tasks": len(self._tasks),
            "tasks": sorted(tasks_list, key=lambda t: t["next_run"] or ""),
        }
