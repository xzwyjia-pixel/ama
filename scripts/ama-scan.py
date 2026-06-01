#!/usr/bin/env python3
"""
AMA Scanner v1.0 — Agent Inventory Discovery Engine
Scans all agent directories, generates structured inventory JSON.
"""
import json, os, glob, hashlib, sys, io
from datetime import datetime

# Fix Windows GBK encoding for emoji output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HOME = os.path.expanduser("~")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

TIMESTAMP = datetime.now().isoformat()
OUTPUT_FILE = os.path.join(OUTPUT_DIR, f"agent-inventory-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")

def file_hash(path, bytes_to_read=2048):
    """Quick content hash for change detection."""
    try:
        with open(path, 'rb') as f:
            return hashlib.md5(f.read(bytes_to_read)).hexdigest()[:12]
    except:
        return "ERROR"

def safe_read(path, max_bytes=2000):
    """Read file safely, return first N chars."""
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read(max_bytes)
    except:
        return ""

def list_dirs(path):
    """List subdirectories, return sorted names."""
    if not os.path.isdir(path):
        return []
    try:
        return sorted([d for d in os.listdir(path)
                      if os.path.isdir(os.path.join(path, d)) and not d.startswith('.')])
    except:
        return []

def list_files(path, ext=None):
    """List files in a directory, optionally filtered by extension."""
    if not os.path.isdir(path):
        return []
    try:
        files = [f for f in os.listdir(path)
                if os.path.isfile(os.path.join(path, f)) and not f.startswith('.')]
        if ext:
            files = [f for f in files if f.endswith(ext)]
        return sorted(files)
    except:
        return []

# ====================================================================
# BUILD INVENTORY
# ====================================================================
inventory = {
    "meta": {
        "scanner": "ama-scan-v1.0",
        "timestamp": TIMESTAMP,
        "platform": sys.platform,
        "hostname": os.environ.get("COMPUTERNAME", "unknown")
    },
    "scan_results": {
        "subagents": [],
        "skills_active": [],
        "skills_archived": [],
        "codex_skills": [],
        "mcp_servers": [],
        "hooks": [],
        "personas": [],
        "external_agents": [],
        "scripts": []
    },
    "frameworks": {},
    "issues": [],
    "stats": {}
}

print("🔍 AMA Scanner v1.0 — Scanning agent ecosystem...\n")

# -------------------------------------------------------------------
# 1. Pi Agent Sub-agents
# -------------------------------------------------------------------
print("📦 Pi Agent Sub-agents...")
agents_dir = os.path.join(HOME, ".pi", "agent", "agents")
if os.path.isdir(agents_dir):
    for f in list_files(agents_dir, ".md"):
        fpath = os.path.join(agents_dir, f)
        content = safe_read(fpath, 800)
        name = f.replace(".md", "")

        # Extract frontmatter
        desc = ""
        model = "unknown"
        thinking = "unknown"
        tools_list = []
        in_frontmatter = False
        for line in content.split('\n'):
            if line.strip() == '---':
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    break
            if in_frontmatter:
                if line.lower().startswith('description:'):
                    desc = line.split(':', 1)[1].strip().strip('"').strip("'")
                if line.lower().startswith('model:'):
                    model = line.split(':', 1)[1].strip()
                if 'thinking' in line.lower():
                    thinking = line.split(':', 1)[1].strip()
                if line.lower().startswith('tools:'):
                    tools_str = line.split(':', 1)[1].strip()
                    tools_list = [t.strip() for t in tools_str.split(',') if t.strip()]

        inventory["scan_results"]["subagents"].append({
            "name": name,
            "framework": "pi",
            "type": "subagent",
            "source_path": fpath,
            "description": desc or name,
            "model": model,
            "thinking": thinking,
            "tools": tools_list,
            "hash": file_hash(fpath)
        })
    count = len(inventory["scan_results"]["subagents"])
    print(f"   ✓ Found {count} sub-agents")
else:
    print("   ✗ Directory not found")

