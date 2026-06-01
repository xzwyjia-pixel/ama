#!/usr/bin/env python3
"""
AMA Pro Report Generator v1.0 — Generates detailed paid diagnostic reports.

Usage:
  python ama-report-pro.py <lead-email>  → generates full report for a lead
  python ama-report-pro.py --json <file>  → generates report from lead JSON
  python ama-report-pro.py --all           → generates reports for all approved leads

Output: Markdown + optional PDF-ready HTML report in output/reports/
"""
import json, os, sys, io, hashlib
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output", "reports")
INVENTORY_PATH = os.path.join(DATA_DIR, "agent-inventory-latest.json")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================================================================
# Report Templates
# ================================================================
def generate_report(lead_data):
    """Generate a comprehensive diagnostic report."""
    now = datetime.now().isoformat()[:19]
    report_id = hashlib.md5(f"{lead_data.get('email','')}{now}".encode()).hexdigest()[:8]

    # Load real inventory data
    inventory = {}
    if os.path.exists(INVENTORY_PATH):
        inventory = json.load(open(INVENTORY_PATH, 'r', encoding='utf-8'))

    lines = []
    w = lines.append

    # ---- COVER ----
    w(f"# AMA Pro Diagnostic Report")
    w(f"**Report ID**: RPT-{report_id}")
    w(f"**Generated**: {now}")
    w(f"**For**: {lead_data.get('email', 'Client')}")
    w(f"**Company**: {lead_data.get('company', 'Not specified')}")
    w(f"**Status**: PROFESSIONAL EDITION")
    w("")
    w("---")
    w("")

    # ---- EXECUTIVE SUMMARY ----
    w("## 1. Executive Summary")
    w("")
    team_size = lead_data.get('teamSize', 0)
    monthly_spend = lead_data.get('monthlySpend', 0)
    monthly_waste = lead_data.get('monthlyWaste', 0)
    yearly_savings = lead_data.get('yearlySavings', 0)
    waste_pct = lead_data.get('wastePct', '0%')

    w(f"Based on your team of **{team_size} developers**, we estimate your current monthly AI API spend at **${monthly_spend:,}**.")
    w("")
    w(f"Of this, approximately **${monthly_waste:,} ({waste_pct})** is wasted on:")
    w("")
    w("1. **Duplicate calls** — same prompts sent to multiple agents")
    w("2. **Overqualified models** — simple tasks running on expensive models")
    w("3. **Cache misses** — no unified prompt caching across agents")
    w("4. **Zombie agents** — unused agents still consuming resources")
    w("")
    w(f"**With AMA deployed, you could save approximately ${yearly_savings:,} per year.**")
    w("")
    w(f"This represents a **{round((yearly_savings/(monthly_spend*12))*100) if monthly_spend > 0 else '300+'}% ROI** on the AMA investment.")
    w("")

    # ---- WASTE BREAKDOWN ----
    w("## 2. Waste Breakdown")
    w("")
    w("| Waste Category | Monthly Cost | Yearly Cost | Root Cause |")
    w("|----------------|-------------|------------|------------|")
    w(f"| Duplicate Calls | ${lead_data.get('dupWaste', 0):,} | ${lead_data.get('dupWaste', 0)*12:,} | No agent registry — same task routed to 3+ agents |")
    w(f"| Overqualified Models | ${lead_data.get('overWaste', 0):,} | ${lead_data.get('overWaste', 0)*12:,} | Simple prompts hitting GPT-4/Opus instead of Haiku/DeepSeek |")
    w(f"| Cache Misses | ${lead_data.get('cacheWaste', 0):,} | ${lead_data.get('cacheWaste', 0)*12:,} | Fragmented prompt prefixes across {lead_data.get('agentCount', 50)} agents |")
    w(f"| Zombie Agents | ${lead_data.get('zombieWaste', 0):,} | ${lead_data.get('zombieWaste', 0)*12:,} | ~{int(lead_data.get('agentCount', 50) * 0.08)} agents unused but still indexed |")
    w("")

    # ---- REAL DATA SECTION ----
    if inventory:
        stats = inventory.get('stats', {})
        assets = inventory.get('scan_results', {})
        w("## 3. Real Agent Inventory Reference")
        w("")
        w(f"AMA has already indexed **{stats.get('total_assets', 457)} AI agents** on a reference machine:")
        w("")
        w("| Agent Type | Count | Example |")
        w("|-----------|-------|---------|")
        for cat in ['subagents', 'skills_active', 'skills_archived', 'codex_skills', 'mcp_servers']:
            items = assets.get(cat, [])
            if items:
                example = items[0].get('name', 'N/A') if items else 'N/A'
                w(f"| {cat.replace('_',' ').title()} | {len(items)} | {example} |")
        w("")
        w("This is a typical developer machine. Your actual inventory will be scanned on AMA deployment.")
        w("")

    # ---- RECOMMENDATION ----
    w("## 4. Recommended Action Plan")
    w("")
    w("### Phase 1: Immediate (Day 1)")
    w("```bash")
    w("# Deploy AMA in 30 seconds")
    w("pip install ama-core")
    w("ama scan    # Discover all agents on your machine")
    w("ama start   # Launch the management dashboard")
    w("```")
    w("")
    w("### Phase 2: Optimization (Week 1)")
    w("- Run full agent audit with AMA Scanner")
    w("- Identify and archive zombie agents")
    w("- Configure smart routing rules")
    w("- Enable unified prompt caching")
    w("")
    w("### Phase 3: Governance (Week 2-4)")
    w("- Set up agent permission boundaries")
    w("- Deploy damage-control safety rules")
    w("- Enable cost tracking per team/project")
    w("- Schedule monthly agent review cadence")
    w("")
    w("### Expected Results")
    w(f"- **Month 1**: Save ${round(yearly_savings/12):,}")
    w(f"- **Month 3**: Save ${round(yearly_savings/4):,} (cumulative)")
    w(f"- **Year 1**: Save ${yearly_savings:,}")
    w("")

    # ---- PRICING ----
    w("## 5. Investment & ROI")
    w("")
    w("| Plan | Price | Best For |")
    w("|------|-------|----------|")
    w("| AMA Open Source | Free | Individual developers, <20 agents |")
    w("| AMA Pro | $49/mo | Small teams, up to 100 agents |")
    w("| AMA Enterprise | $999/mo | 200+ dev teams, unlimited agents, SSO, SLA |")
    w("")
    w(f"**Your estimated ROI with AMA Pro ($49/mo): {(yearly_savings/12 - 49):,.0f}% monthly**")
    w(f"**Your estimated ROI with AMA Enterprise ($999/mo): {((yearly_savings/12 - 999)/(999))*100:.0f}% monthly**")
    w("")

    # ---- NEXT STEPS ----
    w("## 6. Next Steps")
    w("")
    w("1. **Schedule a demo**: Reply to this report to schedule a 15-minute live AMA demo")
    w("2. **Try it yourself**: `pip install ama-core && ama scan && ama start`")
    w("3. **Enterprise assessment**: We'll scan your full org (100+ machines) and produce a comprehensive savings report")
    w("")
    w("---")
    w(f"*Report generated by AMA Pro Diagnostic Engine v1.0 | {now}*")
    w(f"*Agent Management Agent — The OS for your AI agents*")

    return "\n".join(lines)

