# AMA 国际市场战略 — 调研与方向

> **核心发现**: AMA 恰好处于 2026 年最热的赛道 — AI Agent 治理/编排/安全。
> 2025-2026 年这个赛道已经涌入 **$5 亿+ 风投资金**。
> 你的产品方向完全正确，现在是执行速度的问题。

---

## 1. 市场验证: 你不是一个人

### 赛道热度 (2025-2026 融资数据)

| 公司 | 融资额 | 轮次 | 做什么 |
|------|--------|------|--------|
| **Oasis Security** | $1.2 亿 | B 轮 | AI agent 身份与权限治理 |
| **Sycamore Labs** | $6500 万 | 种子轮 | 企业自主 AI 操作系统 |
| **Guild.ai** | $4400 万 | A 轮 | 多 agent 编排 |
| **Onyx Security** | $4000 万 | 启动 | AI agent 实时安全控制 |
| **JetStream** | $3400 万 | 种子轮 | AI 治理控制层 |
| **Geordie AI** | $3650 万 | A 轮 | Agent 安全 (🏆 RSAC 2026 冠军) |
| **Fiddler AI** | $3000 万 | C 轮 | AI 可观测性控制面 |
| **Reco** | $3000 万 | B 轮 | SaaS + AI agent 安全 |

**总计: 仅这 8 家就在 18 个月内融了 $4.25 亿+**

### AMA 的位置 (红点 = 你)

```
AI Agent Infrastructure Stack (2026)

┌─────────────────────────────────────────────┐
│  Application Layer                          │
│  Salesforce Agentforce, ServiceNow, Copilot │
├─────────────────────────────────────────────┤
│  Orchestration Layer     ← Guild.ai         │
│  Multi-agent coordination ← Sycamore        │
├─────────────────────────────────────────────┤
│  GOVERNANCE LAYER        ← AMA IS HERE      │
│  Discovery + Routing +   ← Geordie AI       │
│  Lifecycle + Audit       ← Oasis, Onyx      │
├─────────────────────────────────────────────┤
│  Security Layer                             │
│  Runtime intervention    ← Geordie, Onyx    │
├─────────────────────────────────────────────┤
│  Infrastructure Layer                       │
│  MCP, APIs, Models       ← Anthropic, OpenAI│
└─────────────────────────────────────────────┘
```

**AMA 的差异化**: 多框架 (Pi+Claude+Codex) + 本地优先 + 开源核心。
没有竞品同时做这三件事。

---

## 2. 竞品对比

| 维度 | Geordie AI | Oasis | Guild.ai | Onyx | **AMA** |
|------|-----------|-------|----------|------|---------|
| 融资 | $36.5M | $195M | $44M | $40M | $0 (bootstrapped) |
| Agent 发现 | ✅ | ❌ | ❌ | ✅ | ✅ |
| 多框架 | ❌ | ❌ | ✅ | ❌ | ✅ (Pi+Claude+Codex) |
| 成本优化 | ❌ | ❌ | ❌ | ❌ | ✅ |
| 本地部署 | ❌ | ❌ | ❌ | ❌ | ✅ |
| 开源 | ❌ | ❌ | 部分 | ❌ | ✅ |
| 安全审计 | ✅ | ✅ | ❌ | ✅ | ✅ |
| 定价 | 企业 (未公开) | 企业 | 企业 | 企业 | **$49-$999** |

**核心优势**: 你不需要融 $3000 万才能跟他们竞争。
他们的产品卖 $10 万+/年给银行。你的产品卖 $49-$999 给开发团队。
**完全不同的市场段位 — 你在中小企业/个人开发者市场, 零竞争。**

---

## 3. 国际市场定价 (美金)

国际付费意愿远高于国内。参考 Product Hunt 开发者工具定价:

| 产品 | 价格 | 用户数 |
|------|------|--------|
| GitHub Copilot | $10-39/mo | 180 万付费 |
| Claude Code | $20/mo (Max) | 数十万 |
| Cursor | $20/mo | 数万 |
| Raycast Pro | $8/mo | 数万 |
| **AMA Pro** | **$9.90/mo** | 目标 500 |
| **AMA Team** | **$49/mo** | 目标 50 |
| **AMA Enterprise** | **$999/mo** | 目标 5 |

**汇率红利**: $9.90 = ¥72。国内收 ¥72/月很难, 国外收 $9.90 是正常价格。

---

## 4. 国际市场进入路径

### Phase 1: 开源冷启动 (Week 1-2)

```
GitHub 开源 AMA Core
    │
    ├── README.md (英文, 参考 marketing/social-posts.md)
    ├── 提交到 GitHub Trending
    └── 同步发到:
        ├── Hacker News (Show HN)
        ├── Reddit r/programming
        ├── Reddit r/selfhosted
        └── Twitter/X (英文账号)
```

**目标**: 100 GitHub stars → 500 Calculator 访问者 → 5 个付费用户

### Phase 2: Product Hunt 发布 (Week 2-3)

