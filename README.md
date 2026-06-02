# AMA — Agent Management Agent

**I scanned my PC and found 457 AI agents. You probably have more than you think.**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**Try the live calculator → [ama-agent-store.vercel.app](https://ama-agent-store.vercel.app)**

AMA discovers, routes, and secures every AI agent across **Claude Code, Pi Agent, Codex CLI, and any MCP server** — from a single terminal.

```bash
pip install ama-core && ama scan && ama start
```

---

## The Problem

Your developers are using 50-200+ AI coding agents. You have **zero visibility**
into which ones, what they cost, or where your code is being sent.

```
Typical Developer Machine (real scan results):
├── Claude Code:   192 active skills, 191 archived (still indexed)
├── Codex CLI:      37 skills
├── Pi Agent:        8 sub-agents, 12 scripts, 6 personas
├── MCP Servers:     8 connected services
└── External:        4 standalone agents
                    ───
                    457 AI agent assets. Zero management.
```

### The Waste

| Waste Category | % of Spend | Cause |
|----------------|-----------|-------|
| Duplicate Calls | 8-18% | Same prompt → 3+ agents |
| Overqualified Models | 15-25% | Simple tasks on GPT-4/Opus |
| Cache Misses | 12-20% | No shared prompt cache |
| Zombie Agents | 2-8% | Archived agents still consuming resources |
| **Total Waste** | **30-50%** | |

---

## What AMA Does

### Discover
```bash
$ ama scan
🔍 Scanning agent ecosystem...
   ✓ 8 Pi sub-agents
   ✓ 192 Claude Code skills (active)
   ✓ 191 Claude Code skills (archived)
   ✓ 37 Codex skills
   ✓ 8 MCP servers
   ✓ 3 Hooks, 2 Personas, 4 External agents
   ─────────────────────────────
   Total: 457 assets indexed
```

### Route (Smart Dispatch)
Simple questions → cheap models. Complex tasks → powerful models.
Cuts API costs 30-50% automatically.

### Manage (Lifecycle)
```bash
ama install <agent>   # Register
ama enable  <agent>   # Activate
ama disable <agent>   # Pause
ama archive <agent>   # Archive (auto-candidate after 90 days unused)
```

### Audit (Security)
Permission boundaries, API key hygiene, audit logging.
Your CISO will thank you.

### Track (Cost)
Per-agent, per-team, per-project spend tracking.
Finally know where your AI budget goes.

---

## Architecture

```
AMA (Meta-Agent) — 7 Layers
│
├── L0 Scanner       — Agent discovery & inventory (SQLite registry)
├── L1 Health         — Heartbeat, circuit breaker, performance monitoring
├── L2 Router         — Intent → Agent matching with weighted scoring
├── L3 Lifecycle      — Install, enable, disable, archive state machine
├── L4 Config         — Unified config across Pi, Claude, Codex frameworks
├── L5 Orchestrator   — Parallel/serial/DAG multi-agent workflows
├── L6 Security       — Permission boundaries, audit logging, compliance
└── L7 Observability  — Metrics dashboard, cost tracking, post-mortems
```

---

## Quick Start

### Prerequisites
- Python 3.10+
- At least one AI agent framework installed (Claude Code, Codex, or Pi Agent)

### Install
```bash
pip install ama-core
```

### Scan
```bash
ama scan
# Output: agent inventory JSON + Markdown report
```

### Launch Dashboard
```bash
ama start
# Opens http://localhost:8765/store
```

### Cost Calculator
```bash
ama calculator
# Or visit: https://ama-agent-store.vercel.app/calculator
```

---

## Supported Frameworks

| Framework | Discovery | Routing | Lifecycle | Security |
|-----------|-----------|---------|-----------|----------|
| **Claude Code** | ✅ | ✅ | ✅ | ✅ |
| **Pi Agent** | ✅ | ✅ | ✅ | ✅ |
| **Codex CLI** | ✅ | ✅ | ✅ | ✅ |
| **MCP Servers** | ✅ | ✅ | — | ✅ |
| **Any MCP Tool** | ✅ | — | — | — |

---

## Pricing

| Plan | Price | What You Get |
|------|-------|-------------|
| **Open Source** | Free | Scanner, local dashboard, basic routing |
| **Pro** | $9.90/mo | Premium agents, priority support, auto-updates |
| **Team** | $49/mo | 50 agents, admin dashboard, team cost tracking |
| **Enterprise** | $999/mo | Unlimited, SSO, SLA, dedicated support |

[View Plans →](https://ama-agent-store.vercel.app/store)

---

## Try the Calculator

Estimate your AI waste in 10 seconds:
**[ama-agent-store.vercel.app/calculator](https://ama-agent-store.vercel.app/calculator)**

---

## Real Scan Results

We ran AMA on a single developer machine. Here's what we found:

```
Total Assets:    457
Active Skills:   192
Archived Skills: 191 (still indexed — zombie agents)
Codex Skills:     37
Sub-agents:        8
MCP Servers:       8
Hooks:             3
Personas:          2
External Agents:   4
Scripts:          12
```

[Full Inventory Report →](https://ama-agent-store.vercel.app/store)

---

## Why Open Source

The AI agent ecosystem is fragmenting across multiple frameworks.
No single vendor will solve this — it needs to be community-driven,
multi-framework, and local-first.

AMA Core is MIT licensed. The Pro/Team/Enterprise tiers add
managed hosting, SSO, and priority support.

---

## Contributing

```bash
git clone https://github.com/ama-agent/ama.git
cd ama
pip install -e ".[dev]"
ama scan
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Links

- 🏪 [Agent Store](https://ama-agent-store.vercel.app/store)
- 📊 [Cost Calculator](https://ama-agent-store.vercel.app/calculator)
- 🏢 [Enterprise](https://ama-agent-store.vercel.app/enterprise)
- 📧 [Contact](mailto:ama@ama-agent.dev)

---

**AMA — Know what your agents are doing.**
