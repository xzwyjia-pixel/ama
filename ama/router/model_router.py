"""Model Router — cost-optimized model selection for each task.

Reference patterns:
  - GenericAgent llmcore.py — multi-model adapter with MixinSession failover
  - GenericAgent agentmain.py — next_llm() runtime model switching
  - Pi Agent models.json — declarative provider/model definitions

Core algorithm:
  1. Filter models by capability >= task complexity
  2. Sort by cost (cheapest first)
  3. Try in order with fallback chain on failure
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ama.config import get_models
from ama.workers.base import TaskInput

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Resolved model metadata from config."""

    model_id: str
    provider: str
    model_name: str
    api_base: str
    api_key_ref: str | None
    context_window: int
    max_output_tokens: int
    capability_score: int  # 1-10
    supports_tools: bool
    supports_images: bool
    pricing: dict[str, float]
    model_type: str  # local / cloud
    timeout_seconds: int
    weight: int  # preference weight (higher = preferred within same cost tier)

    @property
    def cost_per_1k_input(self) -> float:
        return self.pricing.get("input_per_1k", 0.0)

    @property
    def cost_per_1k_output(self) -> float:
        return self.pricing.get("output_per_1k", 0.0)

    def estimate_cost(self, estimated_input_tokens: int, estimated_output_tokens: int) -> float:
        """Estimate total cost in yuan for a task."""
        input_cost = (estimated_input_tokens / 1000) * self.cost_per_1k_input
        output_cost = (estimated_output_tokens / 1000) * self.cost_per_1k_output
        per_image = self.pricing.get("per_image", 0.0)
        return round(input_cost + output_cost + per_image, 6)


@dataclass
class RouteResult:
    """Result of model routing decision."""

    model: ModelInfo
    reason: str
    estimated_cost_yuan: float
    fallback_chain: list[str] = field(default_factory=list)


@dataclass
class RouterStats:
    """Aggregated routing statistics."""

    total_routes: int = 0
    fallback_triggered: int = 0
    by_model: dict[str, int] = field(default_factory=dict)
    total_estimated_cost: float = 0.0


