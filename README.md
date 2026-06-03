# AMA — Agent Management Agent

**457 agents found on one dev machine. Most unmanaged. Zero visibility. 30-50% of API spend wasted.**

*This tool was built by someone who doesn't know how to code — using AI to write every line. [Full story →](https://ama-agent-store.vercel.app/real-story.html)*

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/xzwyjia-pixel/ama/pulls)

**Try it live → [ama-agent-store.vercel.app](https://ama-agent-store.vercel.app)**

---

## Demo

https://github.com/user-attachments/assets/ama-demo.mp4

*18 seconds: terminal scan → 457 agents → dashboard*

```bash
pip install ama-core && ama scan && ama start
```

AMA discovers, routes, and secures every AI agent across **Claude Code, Pi Agent, Codex CLI, and any MCP server** — from a single terminal. Built by someone who can't code, powered by AI.

---

## The Problem

Your machine is crawling with AI agents. **You have no idea how many, what they cost, or where they're sending your code.**

```
Real scan of a single developer machine:
├── Claude Code:   192 active skills · 191 archived (still indexed!)
├── Codex CLI:      37 skills
├── Pi Agent:        8 sub-agents · 12 scripts · 6 personas
├── MCP Servers:     8 connected services
└── External:        4 standalone agents
                    ───
                    457 AI agent assets. Zero management.
```

| Waste Category | % of Spend | Root Cause |
|---|---|---|
| Duplicate Calls | 8-18% | Same prompt → 3+ agents |
| Overqualified Models | 15-25% | Simple tasks on premium models |
| Cache Misses | 12-20% | No shared prompt cache |
| Zombie Agents | 2-8% | Archived agents still active |
| **Total Waste** | **30-50%** | |

---

## What AMA Does

### Discover
```bash
$ ama scan
Scanning agent ecosystem...
   ✓ 8 Pi sub-agents
   ✓ 192 Claude Code skills (active)
   ✓ 191 Claude Code skills (archived)
   ✓ 37 Codex skills
   ✓ 8 MCP servers
   ✓ 3 Hooks · 2 Personas · 4 External agents
   ─────────────────────────────
   Total: 457 assets indexed
```

### Route
Smart dispatch: simple questions → cheap models, complex tasks → powerful models. Cuts API costs 30-50% automatically.

### Manage
```bash
ama install <agent>   # Register
ama enable  <agent>   # Activate
ama disable <agent>   # Pause
ama archive <agent>   # Archive (auto after 90 days unused)
```

### Audit
Permission boundaries. API key hygiene. Audit logging. Your CISO will thank you.

### Track
Per-agent, per-team, per-project cost tracking. Finally know where your budget goes.

---

## Architecture

```
AMA (Meta-Agent) — 7 Layers
│
├── L0 Scanner       — Agent discovery & inventory (SQLite)
├── L1 Health        — Heartbeat, circuit breaker, monitoring
├── L2 Router        — Intent → Agent matching, weighted scoring
├── L3 Lifecycle     — Install, enable, disable, archive
├── L4 Config        — Unified config across Pi, Claude, Codex
├── L5 Orchestrator  — Parallel / serial / DAG multi-agent workflows
├── L6 Security      — Permission boundaries, audit, compliance
└── L7 Observability — Metrics, cost tracking, post-mortems
```

Also includes **RuleGuard Pro** — a 3-agent debate protocol for content compliance auditing at $0.002/audit.

---

## Quick Start

```bash
# Install
pip install ama-core

# Scan your machine
ama scan

# Launch dashboard
ama start
# → http://localhost:8765/store

# Estimate your waste
ama calculator
# → https://ama-agent-store.vercel.app/calculator
```

---

## Supported Frameworks

| Framework | Discovery | Routing | Lifecycle | Security |
|---|---|---|---|---|
| **Claude Code** | ✅ | ✅ | ✅ | ✅ |
| **Pi Agent** | ✅ | ✅ | ✅ | ✅ |
| **Codex CLI** | ✅ | ✅ | ✅ | ✅ |
| **MCP Servers** | ✅ | ✅ | — | ✅ |
| **Any MCP Tool** | ✅ | — | — | — |

---

## Pricing

| Plan | Price | Includes |
|---|---|---|
| **Open Source** | Free | Scanner, local dashboard, basic routing |
| **Pro** | $9.90/mo | Premium agents, priority support, auto-updates |
| **Team** | $49/mo | 50 agents, admin dashboard, team cost tracking |
| **Enterprise** | $999/mo | Unlimited, SSO, SLA, dedicated support |

[View all plans →](https://ama-agent-store.vercel.app/store)

---

## Real Numbers

We ran AMA on a single machine. Here's what we found:

```
Total Assets:    457
Active Skills:   192          Claude Code
Archived:        191          ← still indexed, still consuming
Codex Skills:     37
Sub-agents:        8          Pi Agent
MCP Servers:       8
Hooks:             3
Personas:          2
External Agents:   4
Scripts:          12
```

[Browse the full inventory →](https://ama-agent-store.vercel.app/store)

---

## The 48-Hour Build Story

This entire project — scanner, dashboard, marketplace, debate protocol, CI/CD — was built in 48 hours by a **non-coder using AI**. Zero lines written manually. $0.50/month total infrastructure cost.

**Read the full story:** [I don't know how to code — but I built a SaaS business in 48 hours with AI](https://ama-agent-store.vercel.app/real-story.html)

---

## Why Open Source

Agent sprawl affects everyone using Claude Code, Codex, or Pi Agent. No single vendor will solve this — it requires community-driven, multi-framework, local-first infrastructure. AMA Core is MIT. Pro tiers add managed hosting and enterprise features.

---

## Contributing

```bash
git clone https://github.com/xzwyjia-pixel/ama.git
cd ama
pip install -e ".[dev]"
ama scan
```

Issues and PRs welcome. Especially if you've scanned your own machine — we want to know what numbers you get.

---

## Links

- 🏪 [Agent Store](https://ama-agent-store.vercel.app/store) — Browse 457 agents
- 📊 [Cost Calculator](https://ama-agent-store.vercel.app) — Estimate your waste
- 🎬 [Demo Video](https://ama-pi-gray.vercel.app/ama-demo.webm) — 18-second walkthrough
- 📖 [Build Story](https://ama-agent-store.vercel.app/real-story.html) — How a non-coder built this
- 🏢 [Enterprise](https://ama-agent-store.vercel.app/enterprise)
- 📧 [Contact](mailto:ama@ama-agent.dev)

---

**AMA — Know what your agents are doing.**
