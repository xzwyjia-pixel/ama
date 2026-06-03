"""Phase 4: Feedback Loop — auto-categorize failures, trigger improvements.

Analyzes task failures to identify patterns, then suggests or applies fixes.

Reference: GenericAgent memory/ system — L0-L4 layered memory for learning
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FailureEvent:
    """A single failure event for analysis."""
    task_id: str
    worker_type: str
    model: str
    error: str
    timestamp: str
    retry_count: int = 0
    resolved: bool = False
    category: str = "unknown"


FAILURE_CATEGORIES = {
    "rate_limit": ["rate limit", "too many requests", "429", "try again"],
    "timeout": ["timeout", "timed out", "deadline exceeded"],
    "auth_error": ["unauthorized", "auth", "api key", "401", "403", "permission"],
    "model_unavailable": ["not found", "unavailable", "down", "503", "502", "connection"],
    "input_error": ["invalid", "bad request", "400", "validation", "too short", "too long"],
    "budget_exceeded": ["budget", "cost", "exceeded"],
    "worker_error": ["worker", "not found", "not implemented", "no worker"],
    "unknown": [],
}


class FeedbackLoop:
    """Self-improving feedback system.

    Usage:
        loop = FeedbackLoop()
        loop.record_failure(task_id, worker, model, error)
        insights = loop.analyze()
        loop.apply_fix(insight)
    """

    def __init__(
        self,
        db_path: str = "c:/Users/25454/业务中控台/ama/data/ama.db",
    ):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS failure_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    worker_type TEXT NOT NULL,
                    model TEXT NOT NULL,
                    error TEXT,
                    timestamp TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    resolved INTEGER DEFAULT 0,
                    category TEXT DEFAULT 'unknown'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS improvement_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    insight TEXT NOT NULL,
                    action TEXT,
                    applied_at TEXT NOT NULL,
                    impact TEXT DEFAULT 'pending'
                )
            """)
            conn.commit()

    def record_failure(
        self,
        task_id: str,
        worker_type: str,
        model: str,
        error: str,
        retry_count: int = 0,
    ) -> None:
        """Record a task failure for analysis."""
        category = self._categorize(error)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """INSERT INTO failure_events
                   (task_id, worker_type, model, error, timestamp, retry_count, category)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (task_id, worker_type, model, error,
                 datetime.now().isoformat(), retry_count, category),
            )
            conn.commit()
        logger.debug("Failure recorded: %s → %s", task_id, category)

    def _categorize(self, error: str) -> str:
        error_lower = error.lower() if error else ""
        for category, keywords in FAILURE_CATEGORIES.items():
            if any(kw in error_lower for kw in keywords):
                return category
        return "unknown"

    def analyze(self, window_hours: int = 24) -> dict[str, Any]:
        """Analyze recent failures and generate improvement insights.

        Returns categorized failures with suggested fixes.
        """
        cutoff = (datetime.now() - timedelta(hours=window_hours)).isoformat()

        with sqlite3.connect(str(self.db_path)) as conn:
            # Failure counts by category
            cat_rows = conn.execute(
                """SELECT category, COUNT(*) as cnt
                   FROM failure_events
                   WHERE timestamp >= ? AND resolved = 0
                   GROUP BY category
                   ORDER BY cnt DESC""",
                (cutoff,),
            ).fetchall()

            # Failure counts by worker
            worker_rows = conn.execute(
                """SELECT worker_type, COUNT(*) as cnt,
                          SUM(CASE WHEN resolved=1 THEN 1 ELSE 0 END) as resolved_cnt
                   FROM failure_events
                   WHERE timestamp >= ?
                   GROUP BY worker_type""",
                (cutoff,),
            ).fetchall()

            # Top recurring errors
            error_rows = conn.execute(
                """SELECT error, COUNT(*) as cnt
                   FROM failure_events
                   WHERE timestamp >= ? AND resolved = 0
                   GROUP BY error
                   ORDER BY cnt DESC
                   LIMIT 5""",
                (cutoff,),
            ).fetchall()

        categories = {row[0]: row[1] for row in cat_rows}
        workers = {
            row[0]: {"total": row[1], "resolved": row[2]}
            for row in worker_rows
        }

        # Generate insights
        insights = []
        for cat, count in categories.items():
            insight = self._generate_insight(cat, count)
            if insight:
                insights.append(insight)

        total_failures = sum(categories.values())
        return {
            "window_hours": window_hours,
            "total_failures": total_failures,
            "categories": categories,
            "workers": workers,
            "top_errors": [{"error": r[0][:200], "count": r[1]} for r in error_rows],
            "insights": insights,
            "health_score": max(0, 100 - total_failures * 5),
        }

    def _generate_insight(self, category: str, count: int) -> dict | None:
        """Generate actionable insight from failure category."""
        fixes = {
            "rate_limit": {
                "insight": f"Rate limiting detected ({count} occurrences)",
                "action": "increase_delay",
                "detail": "Add exponential backoff between requests",
                "auto_fix": True,
            },
            "timeout": {
                "insight": f"Timeout errors ({count} occurrences)",
                "action": "reduce_complexity",
                "detail": "Route to faster model or reduce task complexity",
                "auto_fix": True,
            },
            "auth_error": {
                "insight": f"Authentication failures ({count} occurrences)",
                "action": "check_keys",
                "detail": "Verify API keys are valid and not expired",
                "auto_fix": False,
            },
            "model_unavailable": {
                "insight": f"Model unavailable ({count} occurrences)",
                "action": "force_fallback",
                "detail": "Temporarily remove from routing pool",
                "auto_fix": True,
            },
            "input_error": {
                "insight": f"Input validation errors ({count} occurrences)",
                "action": "improve_prompt",
                "detail": "Review and fix task input generation",
                "auto_fix": False,
            },
            "budget_exceeded": {
                "insight": f"Budget exceeded ({count} occurrences)",
                "action": "force_cheap_models",
                "detail": "Route all tasks to free local models",
                "auto_fix": True,
            },
            "worker_error": {
                "insight": f"Worker errors ({count} occurrences)",
                "action": "check_worker_health",
                "detail": "Verify worker health and restart if needed",
                "auto_fix": True,
            },
        }
        result = fixes.get(category)
        if result:
            result["category"] = category
            result["count"] = count
        return result

    def apply_fix(self, insight: dict) -> bool:
        """Apply an automated fix based on insight. Returns True if applied."""
        if not insight.get("auto_fix"):
            logger.info("Manual fix required: %s", insight["insight"])
            return False

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """INSERT INTO improvement_log
                   (category, insight, action, applied_at, impact)
                   VALUES (?, ?, ?, ?, 'applied')""",
                (
                    insight["category"],
                    insight["insight"],
                    insight["detail"],
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

        # Mark related failures as resolved
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """UPDATE failure_events SET resolved = 1
                   WHERE category = ? AND resolved = 0""",
                (insight["category"],),
            )
            conn.commit()

        logger.info("Applied fix: %s → %s", insight["action"], insight["detail"])
        return True

    def get_improvement_history(self, limit: int = 20) -> list[dict]:
        """Get history of applied improvements."""
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                """SELECT * FROM improvement_log
                   ORDER BY applied_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [
            {
                "category": r[1], "insight": r[2], "action": r[3],
                "applied_at": r[4], "impact": r[5],
            }
            for r in rows
        ]

    def health_score(self) -> int:
        """Calculate system health score (0-100)."""
        analysis = self.analyze(window_hours=24)
        return analysis["health_score"]