class ModelRouter:
    """Cost-optimized model selection engine.

    Usage:
        router = ModelRouter()
        result = await router.route(task, estimated_tokens=5000)
        # result.model is the best model for this task
    """

    def __init__(self, config_path: str | None = None) -> None:
        config = get_models() if config_path is None else _load_config(config_path)
        self.models: dict[str, ModelInfo] = {}
        self.fallback_chain: list[str] = config.get("fallback_chain", [])
        self.thresholds: dict[str, int] = config.get("complexity_thresholds", {})
        self.default_model: str = config.get("default", "deepseek/flash")
        self.stats = RouterStats()
        self._load_models(config["models"])

    def _load_models(self, models_config: dict) -> None:
        for model_id, cfg in models_config.items():
            self.models[model_id] = ModelInfo(
                model_id=model_id,
                provider=cfg["provider"],
                model_name=cfg["model_name"],
                api_base=cfg["api_base"],
                api_key_ref=cfg.get("api_key_ref"),
                context_window=cfg["context_window"],
                max_output_tokens=cfg["max_output_tokens"],
                capability_score=cfg["capability_score"],
                supports_tools=cfg.get("supports_tools", False),
                supports_images=cfg.get("supports_images", False),
                pricing=cfg["pricing"],
                model_type=cfg["type"],
                timeout_seconds=cfg.get("timeout_seconds", 60),
                weight=cfg.get("weight", 1),
            )
        logger.info(
            "Loaded %d models: %s",
            len(self.models),
            ", ".join(f"{m.model_id}(c={m.capability_score})"
                      for m in sorted(self.models.values(),
                                      key=lambda x: x.capability_score)),
        )

    def route(
        self,
        task: TaskInput,
        estimated_input_tokens: int = 2000,
        estimated_output_tokens: int = 2000,
        preferred_model: str | None = None,
    ) -> RouteResult:
        """Select the best model for a task.

        Algorithm:
          1. If preferred_model is specified and capable, use it.
          2. Filter models with capability >= task complexity.
          3. Sort by: cost (ascending), then weight (descending).
          4. Build fallback chain from remaining models.

        Returns RouteResult with the selected model and fallback options.
        """
        self.stats.total_routes += 1

        # 1. Preferred model override
        if preferred_model and preferred_model in self.models:
            model = self.models[preferred_model]
            if model.capability_score >= task.complexity:
                return self._make_result(model, task, estimated_input_tokens,
                                         estimated_output_tokens, "preferred_model")

        # 2. Filter capable models (exclude incompatible types)
        _is_image_task = task.task_type in (
            "image_gen", "video_gen", "audio_gen",
        )
        capable = [
            m for m in self.models.values()
            if m.capability_score >= task.complexity
            # For non-image tasks: exclude models that ONLY support images
            # (e.g. ComfyUI: supports_images=True, supports_tools=False)
            and (_is_image_task or m.supports_tools
                 or not m.supports_images)
        ]

        if not capable:
            # No model is capable enough — use the highest-capability model
            logger.warning(
                "No model meets complexity %d for task %s, using max available",
                task.complexity, task.task_id,
            )
            capable = sorted(self.models.values(),
                             key=lambda m: m.capability_score, reverse=True)

        # 3. Sort: cheapest first, then by weight (preference)
        capable.sort(key=lambda m: (
            m.estimate_cost(estimated_input_tokens, estimated_output_tokens),
            -m.weight,
        ))

        # 4. Build result with fallback chain
        best = capable[0]
        fallback = [m.model_id for m in capable[1:]]
        # Append global fallback chain for resilience
        for fb in self.fallback_chain:
            if fb not in fallback and fb != best.model_id and fb in self.models:
                fallback.append(fb)

        cost = best.estimate_cost(estimated_input_tokens, estimated_output_tokens)
        reason = (
            f"capability={best.capability_score}>={task.complexity}, "
            f"cost=¥{cost:.4f}, "
            f"type={best.model_type}"
        )

        self.stats.by_model[best.model_id] = \
            self.stats.by_model.get(best.model_id, 0) + 1
        self.stats.total_estimated_cost += cost

        return RouteResult(
            model=best,
            reason=reason,
            estimated_cost_yuan=cost,
            fallback_chain=fallback,
        )

    def get_model(self, model_id: str) -> ModelInfo | None:
        """Get model info by ID."""
        return self.models.get(model_id)

    def _make_result(
        self,
        model: ModelInfo,
        task: TaskInput,
        input_tokens: int,
        output_tokens: int,
        reason_prefix: str,
    ) -> RouteResult:
        cost = model.estimate_cost(input_tokens, output_tokens)
        self.stats.by_model[model.model_id] = \
            self.stats.by_model.get(model.model_id, 0) + 1
        self.stats.total_estimated_cost += cost
        return RouteResult(
            model=model,
            reason=f"[{reason_prefix}] capability={model.capability_score}, "
                   f"cost=¥{cost:.4f}",
            estimated_cost_yuan=cost,
            fallback_chain=self.fallback_chain.copy(),
        )

    async def check_model_health(self, model_id: str) -> bool:
        """Quick health check for a model endpoint.

        For local models (Ollama), checks if the service is running.
        For cloud models, does a lightweight API probe.
        """
        model = self.models.get(model_id)
        if not model:
            return False

        if model.model_type == "local":
            return await self._probe_http(model.api_base, timeout=3)
        else:
            return await self._probe_http(model.api_base, timeout=5)

    async def _probe_http(self, url: str, timeout: int = 5) -> bool:
        """Probe an HTTP endpoint for availability."""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{url}/health", timeout=timeout) as resp:
                    return resp.status < 500
        except Exception:
            pass
        try:
            # Fallback: just check if the host is reachable
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=timeout) as resp:
                    return resp.status < 500
        except Exception:
            return False


def _load_config(path: str) -> dict[str, Any]:
    import json
    with open(path, encoding="utf-8") as f:
        return json.load(f)
