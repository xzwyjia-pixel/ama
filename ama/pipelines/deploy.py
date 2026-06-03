"""Deploy Pipeline — 一键上架准备，从文案到发布清单。

Usage:
    python -m ama.main --pipeline deploy
"""

from __future__ import annotations

import json
import os
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

DEPLOY_KIT = r"""# AMA 上架部署包
> 生成时间: {timestamp}
> 包含: 3个产品 × 5个平台 = 15套完整上架文案

---

## 上架前准备

### 1. 注册账号 (如尚未注册)
- [闲鱼](https://2.taobao.com) — 支付宝登录即用
- [小红书](https://www.xiaohongshu.com) — 手机号注册，需实名
- [抖音](https://www.douyin.com) — 手机号注册，开通橱窗需1000粉丝(可先发内容)
- [B站](https://www.bilibili.com) — 注册后开通工房/专栏
- [微信视频号](https://channels.weixin.qq.com) — 微信直接开通

### 2. 产品准备
- [ ] 准备产品截图(主图3-5张 + 详情图)
- [ ] 准备演示视频(可选, 抖音/B站推荐)
- [ ] 收款方式: 支付宝/微信收款码

### 3. 定价策略
| 平台 | AI Tool Suite (¥99) | AI Roundtable (¥49) | 规则库 (¥29) |
|------|---------------------|---------------------|---------------|
| 闲鱼 | ¥79-99 | ¥39-49 | ¥19-29 |
| 小红书 | ¥99 | ¥49 | ¥29 |
| 抖音 | ¥99 (橱窗) | ¥49 (橱窗) | ¥29 (橱窗) |
| B站 | ¥99 | ¥49 | ¥29 |
| 视频号 | ¥99 | ¥49 | ¥29 |

> 闲鱼建议标价比其他平台低10-20%以获取流量倾斜

---

## 各平台上架指引

### 闲鱼
1. 打开闲鱼APP → 底部"卖闲置"
2. 选"发闲置" → 上传图片
3. 复制下方对应文案 → 粘贴标题和描述
4. 价格参考定价策略表
5. 标签: 复制下方标签
6. 发布！

### 小红书
1. 小红书APP → 底部"+"→ 选"图文"
2. 上传产品截图(建议6-9张)
3. 复制文案(标题≤20字)
4. 添加话题标签
5. 发布笔记

### 抖音
1. 抖音APP → 底部"+"→ 发布图文/视频
2. 如需挂商品链接需开通橱窗(1000粉+实名)
3. 初期可先发布内容引流，评论区引导私信

### B站
1. B站 → 专栏投稿 → 写文章
2. 复制文案 → 粘贴
3. 添加封面图
4. 发布！

### 微信视频号
1. 微信 → 发现 → 视频号 → 发表
2. 可以发图文动态或视频
3. 配合朋友圈和微信群推广

---

## 上架节奏建议

| 日期 | 动作 |
|------|------|
| Day 1 | 闲鱼上架3个产品 (最快出单) |
| Day 2 | 小红书发布3篇笔记 |
| Day 3 | B站发布专栏 + 抖音发短视频 |
| Day 4 | 视频号发布 + 朋友圈推广 |
| Day 5 | 查看数据，优化标题/价格 |
| Day 6-7 | 各平台回复咨询，出单发货 |

---

## 发货流程
1. 买家下单 → 发送下载链接
2. 推荐用百度网盘/阿里云盘/蓝奏云
3. 或直接微信/邮箱发送安装包
4. 售后: 7天无理由退款承诺

---

## 收益追踪

| 平台 | 产品 | 上架日期 | 浏览量 | 咨询量 | 销量 | 收入 |
|------|------|----------|--------|--------|------|------|
| 闲鱼 | Suite | | | | | |
| 闲鱼 | Roundtable | | | | | |
| 闲鱼 | 规则库 | | | | | |
| 小红书 | Suite | | | | | |
| ... | ... | | | | | |

---

{listing_previews}
"""


def generate_deploy_kit(listings_dir: str = "ama/output/listings") -> Path:
    """Generate a complete deployment kit with listings and instructions."""
    listings_path = Path(listings_dir)

    # Read generated listings
    all_json = listings_path / "all_listings.json"
    if not all_json.exists():
        raise FileNotFoundError(
            "No listings found. Run: python -m ama.main --pipeline shop"
        )

    listings = json.loads(all_json.read_text(encoding="utf-8"))

    # Build preview section
    previews = []
    for product_id, platform_listings in listings.items():
        previews.append(f"### {product_id}\n")
        for l in platform_listings:
            previews.append(
                f"#### {l['platform']}\n"
                f"**标题**: {l['title']}\n\n"
                f"**价格**: ¥{l['price_cny']}\n\n"
                f"**标签**: {' · '.join(l['tags'])}\n\n"
                f"{l['description']}\n\n"
                f"---\n"
            )

    kit = DEPLOY_KIT.format(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        listing_previews="\n".join(previews),
    )

    out = Path("c:/Users/25454/业务中控台/ama/output/deploy_kit.md")
    out.write_text(kit, encoding="utf-8")
    return out


def generate_product_images_guide() -> str:
    """Generate a guide for creating product listing images."""
    return """
# 产品图制作指南

## 需要的图片 (每个产品)

### 主图 (1张) — 用于列表页展示
- 尺寸: 800×800px (1:1)
- 内容: 产品名称 + 核心卖点 + 价格
- 工具: Canva / 美图秀秀 / PPT都可以
- 示例文案: "8合1 AI工具套装 ¥99"

### 详情图 (3-5张)
1. 功能介绍图 — 列出8大功能模块
2. 效果对比图 — 使用前 vs 使用后
3. 使用场景图 — 办公/创作/学习场景
4. 价格优势图 — 一个工具 vs 分开买的价格对比
5. 售后保障图 — 7天退款/永久使用/在线客服

### 视频 (可选)
- 抖音/B站: 15-60秒操作演示
- 录屏: Windows自带录屏或OBS
- 内容: 打开软件→演示1-2个功能→效果展示

## 快速制作工具
- Canva (canva.cn) — 免费模板
- 稿定设计 — 电商主图模板
- Figma — 专业设计(免费)
"""


async def main():
    """Run deploy pipeline."""
    print("\n  上架部署包生成中...\n")

    # Generate deploy kit
    kit = generate_deploy_kit()
    print(f"  [OK] 上架指南: {kit}")

    # Generate image guide
    img_guide = Path("c:/Users/25454/业务中控台/ama/output/image_guide.md")
    img_guide.write_text(generate_product_images_guide(), encoding="utf-8")
    print(f"  [OK] 图片指南: {img_guide}")

    # Verify all listings
    listings_dir = Path("c:/Users/25454/业务中控台/ama/output/listings")
    json_file = listings_dir / "all_listings.json"
    if json_file.exists():
        data = json.loads(json_file.read_text(encoding="utf-8"))
        products = list(data.keys())
        platforms = set()
        for p in data.values():
            for l in p:
                platforms.add(l["platform"])
        print(f"  [OK] {len(products)}个产品 × {len(platforms)}个平台 = "
              f"{sum(len(v) for v in data.values())}套文案")
        print(f"  产品: {', '.join(products)}")
        print(f"  平台: {', '.join(sorted(platforms))}")

    print(f"\n  下一步:")
    print(f"  1. 打开 {kit} 查看上架指南")
    print(f"  2. 打开 {img_guide} 制作产品图片")
    print(f"  3. 复制文案 → 粘贴到各平台 → 发布！\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
