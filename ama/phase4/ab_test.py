"""Phase 4: A/B Testing Engine — test listing variants, track which performs best.

Generates multiple variants of listings, tracks performance metrics,
and identifies winning patterns.

Usage:
    python -m ama.phase4.ab_test --product ai-tool-suite --platform xianyu
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# A/B test variant strategies
VARIANT_STRATEGIES = {
    "price_focus": "强调价格优势和性价比，用数字说话",
    "feature_focus": "详细列出功能点，用技术参数打动用户",
    "emotion_focus": "用场景故事引发共鸣，情感驱动购买",
    "social_proof": "强调用户数量和好评，从众心理",
    "urgency": "限时优惠、限量发售，制造紧迫感",
    "comparison": "和竞品横向对比，突出差异化优势",
}


@dataclass
class ListingVariant:
    """A single A/B test variant."""
    variant_id: str
    product_id: str
    platform: str
    strategy: str
    title: str
    description: str
    tags: list[str]
    price_cny: int
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    active: bool = True

    @property
    def ctr(self) -> float:
        """Click-through rate."""
        return self.clicks / max(self.impressions, 1)

    @property
    def cvr(self) -> float:
        """Conversion rate."""
        return self.conversions / max(self.clicks, 1)

    @property
    def score(self) -> float:
        """Composite performance score."""
        return (self.ctr * 0.3 + self.cvr * 0.5 + (self.revenue / max(self.impressions, 1)) * 100) * 0.2


class ABTestEngine:
    """A/B test engine for listing optimization.

    Usage:
        engine = ABTestEngine(llm_call_func)
        variants = await engine.generate_variants("ai-tool-suite", "xianyu")
        engine.record_performance(variant_id, impressions=100, clicks=5, conversions=1)
        winner = engine.get_winner("ai-tool-suite", "xianyu")
    """

    def __init__(
        self,
        llm_call_func=None,
        db_path: str = "c:/Users/25454/业务中控台/ama/data/ama.db",
    ):
        self._llm = llm_call_func
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ab_variants (
                    variant_id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    title TEXT,
                    description TEXT,
                    tags TEXT DEFAULT '[]',
                    price_cny INTEGER DEFAULT 0,
                    impressions INTEGER DEFAULT 0,
                    clicks INTEGER DEFAULT 0,
                    conversions INTEGER DEFAULT 0,
                    revenue REAL DEFAULT 0.0,
                    active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

    async def generate_variants(
        self,
        product_id: str,
        platform: str,
        strategies: list[str] | None = None,
    ) -> list[ListingVariant]:
        """Generate A/B test variants for a product on a platform.

        Args:
            product_id: Product to test
            platform: Target platform
            strategies: Which variant strategies to use (default: top 3)
        """
        from ama.pipelines.shop import PRODUCTS, PLATFORMS

        product = PRODUCTS.get(product_id, PRODUCTS["ai-tool-suite"])
        platform_info = PLATFORMS.get(platform, PLATFORMS["xianyu"])

        if strategies is None:
            strategies = ["price_focus", "feature_focus", "emotion_focus"]

        variants = []
        for strategy in strategies:
            variant_id = f"ab-{product_id}-{platform}-{strategy}-{int(time.time())}"

            if self._llm:
                title, desc, tags = await self._llm_variant(
                    product, platform_info, platform, strategy,
                )
            else:
                title, desc, tags = self._template_variant(
                    product, platform_info, platform, strategy,
                )

            variant = ListingVariant(
                variant_id=variant_id,
                product_id=product_id,
                platform=platform,
                strategy=strategy,
                title=title[:platform_info["title_max"]],
                description=desc,
                tags=tags,
                price_cny=product["price"],
            )
            variants.append(variant)
            self._save_variant(variant)

        logger.info(
            "Generated %d variants for %s on %s",
            len(variants), product_id, platform,
        )
        return variants

    async def _llm_variant(
        self, product: dict, platform: dict, pkey: str, strategy: str,
    ) -> tuple[str, str, list[str]]:
        strategy_desc = VARIANT_STRATEGIES.get(strategy, strategy)
        prompt = (
            f"你是{platform['name']}电商文案专家。\n"
            f"策略：{strategy_desc}\n\n"
            f"产品：{product['name']} — {product['tagline']}\n"
            f"功能：{', '.join(product['features'])}\n"
            f"价格：¥{product['price']}\n"
            f"文案风格：{platform['desc_style']}\n"
            f"标题≤{platform['title_max']}字\n\n"
            f"用{strategy_desc}的策略撰写商品文案。\n"
            f"输出JSON: {{\"title\": \"...\", \"description\": \"...\", \"tags\": [...]}}"
        )
        response = await self._llm(prompt, json_mode=True)
        data = json.loads(response)
        return data["title"], data["description"], data.get("tags", [])

    def _template_variant(
        self, product: dict, platform: dict, pkey: str, strategy: str,
    ) -> tuple[str, str, list[str]]:
        strategy_prefix = {
            "price_focus": f"仅¥{product['price']}! 超值{product['name']}",
            "feature_focus": f"{product['name']} — {len(product['features'])}大核心功能详解",
            "emotion_focus": f"用了{product['name']}之后，我再也不用...",
            "social_proof": f"1000+用户推荐的{product['name']}",
            "urgency": f"限时{product['price']}元! {product['name']}最后3天",
            "comparison": f"{product['name']} vs 竞品: 为什么选它?",
        }
        title = strategy_prefix.get(strategy, product['tagline'])[:platform["title_max"]]
        desc = f"【{product['name']}】\n{product['description']}\n\n"
        desc += "\n".join(f"  • {f}" for f in product["features"])
        desc += f"\n\n💰 价格: ¥{product['price']}"
        tags = [product["category"], product["name"].split()[0], strategy]
        return title, desc, tags[:platform["tags_max"]]

    def record_performance(
        self,
        variant_id: str,
        impressions: int = 0,
        clicks: int = 0,
        conversions: int = 0,
        revenue: float = 0.0,
    ) -> None:
        """Record performance data for a variant."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """UPDATE ab_variants SET
                   impressions = impressions + ?,
                   clicks = clicks + ?,
                   conversions = conversions + ?,
                   revenue = revenue + ?
                   WHERE variant_id = ?""",
                (impressions, clicks, conversions, revenue, variant_id),
            )
            conn.commit()

    def get_winner(self, product_id: str, platform: str) -> ListingVariant | None:
        """Get the best-performing variant for a product/platform combo."""
        variants = self._load_variants(product_id, platform)
        if not variants:
            return None
        return max(variants, key=lambda v: v.score)

    def get_report(self, product_id: str, platform: str) -> dict[str, Any]:
        """Get A/B test performance report."""
        variants = self._load_variants(product_id, platform)
        if not variants:
            return {"product": product_id, "platform": platform, "variants": []}

        winner = max(variants, key=lambda v: v.score)
        return {
            "product": product_id,
            "platform": platform,
            "total_impressions": sum(v.impressions for v in variants),
            "total_clicks": sum(v.clicks for v in variants),
            "total_conversions": sum(v.conversions for v in variants),
            "total_revenue": sum(v.revenue for v in variants),
            "winner_strategy": winner.strategy,
            "winner_score": round(winner.score, 4),
            "variants": [
                {
                    "strategy": v.strategy,
                    "title": v.title[:50],
                    "impressions": v.impressions,
                    "clicks": v.clicks,
                    "conversions": v.conversions,
                    "ctr": round(v.ctr, 4),
                    "cvr": round(v.cvr, 4),
                    "score": round(v.score, 4),
                }
                for v in sorted(variants, key=lambda x: x.score, reverse=True)
            ],
        }

    def _save_variant(self, variant: ListingVariant) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO ab_variants
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    variant.variant_id, variant.product_id, variant.platform,
                    variant.strategy, variant.title, variant.description,
                    json.dumps(variant.tags, ensure_ascii=False),
                    variant.price_cny, variant.impressions, variant.clicks,
                    variant.conversions, variant.revenue,
                    1 if variant.active else 0, variant.created_at,
                ),
            )
            conn.commit()

    def _load_variants(self, product_id: str, platform: str) -> list[ListingVariant]:
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                """SELECT * FROM ab_variants
                   WHERE product_id = ? AND platform = ? AND active = 1
                   ORDER BY created_at DESC""",
                (product_id, platform),
            ).fetchall()

        variants = []
        for row in rows:
            v = ListingVariant(
                variant_id=row[0], product_id=row[1], platform=row[2],
                strategy=row[3], title=row[4], description=row[5],
                tags=json.loads(row[6]), price_cny=row[7],
                impressions=row[8], clicks=row[9], conversions=row[10],
                revenue=row[11], active=bool(row[12]), created_at=row[13],
            )
            variants.append(v)
        return variants
