"""Trading Worker — financial market analysis via TradingAgents framework.

Wraps the TradingAgents Graph API (propagate()) for market analysis,
trading signals, and risk assessment.

Reference patterns:
  - TradingAgents trading_graph.py: TradingAgentsGraph.propagate()
  - TradingAgents schemas.py: PortfolioDecision, TraderProposal structured outputs
"""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any

from ama.workers.base import BaseWorker, TaskInput, TaskOutput, WorkerInfo

logger = logging.getLogger(__name__)

# Path to TradingAgents project
TRADINGAGENTS_PATH = "d:/TradingAgents"


class TradingWorker(BaseWorker):
    """Financial trading worker — wraps TradingAgents multi-agent pipeline.

    Executes: analysts → researchers → trader → risk → portfolio manager
    Returns structured trading decision with confidence scores.

    Requires TradingAgents to be installed in d:/TradingAgents.
    """

    worker_type = "trading"

    def __init__(self, info: WorkerInfo) -> None:
        super().__init__(info)
        self._trading_agents = None  # Lazy import

    async def execute(self, task: TaskInput) -> TaskOutput:
        t0 = time.monotonic()

        try:
            # Ensure TradingAgents is importable
            if TRADINGAGENTS_PATH not in sys.path:
                sys.path.insert(0, TRADINGAGENTS_PATH)

            result = await self._run_analysis(task)
            decision = self._extract_decision(result)

            return self._build_output(
                task_id=task.task_id,
                result={
                    "decision": decision,
                    "raw_result": self._summarize(result),
                },
                success=decision is not None,
                model_used="deepseek/pro-1m",
                tokens_used=result.get("_tokens", 0),
                cost_yuan=self.estimate_cost(task),
                start_time=t0,
                confidence=decision.get("confidence", 0.5) if decision else 0.0,
                error=None if decision else "Failed to extract trading decision",
                needs_human=decision is None or decision.get("signal") == "HOLD",
            )

        except ImportError as exc:
            logger.warning("TradingAgents not available: %s", exc)
            return self._build_output(
                task_id=task.task_id, result=None, success=False,
                model_used="none", start_time=t0,
                error=f"TradingAgents not installed: {exc}",
                needs_human=True,
            )
        except Exception as exc:
            logger.error("TradingWorker error: %s", exc)
            return self._build_output(
                task_id=task.task_id, result=None, success=False,
                model_used="deepseek/pro-1m", start_time=t0,
                error=str(exc), needs_human=True,
            )

    async def health_check(self) -> bool:
        """Check if TradingAgents is available."""
        try:
            if TRADINGAGENTS_PATH not in sys.path:
                sys.path.insert(0, TRADINGAGENTS_PATH)
            from tradingagents.graph.trading_graph import TradingAgentsGraph
            return True
        except ImportError:
            return False

    def estimate_cost(self, task: TaskInput) -> float:
        """TradingAgents uses multiple LLM calls (~50K tokens)."""
        est_tokens = 50000  # Multi-agent pipeline is token-heavy
        return round(est_tokens * 0.000015, 4)  # ~¥0.75 per analysis

    # ── Internal ──────────────────────────────────────────────

    async def _run_analysis(self, task: TaskInput) -> dict[str, Any]:
        """Run TradingAgents propagate() in a thread (it's synchronous)."""
        import asyncio
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG

        ticker = task.context.get("ticker", "NVDA")
        date_str = task.context.get("date", "2024-05-10")

        # Build config
        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = task.context.get("llm_provider", "deepseek")
        config["deep_think_llm"] = task.context.get("deep_model", "deepseek-v4-pro")
        config["quick_think_llm"] = task.context.get("quick_model", "deepseek-v4-flash")
        config["backend_url"] = task.context.get("api_base", "https://api.deepseek.com")
        config["max_debate_rounds"] = task.context.get("debate_rounds", 1)

        # Set API key
        api_key = task.context.get(
            "api_key",
            os.environ.get("ANTHROPIC_AUTH_TOKEN", os.environ.get("DEEPSEEK_API_KEY", "")),
        )
        if api_key:
            os.environ.setdefault("DEEPSEEK_API_KEY", api_key)

        # Run in executor (TradingAgents is synchronous)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._sync_propagate(ticker, date_str, config),
        )

    def _sync_propagate(self, ticker: str, date_str: str,
                        config: dict) -> dict[str, Any]:
        """Synchronous wrapper for TradingAgentsGraph.propagate()."""
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        ta = TradingAgentsGraph(debug=False, config=config)
        final_state, decision = ta.propagate(ticker, date_str)
        return {
            "ticker": ticker,
            "date": date_str,
            "final_state": final_state,
            "decision": decision,
            "_tokens": 50000,  # Conservative estimate
        }

    def _extract_decision(self, result: dict) -> dict | None:
        """Extract structured decision from TradingAgents output."""
        decision = result.get("decision", {})
        if not decision:
            return None

        final = decision.get("final_trade_decision", {})
        if isinstance(final, str):
            return {
                "signal": "HOLD",
                "summary": final[:500],
                "confidence": 0.6,
            }

        return {
            "signal": final.get("signal", final.get("score", "HOLD")),
            "summary": final.get("summary", final.get("executive_summary", ""))[:500],
            "target_price": final.get("target_price"),
            "time_horizon": final.get("time_horizon", "medium"),
            "confidence": final.get("confidence", 0.7),
            "risk_level": final.get("risk_level", "medium"),
        }

    def _summarize(self, result: dict) -> dict:
        """Create a safe summary (strip large nested objects)."""
        summary = {
            "ticker": result.get("ticker"),
            "date": result.get("date"),
        }
        decision = self._extract_decision(result)
        if decision:
            summary["signal"] = decision.get("signal")
            summary["confidence"] = decision.get("confidence")
        return summary
