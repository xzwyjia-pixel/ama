"""Quality Reviewer — post-execution validation of worker outputs.

Checks:
  1. Confidence threshold check
  2. Output completeness (non-empty, reasonable length)
  3. Error/success flag consistency
  4. Cost vs budget alignment

Reference patterns:
  - GenericAgent memory/verify_sop.md — verification SOP
  - Workflow adversarial verify pattern — independent skepticism
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ama.workers.base import TaskInput, TaskOutput

logger = logging.getLogger(__name__)


@dataclass
class ReviewResult:
    """Result of quality review."""
    passed: bool
    score: float  # 0.0 - 1.0
    reason: str
    needs_human: bool = False
    suggestions: list[str] = field(default_factory=list)


class QualityReviewer:
    """Validates worker outputs before delivery.

    Usage:
        reviewer = QualityReviewer(confidence_threshold=0.7)
        result = reviewer.review(task, output)
        if not result.passed:
            # retry or escalate
    """

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        min_result_length: int = 10,
        check_cost_budget: bool = True,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.min_result_length = min_result_length
        self.check_cost_budget = check_cost_budget

    def review(self, task: TaskInput, output: TaskOutput) -> ReviewResult:
        """Review a worker's output against quality criteria.

        Returns ReviewResult with pass/fail and actionable feedback.
        """
        checks: list[tuple[bool, str]] = []

        # 1. Success flag check
        if not output.success:
            return ReviewResult(
                passed=False,
                score=0.0,
                reason=f"Task failed: {output.error or 'Unknown error'}",
                needs_human=output.needs_human,
                suggestions=["Retry with fallback model", "Check worker health"],
            )

        # 2. Confidence check
        if output.confidence < self.confidence_threshold:
            checks.append((
                False,
                f"Confidence {output.confidence:.0%} below threshold "
                f"{self.confidence_threshold:.0%}",
            ))
        else:
            checks.append((True, f"Confidence {output.confidence:.0%} OK"))

        # 3. Result completeness
        result_str = str(output.result) if output.result else ""
        if len(result_str) < self.min_result_length:
            checks.append((
                False,
                f"Result too short ({len(result_str)} chars < {self.min_result_length})",
            ))
        else:
            checks.append((True, f"Result length {len(result_str)} chars OK"))

        # 4. Cost vs budget
        if self.check_cost_budget and output.cost_yuan > task.budget_yuan:
            checks.append((
                False,
                f"Cost ¥{output.cost_yuan:.4f} exceeds budget ¥{task.budget_yuan:.2f}",
            ))
        else:
            checks.append((True, f"Cost ¥{output.cost_yuan:.4f} within budget"))

        # 5. Needs human flag consistency
        if output.needs_human and output.success:
            checks.append((
                True,
                "Task succeeded but worker flagged for human review",
            ))

        # Aggregate
        passed = all(c[0] for c in checks)
        score = sum(1 for c in checks if c[0]) / max(len(checks), 1)
        reason = "; ".join(c[1] for c in checks)
        suggestions = [
            c[1] for c in checks if not c[0]
        ] if not passed else []

        return ReviewResult(
            passed=passed,
            score=round(score, 2),
            reason=reason,
            needs_human=output.needs_human,
            suggestions=suggestions,
        )

    def should_retry(self, result: ReviewResult, attempt: int, max_retries: int) -> bool:
        """Determine if a failed review should trigger a retry."""
        if result.passed:
            return False
        if attempt >= max_retries:
            return False
        # Don't retry if it needs human — escalate instead
        if result.needs_human:
            return False
        return True

    def escalate_to_human(self, task: TaskInput, output: TaskOutput,
                          review: ReviewResult) -> dict[str, Any]:
        """Build a human escalation payload."""
        return {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "description": task.description,
            "result": str(output.result)[:500] if output.result else None,
            "error": output.error,
            "confidence": output.confidence,
            "review_score": review.score,
            "review_reason": review.reason,
            "cost_yuan": output.cost_yuan,
            "action_required": "Please review and decide: retry / accept / cancel",
        }