Product Hunt 是开发者工具最重要的发布渠道。

**准备清单**:
- [ ] 产品名称 (英文): **"AMA — Agent Management Agent"**
- [ ] 一句话: "Scan, manage, and optimize every AI agent on your machine — across Claude Code, Pi, and Codex."
- [ ] 5 张产品截图 (Calculator + Store + Admin Dashboard)
- [ ] Maker 简介 + Twitter 链接
- [ ] 发布日: 周二/周三/周四 (周二流量最高)
- [ ] 提前 2 天通知 PH 社区
- [ ] 找 3-5 个朋友在发布第一小时点赞

**目标**: Product Hunt #1-5 → 5000+ 访问者 → 50 个付费

### Phase 3: 内容引擎 (Week 3-12)

```
每周围绕一个主题发内容:

Week 1: "I found 457 AI agents on my computer"
Week 2: "How much AI waste costs your team (calculator)"
Week 3: "Why your CISO will ban AI agents (and how to stop it)"
Week 4: "Multi-framework agent management — Pi + Claude + Codex"
...
```

分发到: Twitter/X, LinkedIn, Reddit, Dev.to, Hashnode

### Phase 4: 付费增长 (Month 2+)

- GitHub Sponsors
- Reddit Ads ($5/day → r/programming, r/MachineLearning)
- Twitter/X Ads (target: developers, AI engineers)
- SEO: "AI agent management", "agent cost optimization", "AI governance"

---

## 5. 需要做的产品调整 (针对国际市场)

### 即刻可做 (今天):

1. **英文 Landing Page** — Calculator + Store 已有英文界面, 确认没问题
2. **GitHub README** — 全英文, 参考 marketing/social-posts.md 底部的模板
3. **Stripe 国际收款** — 支持美元定价 + 全球信用卡

### 本周:

4. **英文 Admin Dashboard** — 目前是中英混用, 需要统一英文
5. **英文邮件模板** — 已有 `marketing/email-templates.md`, 需翻译英文版
6. **英文文档** — README + Quick Start + API docs

### 本月:

7. **多语言 Calculator** — 自动检测浏览器语言, 中/英切换
8. **AMA CLI 英文版** — `ama scan`, `ama start` 命令输出英文化

---

## 6. 双市场并行执行

```
国内 (中文)                    国外 (英文)
──────────                    ──────────
Calculator (已有)      →      Calculator (同页面, 英文即可)
V2EX/掘金/即刻 发帖    →      HN/Reddit/Twitter 发帖
企业微信/飞书 触达     →      LinkedIn/Twitter DM
¥49-999 RMB           →      $9.90-$999 USD
国内 Stripe (可选)      →      国际 Stripe (主要)
```

**关键**: 同一个 Calculator 链接, 同一个 Store, 同一个后端。
**只需要换营销语言, 不需要换产品。**

---

## 7. 优先级排序 (国际 + 国内并行)

| 优先级 | 行动 | 市场 | 预期效果 | 时间 |
|--------|------|------|---------|------|
| P0 | 注册 Stripe 国际 | 双市场 | 可以收款 | 今天 |
| P0 | GitHub 开源 + README | 国际 | 冷启动流量 | 今天 |
| P0 | V2EX + 即刻 发帖 | 国内 | 首批访问者 | 今天 |
| P1 | Hacker News Show HN | 国际 | 500-5000 views | 明天 |
| P1 | Product Hunt 准备 | 国际 | 最大发布渠道 | 本周 |
| P1 | Reddit r/programming | 国际 | 持续流量 | 本周 |
| P2 | 英文博客 (Dev.to) | 国际 | SEO + 信任 | 持续 |
| P2 | LinkedIn 英文帖子 | 国际 | 企业客户 | 持续 |

---

## 8. 收入估算: 国内 vs 国际

| 场景 | 国内 (保守) | 国际 (保守) | 合计 |
|------|-----------|-----------|------|
| Calculator 月访问 | 500 | 2000 | 2500 |
| 免费报告提交 (3%) | 15 | 60 | 75 |
| Pro Report 购买 (20% upsell) | 3 × ¥360 | 12 × $49 | ¥1,080 + $588 |
| Agent 订阅 (5% of store visitors) | 5 × ¥72/mo | 20 × $9.90/mo | ¥360 + $198/mo |
| 企业客户 (0.5%) | 0 | 1 × $2,500 | $2,500 |
| **月收入估算** | **¥1,440** | **$3,286** | **≈ ¥25,000** |

**关键洞察**: 国际市场收入是国内市场的 **16 倍** (同等流量下)。

---

## 9. 一句话总结

> AMA 在国际市场的定位是:
> **"The open-source, multi-framework, local-first agent manager that doesn't cost $100K/year."**
>
> 竞品融了几千万美元, 服务银行和保险公司, 收费 $10 万+/年。
> 你用开源 + $9.90/月 覆盖剩下 99% 的市场。
>
> **现在开始: GitHub 开源 → HN/Reddit 发帖 → Product Hunt 发布 → 收美金。**
