"""Commerce Worker — AI工具商店运营: listing, pricing, customer service.

Handles e-commerce operations for the user's AI tool shops:
  - AI Tool Suite v1.0 (8合1工具套装)
  - AI tools shop (工具生成与分发)
  - AI tools delivery (工具交付)

Uses LLM calls for copy generation and integrates with platform APIs.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import aiohttp

from ama.workers.base import BaseWorker, TaskInput, TaskOutput, WorkerInfo

logger = logging.getLogger(__name__)

# Paths to the user's AI tool projects
SHOP_PATHS = {
    "suite": Path(os.path.expanduser("~/Desktop/AI-Tool-Suite-v1.0")),
    "shop": Path(os.path.expanduser("~/Desktop/AI-tools-shop")),
    "delivery": Path(os.path.expanduser("~/Desktop/AI-tools-delivery")),
    "rules": Path(os.path.expanduser("~/Desktop/platform-review-rules")),
}

# Known products in the user's portfolio
PRODUCT_CATALOG = {
    "ai-tool-suite": {
        "name": "AI Tool Suite v1.0",
        "description": "8合1 AI工具套装",
        "features": ["AI对话", "图像生成", "文档处理", "代码助手", "翻译", "数据分析", "语音合成", "视频编辑"],
        "target_price_cny": 99,
        "category": "software",
    },
    "ai-roundtable": {
        "name": "AI Roundtable",
        "description": "多AI模型协作讨论工具",
        "features": ["多模型对比", "协作推理", "决策辅助"],
        "target_price_cny": 49,
        "category": "software",
    },
    "platform-review-rules": {
        "name": "平台审核规则库",
        "description": "多平台内容审核规则汇总",
        "features": ["抖音", "小红书", "B站", "微信视频号", "快手"],
        "target_price_cny": 29,
        "category": "digital_goods",
    },
}

# Platform-specific copy templates
PLATFORM_TEMPLATES = {
    "xianyu": {
        "title_max": 30,
        "desc_sections": ["卖点一句话", "功能介绍", "使用场景", "售后说明"],
        "tags_max": 5,
    },
    "xiaohongshu": {
        "title_max": 20,
        "desc_sections": ["痛点引入", "产品亮点", "使用效果", "购买引导"],
        "tags_max": 10,
    },
    "douyin": {
        "title_max": 50,
        "desc_sections": ["吸睛开头", "功能展示", "使用效果", "行动号召"],
        "tags_max": 5,
    },
}


class CommerceWorker(BaseWorker):
    """E-commerce operations worker for AI tool shops.

    Capabilities:
      - listing: Generate optimized product listings per platform
      - pricing: Analyze features → recommend pricing
      - customer_service: Auto-respond to common inquiries
      - order: Process and track orders
    """

    worker_type = "commerce"

    def __init__(self, info: WorkerInfo) -> None:
        super().__init__(info)
        self._session: aiohttp.ClientSession | None = None
        self._catalog = PRODUCT_CATALOG.copy()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def execute(self, task: TaskInput) -> TaskOutput:
        t0 = time.monotonic()
        task_type = task.task_type
        model_id = task.context.get("_model_id", self.info.default_model)

        handlers = {
            "listing": self._handle_listing,
            "pricing": self._handle_pricing,
            "customer_service": self._handle_customer_service,
            "order": self._handle_order,
        }

        handler = handlers.get(task_type, self._handle_generic)
        try:
            result = await handler(task, model_id)
            return self._build_output(
                task_id=task.task_id,
                result=result,
                success=True,
                model_used=model_id,
                tokens_used=result.get("_tokens", 500),
                cost_yuan=self._calc_cost(model_id, result.get("_tokens", 500)),
                start_time=t0,
                confidence=0.85,
            )
        except Exception as exc:
            logger.error("CommerceWorker error: %s", exc)
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
        """Check if shop directories exist and tools are accessible."""
        for key, path in SHOP_PATHS.items():
            if path.exists():
                return True
        return False  # No shops found

    def estimate_cost(self, task: TaskInput) -> float:
        model_id = task.context.get("_model_id", self.info.default_model)
        est_tokens = 2000
        return self._calc_cost(model_id, est_tokens)

    # ── Task Handlers ──────────────────────────────────────────

    async def _handle_listing(self, task: TaskInput, model_id: str) -> dict:
        """Generate a product listing optimized for a specific platform."""
        product_id = task.context.get("product", "ai-tool-suite")
        platform = task.context.get("platform", "xianyu")
        language = task.context.get("language", "zh")

        product = self._catalog.get(product_id, self._catalog["ai-tool-suite"])
        template = PLATFORM_TEMPLATES.get(platform, PLATFORM_TEMPLATES["xianyu"])

        # Generate listing copy via LLM
        prompt = self._build_listing_prompt(product, template, platform, language)
        copy_text = await self._call_llm(model_id, prompt, json_mode=False)

        return {
            "product": product["name"],
            "platform": platform,
            "title": copy_text.split("\n")[0][:template["title_max"]] if copy_text else product["name"],
            "description": copy_text,
            "tags": self._extract_tags(product, platform),
            "price_cny": product["target_price_cny"],
            "generated_at": time.strftime("%Y-%m-%d %H:%M"),
            "_tokens": len(prompt) // 4 + len(copy_text) // 4,
        }

    async def _handle_pricing(self, task: TaskInput, model_id: str) -> dict:
        """Analyze product features and recommend pricing."""
        product_id = task.context.get("product", "ai-tool-suite")
        product = self._catalog.get(product_id, self._catalog["ai-tool-suite"])
        competitor_price = task.context.get("competitor_price", None)

        prompt = (
            f"你是一位AI产品定价专家。分析以下产品并推荐最佳定价策略：\n\n"
            f"产品：{product['name']}\n"
            f"描述：{product['description']}\n"
            f"功能：{', '.join(product['features'])}\n"
            f"当前目标价：¥{product['target_price_cny']}\n"
            f"{'竞品价格：' + str(competitor_price) if competitor_price else ''}\n\n"
            f"输出JSON格式：\n"
            f'{{"recommended_price": 数字, "strategy": "策略名称", '
            f'"reasoning": "定价理由", "upsell_price": 数字, '
            f'"bundle_suggestion": "捆绑销售建议"}}'
        )

        response = await self._call_llm(model_id, prompt, json_mode=True)
        try:
            pricing = json.loads(response)
        except json.JSONDecodeError:
            pricing = {
                "recommended_price": product["target_price_cny"],
                "strategy": "cost-plus",
                "reasoning": "基于功能数量和开发成本的定价",
            }

        return {
            **pricing,
            "product": product["name"],
            "_tokens": len(prompt) // 4 + len(response) // 4,
        }

    async def _handle_customer_service(self, task: TaskInput, model_id: str) -> dict:
        """Generate customer service response."""
        inquiry = task.description
        product_id = task.context.get("product", "ai-tool-suite")
        product = self._catalog.get(product_id, self._catalog["ai-tool-suite"])
        tone = task.context.get("tone", "专业友善")

        prompt = (
            f"你是「{product['name']}」的客服。用{tone}的语气回复客户问题。\n\n"
            f"产品信息：\n"
            f"- 名称：{product['name']}\n"
            f"- 功能：{', '.join(product['features'])}\n"
            f"- 价格：¥{product['target_price_cny']}\n\n"
            f"常见FAQ参考：\n"
            f"Q: 支持退款吗？ A: 购买后7天内支持无理由退款。\n"
            f"Q: 如何安装？ A: 下载后双击运行，无需安装。\n"
            f"Q: 支持Mac吗？ A: 当前仅支持Windows 10/11。\n\n"
            f"客户消息：{inquiry}\n\n"
            f"请直接回复客户（50-200字）："
        )

        reply = await self._call_llm(model_id, prompt, json_mode=False)

        return {
            "inquiry": inquiry[:200],
            "reply": reply,
            "product": product["name"],
            "tone": tone,
            "_tokens": len(prompt) // 4 + len(reply) // 4,
        }

    async def _handle_order(self, task: TaskInput, model_id: str) -> dict:
        """Process an order (simulated — Phase 2 scope)."""
        product_id = task.context.get("product", "ai-tool-suite")
        quantity = task.context.get("quantity", 1)
        product = self._catalog.get(product_id, self._catalog["ai-tool-suite"])

        total = product["target_price_cny"] * quantity

        return {
            "order_id": f"AMA-{int(time.time())}",
            "product": product["name"],
            "quantity": quantity,
            "unit_price_cny": product["target_price_cny"],
            "total_cny": total,
            "status": "confirmed",
            "delivery_method": "digital_download",
            "_tokens": 0,
        }

    async def _handle_generic(self, task: TaskInput, model_id: str) -> dict:
        """Generic commerce task handler."""
        return {
            "message": f"Commerce task '{task.task_type}' processed",
            "description": task.description[:200],
            "_tokens": 100,
        }

    # ── LLM Integration ───────────────────────────────────────

    async def _call_llm(self, model_id: str, prompt: str,
                        json_mode: bool = False) -> str:
        """Call LLM API for commerce tasks."""
        if "ollama" in model_id:
            return await self._call_ollama(prompt, json_mode)
        else:
            return await self._call_deepseek(prompt, json_mode)

    async def _call_deepseek(self, prompt: str, json_mode: bool) -> str:
        """Call DeepSeek API."""
        session = await self._get_session()
        api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN",
                                 os.environ.get("DEEPSEEK_API_KEY", ""))
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        body = {
            "model": "deepseek-v4-flash",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048 if not json_mode else 1024,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        async with session.post(
            "https://api.deepseek.com/v1/chat/completions",
            json=body, headers=headers,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            data = await resp.json()
            if "error" in data:
                raise RuntimeError(f"DeepSeek API error: {data['error']}")
            return data["choices"][0]["message"]["content"]

    async def _call_ollama(self, prompt: str, json_mode: bool) -> str:
        """Call local Ollama model."""
        session = await self._get_session()
        body = {
            "model": "qwen2.5:14b",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 1024},
        }

        async with session.post(
            "http://localhost:11434/api/generate",
            json=body,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            data = await resp.json()
            return data.get("response", "")

    # ── Helpers ────────────────────────────────────────────────

    def _build_listing_prompt(self, product: dict, template: dict,
                              platform: str, language: str) -> str:
        lang_instr = "用中文撰写" if language == "zh" else "Write in English"
        sections = "\n".join(f"{i+1}. {s}" for i, s in enumerate(template["desc_sections"]))

        return (
            f"你是一位{platform}电商平台的专业文案撰写人。{lang_instr}。\n\n"
            f"产品：{product['name']}\n"
            f"描述：{product['description']}\n"
            f"功能：{', '.join(product['features'])}\n"
            f"价格：¥{product['target_price_cny']}\n\n"
            f"请按以下结构撰写产品描述（每段1-3句话，总计150-300字）：\n"
            f"{sections}\n\n"
            f"标题最多{template['title_max']}字。\n"
            f"第一行是标题（加粗），空一行后开始正文。"
        )

    def _extract_tags(self, product: dict, platform: str) -> list[str]:
        base_tags = ["AI工具", "效率工具", product["name"]]
        platform_tags = {
            "xianyu": ["数码", "软件"],
            "xiaohongshu": ["AI神器", "效率提升", "办公必备", "数码好物"],
            "douyin": ["AI", "黑科技", "效率"],
        }
        tags = base_tags + platform_tags.get(platform, [])
        return tags[:PLATFORM_TEMPLATES.get(platform, {}).get("tags_max", 5)]

    def _calc_cost(self, model_id: str, tokens: int) -> float:
        pricing = {
            "deepseek/pro-1m": 0.000015,
            "deepseek/flash": 0.0000015,
            "ollama/qwen2.5:14b": 0.0,
        }
        return round(tokens * pricing.get(model_id, 0.000002), 6)

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