# -------------------------------------------------------------------
# 2. Claude Code Active Skills
# -------------------------------------------------------------------
print("📦 Claude Code Active Skills...")
skills_dir = os.path.join(HOME, ".claude", "skills")
if os.path.isdir(skills_dir):
    for d in list_dirs(skills_dir):
        dpath = os.path.join(skills_dir, d)
        skill_md = os.path.join(dpath, "SKILL.md")
        is_symlink = os.path.islink(dpath) if hasattr(os.path, 'islink') else os.path.isdir(dpath)

        # Quick peek at SKILL.md for description
        desc = ""
        if os.path.exists(skill_md):
            content = safe_read(skill_md, 500)
            for line in content.split('\n'):
                if line.lower().startswith('description:'):
                    desc = line.split(':', 1)[1].strip().strip('"').strip("'")
                    break

        inventory["scan_results"]["skills_active"].append({
            "name": d,
            "framework": "claude",
            "type": "skill",
            "source_path": dpath,
            "description": desc or d,
            "is_external_symlink": is_symlink,
            "has_skill_md": os.path.exists(skill_md),
            "hash": file_hash(skill_md) if os.path.exists(skill_md) else "NO_SKILL_MD"
        })
    count = len(inventory["scan_results"]["skills_active"])
    print(f"   ✓ Found {count} active skills")
else:
    print("   ✗ Directory not found")

# -------------------------------------------------------------------
# 3. Claude Code Archived Skills
# -------------------------------------------------------------------
print("📦 Claude Code Archived Skills...")
archived_dir = os.path.join(HOME, ".claude", "skills-archived")
if os.path.isdir(archived_dir):
    for d in list_dirs(archived_dir):
        dpath = os.path.join(archived_dir, d)
        inventory["scan_results"]["skills_archived"].append({
            "name": d,
            "framework": "claude",
            "type": "skill_archived",
            "source_path": dpath,
            "status": "archived",
            "hash": "ARCHIVED"
        })
    count = len(inventory["scan_results"]["skills_archived"])
    print(f"   ✓ Found {count} archived skills")
else:
    print("   ✗ Directory not found")

# -------------------------------------------------------------------
# 4. Codex Skills
# -------------------------------------------------------------------
print("📦 Codex CLI Skills...")
codex_dir = os.path.join(HOME, ".codex", "skills")
if os.path.isdir(codex_dir):
    for d in list_dirs(codex_dir):
        dpath = os.path.join(codex_dir, d)
        if d.startswith('.'):
            continue
        inventory["scan_results"]["codex_skills"].append({
            "name": d,
            "framework": "codex",
            "type": "skill",
            "source_path": dpath,
            "hash": "CODEX"
        })
    count = len(inventory["scan_results"]["codex_skills"])
    print(f"   ✓ Found {count} Codex skills")
else:
    print("   ✗ Directory not found")

# -------------------------------------------------------------------
# 5. MCP Servers
# -------------------------------------------------------------------
print("📦 MCP Servers...")
mcp_files = [
    os.path.join(HOME, ".pi", "agent", "mcp.json"),
    os.path.join(HOME, ".claude", "settings.json"),
]
for mcp_f in mcp_files:
    if os.path.exists(mcp_f):
        try:
            data = json.loads(safe_read(mcp_f, 10000))
            servers = data.get("mcpServers", {})
            if not servers:
                # Check nested in settings
                servers = data.get("mcpServer", {})
            for sname, sconf in servers.items():
                if isinstance(sconf, dict):
                    inventory["scan_results"]["mcp_servers"].append({
                        "name": sname,
                        "framework": "mcp",
                        "type": "mcp_server",
                        "command": sconf.get("command", "unknown"),
                        "args": sconf.get("args", []),
                        "source_file": mcp_f
                    })
        except Exception as e:
            pass
count = len(inventory["scan_results"]["mcp_servers"])
print(f"   ✓ Found {count} MCP servers")

