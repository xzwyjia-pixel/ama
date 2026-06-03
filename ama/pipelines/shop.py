"""Shop Automation Pipeline — one-click listing generation for all products × platforms.

Generates platform-optimized product copy, pricing, and tags.
Output: ready-to-publish listing packages.

Usage:
    python -m ama.pipelines.shop
    python -m ama.pipelines.shop --product ai-tool-suite --platform xianyu
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Product Catalog ───────────────────────────────────────────

PRODUCTS = {
    "ai-tool-suite": {
        "id": "ai-tool-suite",
        "name": "AI Tool Suite v1.0",
        "tagline": "8合1 AI工具套装，一个工具搞定所有AI需求",
        "description": "集AI对话、图像生成、文档处理、代码助手、翻译、数据分析、语音合成、视频编辑于一体的全能AI工具箱",
        "features": [
            "AI智能对话 — 支持多模型切换",
            "AI图像生成 — 一键出图，风格多样",
            "文档智能处理 — PDF/Word一键分析",
            "代码助手 — 自动补全、Bug修复、代码审查",
            "多语言翻译 — 50+语言互译",
            "数据分析 — 表格识别、图表生成",
            "语音合成 — 文本转语音，多音色可选",
            "视频编辑 — AI剪辑、自动字幕",
        ],
        "price": 99,
        "category": "效率工具",
        "target_users": ["学生", "上班族", "创作者", "开发者", "自媒体人"],
    },
    "ai-roundtable": {
        "id": "ai-roundtable",
        "name": "AI Roundtable",
        "tagline": "多AI模型协作讨论，让不同AI互相辩论帮你做出最佳决策",
        "description": "同时调用多个AI模型对同一问题进行分析和辩论，综合各方观点给出最优解",
        "features": [
            "多模型同时响应 — 对比不同AI的观点",
            "自动辩论模式 — AI之间互相质疑和完善",
            "决策辅助 — 综合多模型输出最优方案",
            "支持模型 — GPT/Claude/DeepSeek/本地模型",
        ],
        "price": 49,
        "category": "决策工具",
        "target_users": ["决策者", "研究员", "产品经理", "创业者"],
    },
    "platform-review-rules": {
        "id": "platform-review-rules",
        "name": "平台审核规则库",
        "tagline": "多平台内容审核规则一键查询，发内容不再踩坑",
        "description": "汇总抖音、小红书、B站、微信视频号、快手五大平台的审核规则，帮你规避内容风险",
        "features": [
            "抖音审核规则 — 限流/违规/封禁红线",
            "小红书审核规则 — 笔记限流/禁词/品类限制",
            "B站审核规则 — 稿件审核/分区规则/创作激励",
            "微信视频号 — 内容规范/直播规则/变现门槛",
            "快手审核规则 — 社区规范/电商规则/流量机制",
        ],
        "price": 29,
        "category": "知识付费",
        "target_users": ["自媒体人", "电商运营", "内容创作者", "品牌方"],
    },
}

# Platform-specific configurations
PLATFORMS = {
    "xianyu": {
        "name": "闲鱼",
        "title_max": 30,
        "desc_style": "直接卖点+功能罗列+信任背书",
        "tags_max": 5,
        "price_tip": "设置比竞品低10-20%的价格更容易卖出",
    },
    "xiaohongshu": {
        "name": "小红书",
        "title_max": 20,
        "desc_style": "痛点引入+产品亮点+使用效果+引导私信",
        "tags_max": 10,
        "price_tip": "强调性价比和使用场景",
    },
    "douyin": {
        "name": "抖音",
        "title_max": 50,
        "desc_style": "吸睛开头+功能展示+效果对比+橱窗引导",
        "tags_max": 5,
        "price_tip": "适合用短视频展示功能后再挂链接",
    },
    "bilibili": {
        "name": "B站",
        "title_max": 80,
        "desc_style": "技术向介绍+实际演示+横向对比+评论区互动",
        "tags_max": 10,
        "price_tip": "强调技术含量和性价比，适合专栏带货",
    },
    "weixin": {
        "name": "微信视频号",
        "title_max": 30,
        "desc_style": "场景化描述+信任背书+限时优惠+私域引导",
        "tags_max": 5,
        "price_tip": "配合朋友圈和社群推广效果更佳",
    },
}


@dataclass
class ListingResult:
    """A single product listing for one platform."""
    product_id: str
    product_name: str
    platform: str
    title: str
    description: str
    tags: list[str]
    price_cny: int
    generated_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M"))


class ShopPipeline:
    """Automated product listing pipeline.

    Usage:
        pipeline = ShopPipeline(llm_call_func)
        results = await pipeline.generate_all()
        pipeline.export(results, "output/listings/")
    """

    def __init__(self, llm_call_func=None):
        self._llm = llm_call_func
        self.results: dict[str, list[ListingResult]] = {}  # product_id → listings

    async def generate_all(
        self,
        products: list[str] | None = None,
        platforms: list[str] | None = None,
    ) -> dict[str, list[ListingResult]]:
        """Generate listings for all products across all platforms.

        Args:
            products: Product IDs to include (default: all)
            platforms: Platform keys to include (default: all)

        Returns:
            {product_id: [ListingResult, ...]}
        """
        product_ids = products or list(PRODUCTS.keys())
        platform_keys = platforms or list(PLATFORMS.keys())

        total = len(product_ids) * len(platform_keys)
        print(f"\n🛍️  Shop Pipeline: {len(product_ids)} products × {len(platform_keys)} platforms = {total} listings\n")

        for i, pid in enumerate(product_ids):
            product = PRODUCTS[pid]
            self.results[pid] = []

            for j, pkey in enumerate(platform_keys):
                platform = PLATFORMS[pkey]
                idx = i * len(platform_keys) + j + 1

                print(f"  [{idx}/{total}] {product['name']} → {platform['name']}...", end=" ")

                listing = await self._generate_listing(product, platform, pkey)
                self.results[pid].append(listing)

                print(f"✓ ({listing.title[:30]}...)")

        print(f"\n✅ {total} listings generated!\n")
        return self.results

    async def generate_one(
        self, product_id: str, platform_key: str,
    ) -> ListingResult:
        """Generate a single listing for one product on one platform."""
        product = PRODUCTS.get(product_id, PRODUCTS["ai-tool-suite"])
        platform = PLATFORMS.get(platform_key, PLATFORMS["xianyu"])
        return await self._generate_listing(product, platform, platform_key)

    async def _generate_listing(
        self, product: dict, platform: dict, pkey: str,
    ) -> ListingResult:
        """Generate a listing using LLM if available, else template-based."""
        if self._llm:
            try:
                title, desc, tags = await self._llm_generate(product, platform, pkey)
            except Exception:
                title, desc, tags = self._template_generate(product, platform, pkey)
        else:
            title, desc, tags = self._template_generate(product, platform, pkey)

        return ListingResult(
            product_id=product["id"],
            product_name=product["name"],
            platform=platform["name"],
            title=title[:platform["title_max"]] if platform["title_max"] else title,
            description=desc,
            tags=tags,
            price_cny=product["price"],
        )

    async def _llm_generate(
        self, product: dict, platform: dict, pkey: str,
    ) -> tuple[str, str, list[str]]:
        """LLM-powered listing generation."""
        prompt = (
            f"你是{platform['name']}平台的专业电商文案。\n\n"
            f"产品：{product['name']}（{product['tagline']}）\n"
            f"价格：¥{product['price']}\n"
            f"功能：\n" + "\n".join(f"- {f}" for f in product["features"]) + "\n\n"
            f"文案风格：{platform['desc_style']}\n"
            f"标题最多{platform['title_max']}字\n\n"
            f"输出JSON格式：\n"
            f'{{"title": "标题", "description": "正文(150-300字)", "tags": ["标签1", "标签2", ...]}}'
        )
        response = await self._llm(prompt, json_mode=True)
        data = json.loads(response)
        return data["title"], data["description"], data.get("tags", [])

    def _template_generate(
        self, product: dict, platform: dict, pkey: str,
    ) -> tuple[str, str, list[str]]:
        """Template-based listing generation (no LLM required)."""
        title = f"{product['name']} | {product['tagline']}"[:platform["title_max"]]

        desc = (
            f"【{product['name']}】{product['tagline']}\n\n"
            f"📦 {product['description']}\n\n"
            f"✨ 核心功能：\n" +
            "\n".join(f"  • {f}" for f in product["features"]) +
            f"\n\n🎯 适合人群：{'、'.join(product['target_users'])}\n\n"
            f"💰 价格：¥{product['price']}\n"
            f"📥 下单即发，自动发货\n"
            f"💬 有任何问题欢迎私信咨询"
        )

        tags = [product["category"], product["name"].split()[0] if " " in product["name"] else product["name"]]
        tags += product["target_users"][:3]
        tags = tags[:platform["tags_max"]]

        return title, desc, tags

    def export(self, output_dir: str = "output/listings") -> Path:
        """Export all generated listings to files.

        Creates:
          output_dir/
            all_listings.json     — All listings in machine-readable format
            all_listings.md       — All listings in human-readable markdown
            {product_id}/         — Per-product directories
              {platform}.md       — Platform-specific listing
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # JSON export (machine-readable)
        json_data = {}
        for pid, listings in self.results.items():
            json_data[pid] = [
                {
                    "product": l.product_name,
                    "platform": l.platform,
                    "title": l.title,
                    "description": l.description,
                    "tags": l.tags,
                    "price_cny": l.price_cny,
                    "generated_at": l.generated_at,
                }
                for l in listings
            ]
        (out / "all_listings.json").write_text(
            json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8",
        )

        # Markdown export (human-readable)
        md_lines = ["# AMA Shop Listings\n", f"Generated: {time.strftime('%Y-%m-%d %H:%M')}\n"]
        for pid, listings in self.results.items():
            product = PRODUCTS[pid]
            md_lines.append(f"\n## {product['name']} — ¥{product['price']}\n")
            for l in listings:
                md_lines.append(f"### {l.platform}\n")
                md_lines.append(f"**标题**: {l.title}\n")
                md_lines.append(f"**标签**: {' · '.join(l.tags)}\n")
                md_lines.append(f"**价格**: ¥{l.price_cny}\n")
                md_lines.append(f"\n{l.description}\n")
                md_lines.append("---\n")
        (out / "all_listings.md").write_text("\n".join(md_lines), encoding="utf-8")

        # Per-product per-platform export
        for pid, listings in self.results.items():
            prod_dir = out / pid
            prod_dir.mkdir(exist_ok=True)
            for l in listings:
                platform_file = prod_dir / f"{_safe_filename(l.platform)}.md"
                platform_file.write_text(
                    f"# {l.product_name} — {l.platform}\n\n"
                    f"**标题**: {l.title}\n\n"
                    f"**价格**: ¥{l.price_cny}\n\n"
                    f"**标签**: {' · '.join(l.tags)}\n\n"
                    f"{l.description}\n",
                    encoding="utf-8",
                )

        logger.info("Exported %d listings to %s", sum(len(v) for v in self.results.values()), out)
        return out


def _safe_filename(name: str) -> str:
    return name.replace(" ", "_").replace("/", "_").lower()


# ── Standalone runner ─────────────────────────────────────────

async def _llm_wrapper(prompt: str, json_mode: bool = False) -> str:
    """LLM call wrapper using DeepSeek API."""
    import aiohttp
    api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN",
                             os.environ.get("DEEPSEEK_API_KEY", ""))
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    body = {
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.deepseek.com/v1/chat/completions",
            json=body, headers=headers,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            data = await resp.json()
            return data["choices"][0]["message"]["content"]


async def main():
    """Run shop pipeline standalone."""
    # Use LLM if API key is available
    api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN",
                             os.environ.get("DEEPSEEK_API_KEY", ""))
    llm = _llm_wrapper if api_key else None

    pipeline = ShopPipeline(llm_call_func=llm)
    results = await pipeline.generate_all()
    out = pipeline.export("c:/Users/25454/业务中控台/ama/output/listings")
    print(f"📁 Exported to: {out}")


if __name__ == "__main__":
    asyncio.run(main())
