# AMA 变现执行计划 — 从 0 到第一块钱

> **当前状态**: Calculator 上线, Store 上线, Admin 就绪, 457 agents 索引完成
> **核心瓶颈**: 有产品, 没流量, 没收款

---

## 现状诊断

```
已有:
  ✅ 获客工具 (Calculator + Lead Capture)
  ✅ 产品展示 (Agent Store — 457 agents)
  ✅ 审批面板 (Admin Dashboard)
  ✅ 后端管理 (AMA Local Server)

缺失:
  ❌ 流量来源 (没人知道 Calculator 存在)
  ❌ 收款能力 (没有支付/计费)
  ❌ 交付物 (点了购买后拿到什么?)
  ❌ 自动化 (Approve 后要手动发邮件)
  ❌ 信任基础 (没有案例/证明/背书)
```

---

## 三条变现路径 (按速度排序)

### 路径 A: 付费诊断报告 (3 天上线, 最速)

**模式**: Calculator 免费 → 详细诊断报告 $49

**操作**:
1. Calculator 页面已有免费版 (6 个滑块)
2. 用户提交邮箱后 → 显示 "Upgrade to Full Report $49"
3. Stripe Payment Link 收款
4. 自动生成 PDF 报告 (包含实际 agent 扫描结果)
5. 自动发送到邮箱

**定价**:
- 免费版: 基础估算 (已有)
- Pro 版: $49/次 — 包含真实扫描、浪费明细、优化方案
- 企业版: $499/次 — 包含人工复核 + 实施路线图

**收入预估**: 
- 假设转化率 3%, 100 个 Calculator 访问者 → 3 个付费
- 月收入: 3 × $49 = $147 (初始)
- 规模化: 1000 访问者 × 3% × $49 = $1,470/月

**需要做**:
- [ ] Stripe 账号 (10 分钟)
- [ ] 创建 Payment Link (5 分钟)
- [ ] 报告生成脚本 (已有数据, 2 小时)
- [ ] Calculator 升级 CTA (30 分钟)

---

### 路径 B: Agent 商店付费 (1 周上线, 可持续)

**模式**: 免费浏览 → 付费安装 $9.90/mo/agent

**操作**:
1. Store 已有 457 agents 可浏览
2. 精选 10 个高价值 agent 作为 "Premium"
3. Stripe 订阅集成
4. 付费后自动发送安装脚本
5. 按月续费

**定价**:
- Free tier: 浏览 + 3 个免费 agent
- Pro: $9.90/mo — 10 个 Premium agent
- Team: $49/mo — 50 agents + Admin Dashboard
- Enterprise: $999/mo — 无限 + 私有部署

**收入预估**:
- 假设 50 个付费用户, 平均 $20/mo
- 月收入: 50 × $20 = $1,000/月

**需要做**:
- [ ] Stripe 订阅集成
- [ ] Agent 精选 + 定价策略
- [ ] 安装脚本自动化
- [ ] 用户账号系统 (或直接用 Stripe Customer Portal)

---

### 路径 C: 企业实施服务 (随时可做, 高客单价)

**模式**: Calculator 获客 → 免费咨询 → 企业实施合同

**销售流程**:
1. Calculator 捕获 CTO/VP 级别线索
2. 你在 Admin 看到 Hot Lead → 主动联系
3. 30 分钟免费诊断咨询 (Zoom)
4. 提案: AMA 部署 + Agent 治理 + 培训
5. 签合同, 收款, 交付

**定价**:
- 快速部署: $2,500 (1 天 — 扫描 + 安装 + 基础培训)
- 全面治理: $15,000 (1 周 — 全部 agent 审核 + 安全规则 + Dashboard)
- 持续运维: $3,000/月 (远程管理 + 月度报告 + 更新)

**收入预估**:
- 每个月签 1 个全面治理 + 2 个快速部署
- 月收入: $15,000 + 2 × $2,500 = $20,000

**需要做**:
- [ ] 准备销售演示 (已有 Calculator + Store, 直接可用)
- [ ] 准备案例模板
- [ ] 定价单页
- [ ] 合同模板

---

## 立即执行 (本周)

### 第一步: 开 Stripe 收款 (今天, 30 分钟)

```
1. 注册 stripe.com (免费)
2. 创建一个 Payment Link:
   - "AMA Pro Report" — $49
   - "AMA Enterprise Scan" — $499
3. 把链接放到 Calculator 的 Success 页面
```

### 第二步: 流量 (明天开始)

**免费流量源 (按优先级)**:

| 渠道 | 动作 | 预期流量 | 难度 |
|------|------|---------|------|
| **Twitter/X** | 发帖: "I indexed 457 AI agents on my machine. Here's how much money I'm wasting." + Calculator 链接 | 500-5000 views | 低 |
| **Hacker News** | Show HN: "AMA — I built an OS for AI agents after finding 457 unmanaged agents on my PC" | 1000-10000 views | 中 |
| **Reddit** | r/programming, r/MachineLearning, r/selfhosted 发帖 | 500-3000 views | 中 |
| **GitHub** | 开源 AMA Core, README 带 Calculator 链接 | 持续流量 | 中 |
| **V2EX/掘金** | 中文社区: "盘点电脑里的 457 个 AI Agent, 发现每月浪费 XX 元" | 500-5000 views | 低 |
| **即刻/小红书** | 截图 Calculator 结果, 配文引导 | 100-1000 views | 低 |

**第一周目标**: 100 个 Calculator 访问者 → 3 个付费报告 → $147

### 第三步: 构建信任 (本周)

- [ ] Calculator 页面加一个 "Real Data" 区块: "Scanned: 457 agents on a real developer machine"
- [ ] 截图你的真实扫描结果作为 social proof
- [ ] 写一篇博客: "I found 457 AI agents on my computer. Here's what I learned."

---

## 收入里程碑

| 时间 | 里程碑 | 月收入 | 关键动作 |
|------|--------|--------|---------|
| **Week 1** | 第一笔付费报告 | $49-147 | Stripe + 社交推广 |
| **Week 2** | 第一个企业咨询 | $2,500 | Hot Lead 跟进 |
| **Month 1** | 稳定流量 + 付费 | $500-1,000 | 内容持续输出 |
| **Month 3** | Store 付费订阅上线 | $2,000-5,000 | Stripe 订阅 + 精选 Agent |
| **Month 6** | AMA Cloud 企业版 | $5,000-15,000 | 多租户 SaaS + 企业销售 |
| **Month 12** | 目标 | $20,000-50,000/月 | 规模化 + 渠道合作 |

---

## 关键决策

现在需要你做一个选择:

**A. 快速变现 ($49 报告)** — 3 天上线, 但天花板低 (月入 $500-2000)
**B. 企业服务 ($2,500-15,000)** — 随时可做, 但需要主动销售  
**C. SaaS 订阅 ($999/月)** — 天花板高但需要 1-2 个月开发
**D. 三条同时做** — 最大化收入, 但精力分散

**推荐: D (三条同时做) + 精力分配 40% 社交引流 / 30% 企业销售 / 30% 产品开发**

---

## 今天下午就能做的 3 件事

1. **注册 Stripe** → 创建 $49 Payment Link → 放到 Calculator
2. **发一条推文** → 截图你的 Calculator 结果 → 附链接
3. **找一个潜在客户** → 谁在抱怨 AI 太贵? → 私信对方 Calculator 链接