# -------------------------------------------------------------------
# 6. Hooks
# -------------------------------------------------------------------
print("📦 Claude Code Hooks...")
hooks_dir = os.path.join(HOME, ".claude", "hooks")
if os.path.isdir(hooks_dir):
    for f in list_files(hooks_dir, ".py"):
        fpath = os.path.join(hooks_dir, f)
        content = safe_read(fpath, 600)
        hook_type = "unknown"
        if "PreToolUse" in content or "pre_tool" in content.lower():
            hook_type = "PreToolUse"
        if "SessionStart" in content or "session_start" in content.lower():
            hook_type = "SessionStart"
        if "Stop" in content or "stop" in content.lower():
            hook_type = "Stop"
        if "PostToolUse" in content:
            hook_type = "PostToolUse"

        inventory["scan_results"]["hooks"].append({
            "name": f.replace(".py", ""),
            "framework": "claude",
            "type": "hook",
            "hook_event": hook_type,
            "source_path": fpath,
            "hash": file_hash(fpath)
        })
    count = len(inventory["scan_results"]["hooks"])
    print(f"   ✓ Found {count} hooks")
else:
    print("   ✗ Directory not found")

# -------------------------------------------------------------------
# 7. Personas
# -------------------------------------------------------------------
print("📦 Pi Agent Personas...")
personas_file = os.path.join(HOME, ".pi", "agent", "personas", "personas.json")
if os.path.exists(personas_file):
    try:
        pdata = json.loads(safe_read(personas_file, 5000))
        for pname, pconf in pdata.items():
            thinking_level = "unknown"
            desc = ""
            if isinstance(pconf, dict):
                thinking_level = pconf.get("thinkingLevel", pconf.get("thinking", "unknown"))
                desc = pconf.get("description", "")
            inventory["scan_results"]["personas"].append({
                "name": pname,
                "framework": "pi",
                "type": "persona",
                "thinking_level": thinking_level,
                "description": desc,
                "source_path": personas_file
            })
    except Exception as e:
        print(f"   ⚠ Error reading personas: {e}")
    count = len(inventory["scan_results"]["personas"])
    print(f"   ✓ Found {count} personas")
else:
    print("   ✗ File not found")

# -------------------------------------------------------------------
# 8. External Agents
# -------------------------------------------------------------------
print("📦 External Agents...")
external_targets = [
    ("d:/agent-tools", "python-agent", ["CLAUDE.md", "agent.py", "pyproject.toml"]),
    ("d:/agent-browser", "browser-agent", ["AGENTS.md", "README.md"]),
    (os.path.join(HOME, ".agent-browser"), "browser-agent-clone", ["AGENTS.md"]),
    (os.path.join(HOME, "pi-agent-toolkit"), "pi-toolkit", ["README.md", "package.json"]),
]
for ext_path, ext_type, key_files in external_targets:
    if os.path.isdir(ext_path):
        found_files = [f for f in key_files if os.path.exists(os.path.join(ext_path, f))]
        inventory["scan_results"]["external_agents"].append({
            "name": os.path.basename(ext_path),
            "framework": "external",
            "type": ext_type,
            "source_path": ext_path,
            "key_files_found": found_files,
            "hash": "EXTERNAL"
        })
count = len(inventory["scan_results"]["external_agents"])
print(f"   ✓ Found {count} external agents")

# -------------------------------------------------------------------
# 9. Pi Scripts
# -------------------------------------------------------------------
print("📦 Pi Agent Scripts...")
scripts_dir = os.path.join(HOME, ".pi", "agent", "scripts")
if os.path.isdir(scripts_dir):
    for f in list_files(scripts_dir, ".sh"):
        fpath = os.path.join(scripts_dir, f)
        inventory["scan_results"]["scripts"].append({
            "name": f.replace(".sh", ""),
            "framework": "pi",
            "type": "script",
            "source_path": fpath,
            "hash": file_hash(fpath)
        })
    count = len(inventory["scan_results"]["scripts"])
    print(f"   ✓ Found {count} scripts")
else:
    print("   ✗ Directory not found")

# -------------------------------------------------------------------
# COMPUTE STATS
# -------------------------------------------------------------------
print("\n📊 Computing statistics...")
s = inventory["scan_results"]
stats = {
    "total_assets": sum(len(v) for v in s.values()),
    "by_type": {k: len(v) for k, v in s.items()},
    "frameworks_detected": ["pi", "claude", "codex", "mcp", "external"],
    "health_summary": {}
}
inventory["stats"] = stats

