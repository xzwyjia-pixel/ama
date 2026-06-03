"""Content Worker — writing, translation, summarization, social media.

Uses LLM API calls (OpenAI-compatible) to perform content generation tasks.
Supports both cloud (DeepSeek) and local (Ollama) models.

Reference patterns:
  - GenericAgent llmcore.py — LLMSession/NativeOAISession for API calls
  - Pi Agent models.json — DeepSeek/Ollama provider config format
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import aiohttp

from ama.workers.base import BaseWorker, TaskInput, TaskOutput, WorkerInfo

logger = logging.getLogger(__name__)

# Provider configs from environment / settings
# These match the DeepSeek Anthropic-compatible endpoint from CLAUDE.md
PROVIDER_CONFIGS = {
    "deepseek": {
        "api_base": "https://api.deepseek.com",
        "api_key": os.environ.get(
            "ANTHROPIC_AUTH_TOKEN",
            os.environ.get("DEEPSEEK_API_KEY", ""),
        ),
        "anthropic_compat": True,
    },
    "ollama": {
        "api_base": "http://localhost:11434/v1",
        "api_key": "ollama",  # not required
        "anthropic_compat": False,
    },
}

# Model name mapping
MODEL_NAMES = {
    "deepseek/pro-1m": "deepseek-v4-pro",
    "deepseek/flash": "deepseek-v4-flash",
    "ollama/qwen2.5:14b": "qwen2.5:14b",
}


class ContentWorker(BaseWorker):
    """Content generation worker — writing, translation, social media.

    Can use any OpenAI-compatible LLM endpoint.
    """

    worker_type = "content"

    def __init__(self, info: WorkerInfo) -> None:
        super().__init__(info)
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def execute(self, task: TaskInput) -> TaskOutput:
        t0 = time.monotonic()
        model_id = task.context.get("_model_id", self.info.default_model)
        model_name = MODEL_NAMES.get(model_id, model_id)
        provider = model_id.split("/")[0] if "/" in model_id else "deepseek"

        cfg = PROVIDER_CONFIGS.get(provider, PROVIDER_CONFIGS["deepseek"])

        system_prompt = self._build_system_prompt(task)
        user_prompt = self._build_user_prompt(task)

        try:
            session = await self._get_session()

            if cfg.get("anthropic_compat"):
                result_text, tokens = await self._call_anthropic_compat(
                    session, cfg, model_name, system_prompt, user_prompt,
                )
            else:
                result_text, tokens = await self._call_openai_compat(
                    session, cfg, model_name, system_prompt, user_prompt,
                )

            cost = self._calc_cost(model_id, tokens)
            return self._build_output(
                task_id=task.task_id,
                result=result_text,
                success=True,
                model_used=model_id,
                tokens_used=tokens,
                cost_yuan=cost,
                start_time=t0,
                confidence=self._estimate_confidence(result_text),
            )

        except Exception as exc:
            logger.error("ContentWorker error: %s", exc)
            return self._build_output(
                task_id=task.task_id,
                result=None,
                success=False,
                model_used=model_id,
                error=str(exc),
                start_time=t0,
                needs_human=True,
            )

    async def health_check(self) -> bool:
        """Quick health check — try Ollama first (local), then DeepSeek."""
        try:
            session = await self._get_session()
            # Try Ollama (fast, local)
            async with session.get(
                "http://localhost:11434/api/tags", timeout=aiohttp.ClientTimeout(total=3),
            ) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        # Fallback: check if we have API keys configured
        return bool(PROVIDER_CONFIGS["deepseek"]["api_key"])

    def estimate_cost(self, task: TaskInput) -> float:
        model_id = task.context.get("_model_id", self.info.default_model)
        if "ollama" in model_id:
            return 0.0
        est_tokens = task.complexity * 2000
        return round(est_tokens * 0.000002, 4)

    # ── Prompt builders ──────────────────────────────────────

    def _build_system_prompt(self, task: TaskInput) -> str:
        task_type = task.task_type
        prompts = {
            "writing": "你是一位专业的中文内容创作者。输出高质量、结构清晰、可直接发布的文章。",
            "translation": "你是一位专业翻译。准确翻译以下内容，保持原意的同时让中文表达自然流畅。",
            "summary": "你是一位信息提炼专家。精准提取核心要点，输出简洁清晰的摘要。",
            "social_media": "你是一位社交媒体运营专家。创作吸引眼球、适合目标平台的内容，善用表情符号和互动引导。",
        }
        return prompts.get(task_type, prompts["writing"])

    def _build_user_prompt(self, task: TaskInput) -> str:
        parts = [task.description]
        if task.context:
            extra = {k: v for k, v in task.context.items()
                     if not k.startswith("_")}
            if extra:
                parts.append(f"\n\n参考信息:\n{json.dumps(extra, ensure_ascii=False, indent=2)}")
        return "\n".join(parts)

    # ── LLM API calls ────────────────────────────────────────

    async def _call_anthropic_compat(
        self,
        session: aiohttp.ClientSession,
        cfg: dict,
        model: str,
        system: str,
        prompt: str,
    ) -> tuple[str, int]:
        """Call via Anthropic-compatible Messages API (DeepSeek proxy)."""
        url = f"{cfg['api_base']}/anthropic/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": cfg["api_key"],
            "anthropic-version": "2023-06-01",
        }
        body = {
            "model": model,
            "max_tokens": 4096,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with session.post(
            url, json=body, headers=headers,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            data = await resp.json()
            if "error" in data:
                raise RuntimeError(f"API error: {data['error']}")
            content = data.get("content", [{}])
            text = "".join(
                block.get("text", "") for block in content
                if block.get("type") == "text"
            )
            usage = data.get("usage", {})
            tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            return text, tokens

    async def _call_openai_compat(
        self,
        session: aiohttp.ClientSession,
        cfg: dict,
        model: str,
        system: str,
        prompt: str,
    ) -> tuple[str, int]:
        """Call via OpenAI-compatible Chat Completions API."""
        url = f"{cfg['api_base']}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}",
        }
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 4096,
        }
        async with session.post(
            url, json=body, headers=headers,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            data = await resp.json()
            if "error" in data:
                raise RuntimeError(f"API error: {data['error']}")
            choices = data.get("choices", [{}])
            text = choices[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            return text, tokens

    # ── Helpers ──────────────────────────────────────────────

    def _calc_cost(self, model_id: str, tokens: int) -> float:
        """Calculate cost based on model pricing."""
        pricing = {
            "deepseek/pro-1m": 0.000015,  # ~¥0.015/K tokens avg
            "deepseek/flash": 0.0000015,  # ~¥0.0015/K tokens avg
            "ollama/qwen2.5:14b": 0.0,
        }
        rate = pricing.get(model_id, 0.000002)
        return round(tokens * rate, 6)

    def _estimate_confidence(self, text: str) -> float:
        """Simple heuristic confidence estimate based on output quality."""
        if not text or len(text) < 20:
            return 0.3
        if len(text) < 100:
            return 0.6
        # Longer, structured output = higher confidence
        has_structure = any(
            marker in text for marker in ["#", "**", "1.", "- ", "。", "\n\n"]
        )
        return 0.9 if has_structure else 0.75

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
