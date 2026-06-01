# AMA Launch Checklist — 双市场同步上线

> 按顺序执行。每完成一项打勾。

---

## Phase 0: 收款 (先做, 5 分钟)

- [ ] 打开 https://stripe.com → 注册账号
- [ ] 创建 Payment Link: "AMA Pro Report" — $49 (一次性)
- [ ] 创建 Payment Link: "AMA Pro Monthly" — $9.90/月
- [ ] 创建 Payment Link: "AMA Team" — $49/月
- [ ] 创建 Payment Link: "AMA Enterprise" — $999/月
- [ ] 把 4 个链接粘贴到 `public/store.html` 的 `STRIPE_LINKS` 对象
- [ ] 把 Pro Report 链接粘贴到 `public/index.html` (搜索 `YOUR_PRO_REPORT_LINK`)
- [ ] 运行部署: `vercel deploy public/ --prod`

---

## Phase 1: GitHub 开源 (10 分钟)

- [ ] 打开 https://github.com/new → 创建 repo: `ama-agent/ama`
- [ ] Push `github/README.md` 作为主 README
- [ ] 添加 topics: `ai-agents`, `agent-management`, `claude-code`, `devtools`, `ai-governance`
- [ ] 设置 About: "The OS for your AI agents. Scan, manage, optimize — across Claude Code, Pi, and Codex."
- [ ] 添加 Website 链接: https://ama-agent-store.vercel.app

---

## Phase 2: 社交发布 (15 分钟)

### 国内
- [ ] **V2EX** → 复制 `marketing/social-posts.md` 里的 V2EX 帖子 → 发布
- [ ] **即刻** → 复制即刻短文案 → 发布
- [ ] **掘金** → 复制 V2EX 帖子 (改标题) → 发布
- [ ] **小红书** → 截图 Calculator → 配文案 → 发布

### 国际
- [ ] **Hacker News** → 复制 `marketing/product-hunt-launch.md` 里的 Show HN → 发布
- [ ] **Twitter/X** → 复制推文线程 (5 条) → 发布
- [ ] **Reddit r/programming** → 复制 Reddit 帖子 → 发布
- [ ] **Reddit r/selfhosted** → 复制 selfhosted 版本 → 发布
- [ ] **Dev.to** → 复制 HN 帖子 → 发布为文章

---

## Phase 3: Product Hunt (本周二/三/四)

- [ ] 准备 5 张产品截图:
  - [ ] Calculator 结果页 (红色浪费数字)
  - [ ] Terminal `ama scan` 输出
  - [ ] Agent Store 页面
  - [ ] Admin Dashboard
  - [ ] 架构图
- [ ] 创建 Product Hunt 即将发布页面 (提前 2 天)
- [ ] 找 3-5 个朋友, 约定发布第一小时点赞
- [ ] 发布日: 复制 `marketing/product-hunt-launch.md` 内容 → PH
- [ ] 第一时间在 PH 发 First Comment

---

## Phase 4: 监控与转化 (持续)

- [ ] 打开 https://ama-agent-store.vercel.app/admin — 盯 Lead 面板
- [ ] 每次看到 Hot Lead → 点 Approve → 发送邮件模板
- [ ] 每 24 小时检查一次:
  - Calculator 访问量 (Vercel Analytics)
  - Lead 提交数 (Admin 面板)
  - 付费数 (Stripe Dashboard)
- [ ] 第一笔付费入账后 → 截图 → 发社交媒体庆祝贴

---

## 第一周目标

| 指标 | 目标 |
|------|------|
| Calculator 访问 | 500+ |
| Lead 捕获 | 15+ |
| Pro Report 购买 | 3+ |
| GitHub Stars | 50+ |
| Product Hunt 排名 | Top 5 |
| **第一笔收入** | **$49+** |

---

## 快速命令参考

```bash
# 部署更新
cd c:\Users\25454\业务中控台
vercel deploy public/ --prod

# 重新扫描 agent
python scripts/ama-scan.py

# 启动本地服务
python scripts/ama-server-prod.py --daemon

# 查看服务状态
python scripts/ama-server-prod.py --status

# 生成 Pro 报告
python scripts/ama-report-pro.py <email>

# 查看线上版本
vercel ls --scope xzwyjia
```