# -------------------------------------------------------------------
# FRAMEWORKS SUMMARY
# -------------------------------------------------------------------
inventory["frameworks"] = {
    "pi": {
        "root": os.path.join(HOME, ".pi", "agent"),
        "status": "active",
        "subagents": len(s["subagents"]),
        "personas": len(s["personas"]),
        "scripts": len(s["scripts"]),
        "mcp_servers": len(s["mcp_servers"]),
    },
    "claude": {
        "root": os.path.join(HOME, ".claude"),
        "status": "active",
        "active_skills": len(s["skills_active"]),
        "archived_skills": len(s["skills_archived"]),
        "hooks": len(s["hooks"]),
    },
    "codex": {
        "root": os.path.join(HOME, ".codex"),
        "status": "active" if os.path.isdir(os.path.join(HOME, ".codex")) else "missing",
        "skills": len(s["codex_skills"]),
    },
    "external": {
        "agents": len(s["external_agents"]),
    }
}

# -------------------------------------------------------------------
# ISSUES DETECTION
# -------------------------------------------------------------------
issues = []
if len(s["skills_archived"]) > 150:
    issues.append({
        "severity": "warning",
        "category": "skill_sprawl",
        "message": f"{len(s['skills_archived'])} archived skills — consider permanent deletion",
        "recommendation": "Run ama-cleanup.sh to remove skills archived >180 days"
    })
if len(s["skills_active"]) > 150:
    issues.append({
        "severity": "warning",
        "category": "skill_sprawl",
        "message": f"{len(s['skills_active'])} active skills — skill sprawl detected",
        "recommendation": "Review and archive unused skills"
    })
if len(s["mcp_servers"]) == 0:
    issues.append({
        "severity": "info",
        "category": "mcp",
        "message": "No MCP servers detected in standard locations",
        "recommendation": "Check mcp.json and settings.json for MCP configurations"
    })
if len(s["personas"]) == 0:
    issues.append({
        "severity": "info",
        "category": "personas",
        "message": "No personas detected",
        "recommendation": "Check personas.json format"
    })
if len(s["hooks"]) < 2:
    issues.append({
        "severity": "medium",
        "category": "safety",
        "message": "Minimal hooks detected — safety guardrails may be insufficient",
        "recommendation": "Add PreToolUse guard hook"
    })

inventory["issues"] = issues

# -------------------------------------------------------------------
# WRITE OUTPUT
# -------------------------------------------------------------------
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(inventory, f, indent=2, ensure_ascii=False, default=str)

# Save a "latest" copy for easy access
latest_path = os.path.join(DATA_DIR, "agent-inventory-latest.json")
with open(latest_path, 'w', encoding='utf-8') as f:
    json.dump(inventory, f, indent=2, ensure_ascii=False, default=str)

# -------------------------------------------------------------------
# PRINT SUMMARY
# -------------------------------------------------------------------
print(f"\n{'='*60}")
print(f"✅ AMA Scan Complete!")
print(f"{'='*60}")
print(f"  Output:  {OUTPUT_FILE}")
print(f"  Latest:  {latest_path}")
print(f"  Assets:  {stats['total_assets']} total")
print(f"{'='*60}")
print(f"  Sub-agents:       {stats['by_type']['subagents']:>4}")
print(f"  Active skills:    {stats['by_type']['skills_active']:>4}")
print(f"  Archived skills:  {stats['by_type']['skills_archived']:>4}")
print(f"  Codex skills:     {stats['by_type']['codex_skills']:>4}")
print(f"  MCP servers:      {stats['by_type']['mcp_servers']:>4}")
print(f"  Hooks:            {stats['by_type']['hooks']:>4}")
print(f"  Personas:         {stats['by_type']['personas']:>4}")
print(f"  External agents:  {stats['by_type']['external_agents']:>4}")
print(f"  Scripts:          {stats['by_type']['scripts']:>4}")
print(f"{'='*60}")

if issues:
    print(f"\n🔔 {len(issues)} issue(s) detected:")
    for i in issues:
        sev_emoji = {"warning": "⚠️", "medium": "🟡", "info": "ℹ️"}.get(i["severity"], "•")
        print(f"  {sev_emoji} [{i['category']}] {i['message']}")
        print(f"     → {i['recommendation']}")
else:
    print("\n✅ All systems healthy")

print(f"\n📄 Human-readable report: Run 'python ama-report.py' to generate")
