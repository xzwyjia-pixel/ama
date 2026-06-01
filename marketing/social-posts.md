# AMA Social Media Content Pack
> Copy, paste, post. Replace [URL] with https://ama-agent-store.vercel.app/calculator

---

## Twitter/X (280 chars)

### Post 1: The Hook (pin this)
```
I indexed every AI agent on my computer. Found 457 of them.

Zero centralized management. 30-50% of API spend is pure waste.

Built a free calculator to check yours:
[URL]
```

### Post 2: The Numbers
```
Breaking down AI agent waste on a typical dev machine:

• Duplicate calls: 8-18% waste
• Overqualified models: 15-25% waste
• Cache misses: 12-20% waste
• Zombie agents: 2-8% waste

Total: 30-50% of your AI bill is being thrown away.

Calc: [URL]
```

### Post 3: The Fix
```
After discovering 457 unmanaged AI agents on my machine, I built AMA.

- Scans all agents across Pi, Claude Code, Codex, MCP
- Smart routing (simple task → cheap model)
- Unified prompt caching
- Agent lifecycle management

Open source core. Free calculator: [URL]
```

### Post 4: Enterprise Angle
```
CTOs: Your devs are using 50+ AI agents. 

Do you know:
• Which ones?
• What they cost?
• Where your code is being sent?

AMA Enterprise scans your entire org. 
$2,500 one-time. Full audit + governance.
[URL]
```

---

## Reddit (r/programming, r/MachineLearning, r/selfhosted)

### Title: I indexed every AI agent on my PC — found 457 of them. Here's the breakdown.

```
After months of using Claude Code, Codex, and Pi Agent, I
realized I had no idea how many AI agents were actually running
on my machine. So I built a scanner.

Results:
- 192 active Claude Code skills
- 191 archived skills (still indexed)
- 37 Codex skills
- 8 MCP servers
- 9 sub-agents
- 12 utility scripts
Total: 457 AI agent assets. Zero centralized management.

The waste comes from:
1. Same prompt sent to 3 different agents
2. Simple questions hitting GPT-4 when Haiku would do
3. No shared prompt cache across agents
4. Archived agents still consuming scan resources

I built a free calculator to estimate your waste:
[URL]

And an open-source management tool (AMA) to fix it.
Would love feedback from anyone else dealing with agent sprawl.
```

### r/selfhosted version:
```
AMA: Self-hosted AI Agent Manager — like Portainer for your AI agents

- One-command scan discovers all agents
- Local SQLite registry (your data stays on your machine)
- Smart routing to cut API costs 30-50%
- Web dashboard at localhost:8765

Free, open source, zero cloud dependencies.
Calculator: [URL]
```

---

## V2EX (中文)

### 标题: 扫描了电脑里的 AI Agent, 发现 457 个，每月浪费几千块

```
最近发现我的电脑上有 Claude Code、Codex、Pi Agent 三套 AI 编码工具,
每一套都装了几十个 skills/agents, 总共 457 个。

问题是: 完全没人管。同一个任务经常发给 3 个 agent,
简单问题也跑在贵模型上, prompt cache 也各用各的。

粗略算了下, 30-50% 的 API 费用是浪费的。

做了个免费计算器, 可以估算你的浪费金额:
[URL]

开源管理工具 AMA (Agent Management Agent) 也做好了,
一键扫描 + 智能路由 + 成本追踪。
欢迎试用和反馈。
```

---

## 即刻/小红书 (短文案)

```
🔍 扫描了电脑里的 AI Agent，发现了 457 个...

其中:
• 192 个活跃中
• 191 个已归档但还在占资源
• 37 个来自 Codex
• 8 个 MCP 服务器

一个月浪费几千块 API 费用。

做了个免费计算器, 10 秒出结果 👉 [URL]
```

---

## GitHub README (for open-source repo)

```markdown
# AMA — Agent Management Agent

**The operating system for your AI agents.**

AMA scans, manages, and optimizes every AI agent on your machine —
across Claude Code, Pi Agent, Codex CLI, and any MCP server.

## One command
```bash
pip install ama-core && ama scan && ama start
```

## What it does
- **Discovers** every agent on your system (we found 457 on one machine)
- **Routes** tasks to the optimal model (cuts API costs 30-50%)
- **Manages** agent lifecycle (install, enable, disable, archive)
- **Audits** security (permission boundaries, API key hygiene)
- **Tracks** costs (per agent, per team, per project)

## Quick Start
```bash
ama scan       # Discover all agents
ama dashboard  # Open web UI at localhost:8765
ama optimize   # Get cost-saving recommendations
```

## Architecture
```
AMA (Meta-Agent)
├── Scanner (L0)    — Agent discovery & inventory
├── Router (L2)     — Smart task-to-agent dispatch
├── Lifecycle (L3)  — Install/enable/disable/archive
├── Config (L4)     — Unified multi-framework config
├── Orchestrator (L5)— Multi-agent workflow engine
├── Security (L6)   — Permission boundaries + audit
└── Observability (L7) — Metrics + cost tracking
```

## Try the Calculator
https://ama-agent-store.vercel.app/calculator
```
