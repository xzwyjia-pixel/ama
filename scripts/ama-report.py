#!/usr/bin/env python3
"""
AMA Report Generator — Converts inventory JSON to human-readable markdown report.
Also generates the landing-page-ready Agent Asset Overview.
"""
import json, os, sys, io
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load inventory
inventory_path = os.path.join(DATA_DIR, "agent-inventory-latest.json")
if not os.path.exists(inventory_path):
    print("ERROR: No inventory found. Run ama-scan.py first.")
    sys.exit(1)

inv = json.load(open(inventory_path, 'r', encoding='utf-8'))
stats = inv["stats"]
assets = inv["scan_results"]
issues = inv["issues"]
frameworks = inv["frameworks"]

# Generate report
report = []
def w(line=""):
    report.append(line)

w("# Agent Inventory Report")
w(f"> Generated: {inv['meta']['timestamp'][:19]}")
w(f"> Platform: {inv['meta']['platform']} | Scanner: {inv['meta']['scanner']}")
w(f"> **Total Assets: {stats['total_assets']}**")
w("")

# ---- Executive Summary ----
w("## Executive Summary")
w("")
w(f"Across **{len(frameworks)} agent frameworks**, this machine hosts **{stats['total_assets']} AI agent assets** — with no centralized management.")
w("")
w("| Framework | Status | Key Counts |")
w("|-----------|--------|-----------|")
for fname, finfo in frameworks.items():
    status = finfo.get("status", finfo.get("health", "unknown"))
    if fname == "pi":
        counts = f"{finfo.get('subagents',0)} sub-agents, {finfo.get('personas',0)} personas, {finfo.get('scripts',0)} scripts"
    elif fname == "claude":
        counts = f"{finfo.get('active_skills',0)} active skills, {finfo.get('archived_skills',0)} archived, {finfo.get('hooks',0)} hooks"
    elif fname == "codex":
        counts = f"{finfo.get('skills',0)} skills"
    elif fname == "external":
        counts = f"{finfo.get('agents',0)} agents"
    else:
        counts = "-"
    w(f"| **{fname}** | {status} | {counts} |")
w("")

# ---- Risk Alerts ----
if issues:
    w("## Risk Alerts")
    w("")
    for i in issues:
        sev = i["severity"].upper()
        w(f"### {sev}: {i['category']}")
        w(f"**{i['message']}**")
        w(f"→ {i['recommendation']}")
        w("")

# ---- Asset Breakdown ----
w("## Asset Breakdown")
w("")

w("### Sub-Agents (8)")
w("")
w("| Name | Model | Description |")
w("|------|-------|-------------|")
for a in assets["subagents"]:
    w(f"| {a['name']} | {a.get('model','?')} | {a.get('description','')[:80]} |")
w("")

w("### Active Skills (192) — Top 30 by name")
w("")
w("| # | Skill | Has SKILL.md |")
w("|---|-------|-------------|")
for i, s in enumerate(assets["skills_active"][:30]):
    has_md = "Yes" if s.get("has_skill_md") else "No"
    w(f"| {i+1} | {s['name']} | {has_md} |")
if len(assets["skills_active"]) > 30:
    w(f"| ... | +{len(assets['skills_active'])-30} more | |")
w("")

w("### Archived Skills (191) — Sample")
w("")
w("| # | Skill |")
w("|---|-------|")
for i, s in enumerate(assets["skills_archived"][:20]):
    w(f"| {i+1} | {s['name']} |")
w(f"| ... | +{len(assets['skills_archived'])-20} more |")
w("")

w("### Codex Skills (37)")
w("")
w("| # | Skill |")
w("|---|-------|")
for i, s in enumerate(assets["codex_skills"][:15]):
    w(f"| {i+1} | {s['name']} |")
if len(assets["codex_skills"]) > 15:
    w(f"| ... | +{len(assets['codex_skills'])-15} more |")
w("")

w("### MCP Servers (8)")
w("")
w("| Name | Command |")
w("|------|---------|")
for s in assets["mcp_servers"]:
    w(f"| {s['name']} | {s.get('command','?')} |")
w("")

w("### Hooks (3)")
w("")
w("| Name | Event |")
w("|------|-------|")
for h in assets["hooks"]:
    w(f"| {h['name']} | {h.get('hook_event','?')} |")
w("")

w("### External Agents (4)")
w("")
w("| Name | Type | Key Files |")
w("|------|------|-----------|")
for e in assets["external_agents"]:
    w(f"| {e['name']} | {e.get('type','?')} | {', '.join(e.get('key_files_found',[]))} |")
w("")

w("### Scripts (12)")
w("")
w("| # | Script |")
w("|---|--------|")
for i, s in enumerate(assets["scripts"]):
    w(f"| {i+1} | {s['name']} |")
w("")

# ---- Recommendations ----
w("## Recommendations")
w("")
w("1. **Archive cleanup**: 191 archived skills — consider permanent deletion for skills archived >180 days")
w("2. **Skill rationalization**: 192 active skills with significant overlap — deduplicate by capability")
w("3. **MCP health**: Verify all 8 MCP servers are reachable and responding")
w("4. **Persona fix**: Personas JSON structure needs review (showing 2 entries but not individual personas)")
w("5. **Centralized management**: No single dashboard to manage all 457 assets — deploy AMA")
w("")

# ---- Monetization Angle ----
w("## Commercial Value (Embedded)")
w("")
w("This inventory represents the **supply side** of an Agent Marketplace:")
w("")
w(f"- **{len(assets['skills_active'])} active skills** ready for curation and packaging")
w(f"- **{len(assets['skills_archived'])} archived skills** that could be revived/repurposed")
w(f"- **{len(assets['subagents'])} sub-agents** with defined tool boundaries — production-ready")
w(f"- **{len(assets['mcp_servers'])} MCP tools** for integration with external services")
w("")
w("At an average marketplace price of $9.90/month per skill:")
w(f"  → Revenue potential: ${len(assets['skills_active']) * 9.9:.0f}/month (at 100% utilization)")
w(f"  → Conservative estimate (10%): ${len(assets['skills_active']) * 9.9 * 0.1:.0f}/month")
w("")

# Write output
report_text = "\n".join(report)
report_path = os.path.join(OUTPUT_DIR, f"agent-inventory-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md")
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(report_text)

latest_report = os.path.join(DATA_DIR, "agent-inventory-report-latest.md")
with open(latest_report, 'w', encoding='utf-8') as f:
    f.write(report_text)

print(f"Report generated: {report_path}")
print(f"Latest copy:     {latest_report}")
print(f"Lines: {len(report)}")
