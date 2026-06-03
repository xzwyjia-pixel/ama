# 全平台审计 + 竞品分析 + 避坑指南 — 2026-06-03

---

## 一、所有平台状态

| 平台 | 状态 | 详情 |
|---|---|---|
| 🟢 **AMA Store** | 在线 | ama-agent-store.vercel.app, 457 agents |
| 🟢 **Agent Business** | 在线 | agent-business-xi.vercel.app, USD定价, Stripe已接入 |
| 🟢 **GitHub** | 公开 | github.com/xzwyjia-pixel/ama, MIT, 10+ commits |
| 🟢 **Dev.to #1** | 在线 | "I scanned my PC and found 457 AI agents" |
| 🟢 **Dev.to #2** | 在线 | "I Scanned My PC for AI Agents — Found 457" |
| 🟢 **Dev.to #3** | 在线 | "I don't know how to code — but built a SaaS in 48h" |
| 🟢 **Dev.to #3** | 🎉 进入Google搜索! | "one person company"查询中出现 |
| 🟢 **Twitter** | 1 thread已发 | 账号临时受限(自动化触发) |
| 🟢 **Stripe** | 已接入 | 3个Payment Links, live模式, SGD结算 |
| 🟢 **Daemon** | 运行中 | localhost:3456, 每日8:30自动生成 |
| 🟡 **HN** | 1个普通链接帖 | rate-limit等待中 |
| 🔴 **Product Hunt** | 未成功 | 同名产品hamr0/ama占据搜索 |
| 🔴 **Reddit** | 2帖全删 | r/selfhosted + r/aiagents |
| 🔴 **n8n Cloud** | 废弃 | 5个工作流无法激活 |

---

## 二、竞品格局

### 直接竞品（Agent管理/编排工具）

| 竞品 | 定价 | 差异化 | 威胁等级 |
|---|---|---|---|
| **Mission Control** | MIT开源 | 32面板SPA, SQLite, 零外部依赖 | 🔴 高 |
| **AirisOS** | 开源 | "OS for AI agents", 企业级 | 🟡 中 |
| **VNX** | 开源 | CLI优先, Merkle审计链 | 🟡 中 |
| **Microsoft AGT** | 开源 | <0.1ms延迟, 5行业场景 | 🟢 低(企业市场) |
| **cc-orchestrator** | 开源 | Claude+Codex双引擎 | 🟡 中 |

### 间接竞品（AI客服/内容/分析）

| 领域 | 头部玩家 | 定价 | 你的优势 |
|---|---|---|---|
| AI客服 | Intercom Fin $0.99/res, Zendesk $1.50-2.00/res | 按量计费 | 你的$799/月对于高频使用更便宜 |
| AI内容 | 无明确"AI内容部门"品类 | — | 你是第一个打出这个定位的 |
| AI分析 | 分散在BI工具中 | — | 5-Agent并行分析是差异化 |

---

## 三、客户痛点映射

| 痛点 | 市场规模 | 你的解决方案 |
|---|---|---|
| Agent不可见(不知道有多少) | 100%的Claude Code/Codex用户 | `ama scan` |
| API花费不可控 | AI Agent市场$78.4亿 | `ama spend` + TokenCostTracker |
| 模型路由混乱 | 30-50%浪费率 | `ama route` |
| 安全合规真空 | 70-80%企业项目未通过POC | `ama audit` + RuleGuard |
| 一人公司需要操作系统 | 2026 OPC元年 | Agent Business $499-799/mo |
| AI客服按量计费太贵 | 企业月费$55-175/agent+AI费 | $799/月全包 |
| 无"AI内容部门"品类 | 市场空白 | 你是品类定义者 |

---

## 四、衍生品/扩展机会

1. **RuleGuard Pro 独立产品** — $49/次合规审查, 卖给MCN/电商
2. **AMA CLI (npm/pip包)** — 让开发者用命令管理agent, 开源引流
3. **Agent Audit as a Service** — 企业安全审计, $999/次
4. **OPC Playbook** — 一人公司操作手册, 电子书/课程, $29
5. **Agent Marketplace** — 457个agent的付费市场, 抽佣30%

---

## 五、今日避坑指南（10条精华）

1. 新号在HN/Reddit/PH全部受限 — 先养号再推广
2. AI自动化不如手动快 — 2分钟的手动操作, AI搞了2小时
3. 定价锚点决定一切 — ¥200 vs $499, 14倍差距
4. SaaS激活需>2次点击就不适合非技术用户 — n8n教训
5. 名字太常见会被淹没 — 'AMA'在PH上被同名产品占据
6. Dev.to文章Google可搜 — 比5个社交平台广告都有效
7. API key不能硬编码 — 写入文件会触发auto mode封锁
8. 产品定位比产品功能重要 — "代写工具"vs"一人公司OS"
9. 本地脚本比SaaS可靠 — 50行Node.js替代了n8n
10. AI基础设施几乎免费 — $0.50/月, 贵的是被浪费的时间
