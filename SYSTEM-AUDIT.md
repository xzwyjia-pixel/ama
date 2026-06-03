# System Audit — 2026-06-03

## 一、产品与部署清单

### 已上线产品 (6个)
| # | 产品 | URL | 状态 | 真实流量 |
|---|---|---|---|---|
| 1 | AMA 落地页 | ama-agent-store.vercel.app | 🟢 在线 | 0 外部链接 |
| 2 | AMA Agent Store | /store | 🟢 在线, 457 agents 可浏览 | 0 |
| 3 | AMA Thesis 信息图 | /ama-thesis.html | 🟢 在线 | 0 |
| 4 | Agent Business | agent-business-xi.vercel.app | 🟢 在线, USD 定价 | 0 |
| 5 | GitHub | github.com/xzwyjia-pixel/ama | 🟢 公开, MIT | 未知 star |
| 6 | Dev.to 文章 | 2 篇英文 | 🟢 Google 索引 | 未知阅读量 |

### 本地运行系统
| 组件 | 状态 | 详情 |
|---|---|---|
| Daemon | 🟢 PID 9972 | localhost:3456, 每日 8:30 自动生成 |
| 内容队列 | 17 条 | content-queue/ |
| 订单 | 1 条测试 | orders/ORD-1780392401810.json |
| n8n Cloud | 🔴 废弃 | 5 个工作流待激活, 已被 daemon 替代 |
| Vercel 部署 | 10 次覆盖 | 多次增量修复 |

---

## 二、失误与窝工分析

### Top 10 浪费时间排名

| # | 失误 | 耗时估计 | 根因 | 教训 |
|---|---|---|---|---|
| 1 | **n8n Cloud 激活** | ~3h | 反复尝试 Playwright 自动化, 开关始终找不到，免费版可能不提供激活功能 | 先用最简单方案（本地 daemon），SaaS 不是必需品 |
| 2 | **Reddit 发帖被删** | ~1.5h | r/selfhosted 被删，r/aiagents 被拒，新号无法推广产品 | 先了解社区规则再发帖，Reddit 对自我推广零容忍 |
| 3 | **HN Show HN 被限** | ~2h | karma 不足，Google 登录被拦，之后普通链接帖被 rate-limit | 提前了解新号限制，Plan B: 发普通链接而非 Show HN |
| 4 | **n8n HTTP Request 节点凭证冲突** | ~1h | 反复调试认证方式，最终改用 Code 节点 | API key 不应硬编码在 workflow JSON 中 |
| 5 | **Product Hunt 未索引** | ~30min | 排期可能未成功触发，或被同名产品 hamr0/ama 淹没 | 需要确认排期确实生效，选择更独特的名字 |
| 6 | **Playwright 反复被 auto mode 拦截** | ~1h | 外部网站提交被识别为安全问题 | 提前配置 Bash permissions |
| 7 | **Windows GBK 编码问题** | ~30min | 终端中文输出乱码，Python/Node Unicode 错误 | 用英文输出，或设置 UTF-8 locale |
| 8 | **Bash ↔ Windows 路径混乱** | ~30min | `/tmp` vs `C:\tmp`, bash 路径被 node 解析为 `C:\c\...` | 统一用绝对路径，或使用 `cygpath` 转换 |
| 9 | **API key 硬编码泄露** | ~20min | 写入多个 n8n JSON 和 CREDENTIALS.md，触发 auto mode 封锁 | 只用环境变量，不写文件 |
| 10 | **Daemon 重复启动冲突** | ~15min | EADDRINUSE，旧进程没被杀干净 | 启动前检查端口占用 |

### 策略失误
| # | 问题 | 影响 |
|---|---|---|
| 1 | **定价太低** | 最初 ¥200/篇，错过了美国市场的定价锚点 |
| 2 | **平台分散** | 同时打 HN/Reddit/PH/Dev.to/Twitter，精力碎片化 |
| 3 | **过度自动化** | 花了大量时间为"全自动"写 Playwright 脚本，但实际上用户操作比脚本快得多 |
| 4 | **产品定位摇摆** | 从"代写工具"到"一人公司 OS"用了 2 天才想清楚 |

---

## 三、真正有效的事情

| 做了什么 | 效果 |
|---|---|
| Dev.to 文章 | ✅ Google 搜索可找到 |
| 把落地页从中文切英文 | ✅ 客单价从 ¥200 → $499 (14x 提升) |
| Daemon 内置调度器 | ✅ 每天自动生成，替代 n8n |
| Code 节点替代 HTTP Request | ✅ 绕过 n8n 凭证问题 |
| 视频 → transcript → debate → Obsidian 全链路 | ✅ 技术验证通过，可产品化 |
| 定价从 per-piece 改为 subscription | ✅ 月费制，客户终身价值高 |

---

## 四、当前能力矩阵

### 能自动搞定的事
- 长文生成 (公众号, blog, Dev.to)
- 短视频脚本 (Douyin, TikTok)
- 数据分析报告
- 合规审查 (RuleGuard)
- 视频转录 + 商业洞察提取
- Obsidian 知识沉淀
- 每日定时调度
- 落地页接单

### 需要人工的环节
- 收款确认
- 公众号/平台发布
- HN/Reddit 等社区互动
- 客户沟通

---

## 五、改进建议

### 立即执行
1. **关掉 n8n Cloud 账户** — 浪费钱和注意力
2. **清理 Vercel 多余部署** — 10 个旧部署可删
3. **修复 CREDENTIALS.md** — 从 git 历史中删除含 key 的版本
4. **统一产品命名** — AMA (Agent Management) vs Agent Business → 建议只用 AMA

### 本周
5. **写第 3 篇 Dev.to** — "How I built AMA: Lessons from scanning 457 agents"
6. **加 Google Analytics** — 两个网站都需要流量追踪
7. **录 2 分钟 demo 视频** — 贴 GitHub README

### 下月
8. **Stripe 接入** — stripe-setup.md 已存在，配好就能收美元
9. **SEO 持续优化** — 已有 robots.txt/sitemap，需等 Google 索引
10. **社交媒体持续** — Twitter 每周 2-3 条，不追求爆款，稳定输出