# ================================================================
# Main
# ================================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="AMA Pro Report Generator")
    parser.add_argument("email", nargs="?", help="Lead email to generate report for")
    parser.add_argument("--json", help="Path to lead JSON file")
    parser.add_argument("--all", action="store_true", help="Generate reports for all leads")
    args = parser.parse_args()

    if args.json:
        lead = json.load(open(args.json, 'r', encoding='utf-8'))
        report = generate_report(lead)
        out_path = os.path.join(OUTPUT_DIR, f"report-{lead.get('email','unknown').replace('@','-')}.md")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report: {out_path}")
        print(f"Lines: {len(report.split(chr(10)))}")
        return

    if args.all:
        # Try to load leads from various sources
        leads_file = os.path.join(DATA_DIR, "ama-leads.json")
        if os.path.exists(leads_file):
            leads = json.load(open(leads_file, 'r', encoding='utf-8'))
        else:
            leads = []
        if not leads:
            print("No leads found. Save leads to data/ama-leads.json")
            return
        for lead in leads:
            if lead.get('status') == 'approved':
                report = generate_report(lead)
                out_path = os.path.join(OUTPUT_DIR, f"report-{lead.get('email','unknown').replace('@','-')}.md")
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"Generated: {out_path}")
        return

    if args.email:
        # Generate a demo report
        lead = {
            'email': args.email,
            'company': 'Acme Corp',
            'teamSize': 50,
            'monthlySpend': 15000,
            'monthlyWaste': 6000,
            'wastePct': '40%',
            'yearlySavings': 54000,
            'dupWaste': 1800,
            'overWaste': 2400,
            'cacheWaste': 1200,
            'zombieWaste': 600,
            'agentCount': 50,
        }
        report = generate_report(lead)
        out_path = os.path.join(OUTPUT_DIR, f"report-{args.email.replace('@','-')}.md")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report: {out_path}")
        print("\n" + report[:500] + "...")
        return

    # Demo report
    lead = {
        'email': 'demo@example.com',
        'company': 'Demo Corp',
        'teamSize': 50,
        'monthlySpend': 15000,
        'monthlyWaste': 6000,
        'wastePct': '40%',
        'yearlySavings': 54000,
        'dupWaste': 1800, 'overWaste': 2400,
        'cacheWaste': 1200, 'zombieWaste': 600,
        'agentCount': 50,
    }
    report = generate_report(lead)
    out_path = os.path.join(OUTPUT_DIR, "report-demo.md")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"Demo report: {out_path}")
    print("\n" + report[:800] + "...")

if __name__ == "__main__":
    main()
