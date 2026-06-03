"""Content Operations Pipeline — automated content creation from topic to publish-ready.

Pipeline: topic → outline → draft → polish → platform-adapt → publish package

Usage:
    python -m ama.pipelines.content --topic "AI工具推荐"
    python -m ama.pipelines.content --batch --count 7  # Generate 7 pieces
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Content types and their platform configurations
CONTENT_TYPES = {
    "wechat_article": {
        "name": "公众号文章",
        "length": "800-1500字",
        "style": "深度长文，干货+观点+案例",
        "structure": ["标题(吸引点击)", "引言(痛点引入)", "正文(分3-5个小标题)", "总结", "引导关注"],
    },
    "xiaohongshu_note": {
        "name": "小红书笔记",
        "length": "300-500字",
        "style": "真实分享感，emoji丰富，话题标签",
        "structure": ["封面标题", "痛点/场景引入", "核心观点(3-5条)", "个人体验", "行动建议", "话题标签"],
    },
    "douyin_script": {
        "name": "抖音口播脚本",
        "length": "200-300字(约60秒)",
        "style": "口语化，节奏快，前3秒抓眼球",
        "structure": ["Hook(前3秒)", "核心观点", "案例/演示", "反转/升华", "引导互动"],
    },
    "bilibili_column": {
        "name": "B站专栏",
        "length": "1000-2000字",
        "style": "技术向深度内容，数据支撑，适度玩梗",
        "structure": ["封面标题", "引言(为什么写这个)", "正文(技术分析+案例)", "总结+展望", "评论区互动引导"],
    },
}

# Content topics pool (AI/tech focused)
TOPIC_POOL = [
    "2026年最值得推荐的5款AI工具",
    "AI Agent如何改变我们的工作方式",
    "普通人如何利用AI提升3倍工作效率",
    "AI工具对比：ChatGPT vs Claude vs DeepSeek",
    "零基础入门AI：从这些工具开始",
    "AI绘画工具横评：哪款最适合你",
    "如何用AI做自媒体：从0到1实操指南",
    "AI编程助手测评：Claude Code vs GitHub Copilot",
    "2026年AI趋势：Agent时代的到来",
    "避开这些坑：AI工具选购指南",
]


@dataclass
class ContentPiece:
    """A single piece of content through the pipeline."""
    topic: str
    content_type: str
    stage: str  # topic/outline/draft/polish/platform_adapt/done
    title: str = ""
    outline: list[str] = field(default_factory=list)
    draft: str = ""
    polished: str = ""
    platform_version: dict[str, str] = field(default_factory=dict)  # platform → text
    tags: list[str] = field(default_factory=list)
    publish_time_suggestion: str = ""
    generated_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M"))


class ContentPipeline:
    """Automated content creation pipeline.

    Usage:
        pipeline = ContentPipeline(llm_call_func)
        piece = await pipeline.create_piece("AI工具推荐", "wechat_article")
        package = pipeline.export_piece(piece)
    """

    def __init__(self, llm_call_func=None):
        self._llm = llm_call_func
        self.pieces: list[ContentPiece] = []

    async def create_piece(
        self,
        topic: str,
        content_type: str = "wechat_article",
    ) -> ContentPiece:
        """Create a single piece of content through the full pipeline."""
        ct = CONTENT_TYPES.get(content_type, CONTENT_TYPES["wechat_article"])
        piece = ContentPiece(topic=topic, content_type=content_type, stage="topic")

        print(f"\n📝 Content Pipeline: {topic}")
        print(f"   类型: {ct['name']} | {ct['length']}")

        # Stage 1: Generate outline
        piece.stage = "outline"
        outline = await self._generate(topic, "outline", ct)
        piece.outline = self._parse_list(outline)
        print(f"   [1/4] 大纲: {len(piece.outline)}个要点")

        # Stage 2: Generate draft
        piece.stage = "draft"
        draft = await self._generate(topic, "draft", ct, outline)
        piece.draft = draft
        print(f"   [2/4] 初稿: {len(draft)}字")

        # Stage 3: Polish
        piece.stage = "polish"
        polished = await self._generate(topic, "polish", ct, draft)
        piece.polished = polished
        piece.title = polished.split("\n")[0].lstrip("# ").strip() if polished else topic
        print(f"   [3/4] 润色: {len(polished)}字")

        # Stage 4: Platform adaptation
        piece.stage = "platform_adapt"
        for pkey, ptype in CONTENT_TYPES.items():
            if pkey != content_type:
                adapted = await self._adapt_to_platform(piece.polished, content_type, pkey, ptype)
                piece.platform_version[pkey] = adapted
        print(f"   [4/4] 平台适配: {len(piece.platform_version)}个版本")

        piece.stage = "done"
        piece.tags = self._extract_tags(piece)
        piece.publish_time_suggestion = self._suggest_publish_time(content_type)

        self.pieces.append(piece)
        return piece

    async def batch_create(
        self,
        topics: list[str],
        content_type: str = "wechat_article",
    ) -> list[ContentPiece]:
        """Batch create multiple content pieces."""
        pieces = []
        for i, topic in enumerate(topics):
            print(f"\n[{i+1}/{len(topics)}] ", end="")
            piece = await self.create_piece(topic, content_type)
            pieces.append(piece)
        return pieces

    async def _generate(
        self, topic: str, stage: str, ct: dict, context: str = "",
    ) -> str:
        """Generate content using LLM or template."""
        if self._llm:
            prompts = {
                "outline": (
                    f"你是一位资深{ct['name']}写作者。\n"
                    f"为「{topic}」设计一个大纲。\n"
                    f"风格：{ct['style']}\n"
                    f"结构参考：{' → '.join(ct['structure'])}\n"
                    f"输出5-7个要点的列表，每行一个要点。"
                ),
                "draft": (
                    f"根据以下大纲，撰写一篇完整的{ct['name']}。\n"
                    f"主题：{topic}\n"
                    f"大纲：\n{context}\n"
                    f"长度：{ct['length']}\n"
                    f"风格：{ct['style']}\n"
                    f"按此结构组织：{' → '.join(ct['structure'])}"
                ),
                "polish": (
                    f"润色以下{ct['name']}，使其更具吸引力和可读性：\n\n{context}\n\n"
                    f"要求：\n"
                    f"1. 标题要有点击欲望\n"
                    f"2. 开头3句话必须抓住读者\n"
                    f"3. 增加具体案例和数据支撑\n"
                    f"4. 语言生动，避免AI感\n"
                    f"5. 结尾有明确的行动引导"
                ),
            }
            try:
                return await self._llm(prompts.get(stage, ""), json_mode=False)
            except Exception:
                pass
        return self._template_generate(topic, stage, ct, context)

    async def _adapt_to_platform(
        self, source: str, from_type: str, to_key: str, to_type: dict,
    ) -> str:
        """Adapt content from one platform format to another."""
        if self._llm:
            prompt = (
                f"将以下{CONTENT_TYPES[from_type]['name']}改写成{to_type['name']}。\n\n"
                f"原文：\n{source[:1500]}\n\n"
                f"目标平台要求：\n"
                f"- 长度：{to_type['length']}\n"
                f"- 风格：{to_type['style']}\n"
                f"- 结构：{' → '.join(to_type['structure'])}\n\n"
                f"直接输出改写后的内容。"
            )
            try:
                return await self._llm(prompt, json_mode=False)
            except Exception:
                pass
        return f"[{to_type['name']}版本]\n\n{source[:500]}..."

    def _template_generate(self, topic: str, stage: str, ct: dict, context: str) -> str:
        """Template-based generation when no LLM is available."""
        if stage == "outline":
            return "\n".join(
                f"{i+1}. {topic} — 要点{i+1}"
                for i in range(5)
            )
        elif stage in ("draft", "polish"):
            sections = ct["structure"]
            return (
                f"# {topic}\n\n"
                + "\n\n".join(
                    f"## {s}\n\n这是关于{topic}的{s}部分内容。"
                    for s in sections
                )
            )
        return f"# {topic}\n\n内容生成中..."

    def _parse_list(self, text: str) -> list[str]:
        """Parse a numbered/bulleted list from LLM output."""
        lines = text.strip().split("\n")
        items = []
        for line in lines:
            line = line.strip()
            # Remove numbering like "1.", "1)", "-", "•"
            for prefix in ["- ", "• ", "* "]:
                if line.startswith(prefix):
                    line = line[len(prefix):]
                    break
            import re
            line = re.sub(r"^\d+[\.\)]\s*", "", line)
            if len(line) > 5:
                items.append(line)
        return items[:7]

    def _extract_tags(self, piece: ContentPiece) -> list[str]:
        """Extract relevant tags/hashtags."""
        # Simple keyword extraction
        text = (piece.topic + " " + piece.polished).lower()
        tag_keywords = {
            "AI": ["ai", "人工智能", "agent", "智能"],
            "工具": ["工具", "软件", "应用", "tool"],
            "效率": ["效率", "工作", "生产力", "提升"],
            "教程": ["教程", "入门", "指南", "怎么", "如何"],
            "对比": ["对比", "测评", "推荐", "最好", "vs"],
            "趋势": ["趋势", "2026", "未来", "发展"],
        }
        tags = []
        for tag, kws in tag_keywords.items():
            if any(kw in text for kw in kws):
                tags.append(tag)
        return tags + [f"#{piece.content_type}"]

    def _suggest_publish_time(self, content_type: str) -> str:
        """Suggest optimal publish time based on platform."""
        times = {
            "wechat_article": "周二/四 20:00-21:00 (公众号阅读高峰)",
            "xiaohongshu_note": "周一至周五 7:30-8:30 或 12:00-13:00",
            "douyin_script": "工作日 18:00-20:00 (通勤高峰)",
            "bilibili_column": "周末 10:00-12:00 (B站用户活跃时段)",
        }
        return times.get(content_type, "工作日 20:00")

    def export_piece(self, piece: ContentPiece, output_dir: str = "output/content") -> Path:
        """Export a content piece as a publish-ready package."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        filename = _safe_filename(piece.topic[:30])
        package = {
            "topic": piece.topic,
            "type": piece.content_type,
            "title": piece.title,
            "outline": piece.outline,
            "main_content": piece.polished,
            "platform_versions": piece.platform_version,
            "tags": piece.tags,
            "publish_time": piece.publish_time_suggestion,
            "generated_at": piece.generated_at,
        }
        (out / f"{filename}.json").write_text(
            json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8",
        )

        # Markdown export
        md = [
            f"# {piece.title}\n",
            f"**类型**: {CONTENT_TYPES.get(piece.content_type, {}).get('name', piece.content_type)}",
            f"**标签**: {' · '.join(piece.tags)}",
            f"**建议发布时间**: {piece.publish_time_suggestion}",
            f"**生成时间**: {piece.generated_at}\n",
            "---\n",
            piece.polished,
            "\n---\n",
            "## 大纲\n",
        ]
        md.extend(f"- {item}" for item in piece.outline)
        (out / f"{filename}.md").write_text("\n".join(md), encoding="utf-8")

        logger.info("Exported content package: %s", filename)
        return out / f"{filename}.md"

    def export_all(self, output_dir: str = "output/content") -> Path:
        """Export all generated pieces."""
        paths = []
        for piece in self.pieces:
            paths.append(self.export_piece(piece, output_dir))
        return Path(output_dir)


def _safe_filename(text: str) -> str:
    return "".join(c for c in text[:30] if c.isalnum() or c in "._- ").strip().replace(" ", "_")


# ── Standalone runner ─────────────────────────────────────────

async def main():
    """Run content pipeline standalone."""
    import aiohttp

    api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN",
                             os.environ.get("DEEPSEEK_API_KEY", ""))

    async def llm_call(prompt: str, json_mode: bool = False) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        body = {
            "model": "deepseek-v4-flash",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.deepseek.com/v1/chat/completions",
                json=body, headers=headers,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    pipeline = ContentPipeline(llm_call_func=llm_call if api_key else None)

    # Single piece demo
    piece = await pipeline.create_piece(
        "2026年最值得推荐的5款AI效率工具",
        "wechat_article",
    )
    out = pipeline.export_piece(piece, "c:/Users/25454/业务中控台/ama/output/content")
    print(f"\n📁 Exported to: {out}")


if __name__ == "__main__":
    asyncio.run(main())
