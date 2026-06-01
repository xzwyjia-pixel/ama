#!/bin/bash
# =============================================================================
# AMA Scanner v1.0 — Agent Inventory Discovery Engine
# Scans all agent directories, generates inventory.json + human-readable report
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/../output"
mkdir -p "$OUTPUT_DIR"

TIMESTAMP=$(date -Iseconds)
INVENTORY_JSON="$OUTPUT_DIR/agent-inventory-$(date +%Y%m%d-%H%M%S).json"
REPORT_MD="$OUTPUT_DIR/agent-inventory-report-$(date +%Y%m%d-%H%M%S).md"

echo "🔍 AMA Scanner v1.0 — Scanning all agent assets..."
echo "================================================"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
count_files() { find "$1" -type f 2>/dev/null | wc -l; }
count_dirs()  { find "$1" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l; }
safe_read()   { cat "$1" 2>/dev/null || echo ""; }
file_age_days() {
    if [ -f "$1" ]; then
        local mtime
        mtime=$(stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0)
        local now
        now=$(date +%s)
        echo $(( (now - mtime) / 86400 ))
    else
        echo "N/A"
    fi
}

# ---------------------------------------------------------------------------
# JSON builder — accumulating in temp file for incremental build
# ---------------------------------------------------------------------------
TMP_JSON=$(mktemp)
echo '{
  "meta": {
    "scanner_version": "1.0.0",
    "scan_timestamp": "'"$TIMESTAMP"'",
    "hostname": "'"$(hostname 2>/dev/null || echo 'unknown')"'",
    "platform": "'"$(uname -s 2>/dev/null || echo 'unknown')"'"
  },
  "summary": {},
  "frameworks": {},
  "subagents": [],
  "skills_active": [],
  "skills_archived": [],
  "mcp_servers": [],
  "hooks": [],
  "personas": [],
  "external_agents": [],
  "codex_skills": [],
  "scripts": []
}' > "$TMP_JSON"

# ---------------------------------------------------------------------------
# 1. Scan Pi Agent Framework
# ---------------------------------------------------------------------------
echo ""
echo "📦 Scanning Pi Agent Framework..."
PI_DIR="$HOME/.pi/agent"
if [ -d "$PI_DIR" ]; then
    AGENTS_DIR="$PI_DIR/agents"
    if [ -d "$AGENTS_DIR" ]; then
        AGENT_COUNT=0
        for f in "$AGENTS_DIR"/*.md; do
            [ -f "$f" ] || continue
            AGENT_COUNT=$((AGENT_COUNT + 1))
            fname=$(basename "$f" .md)
            # Extract YAML frontmatter if present
            frontmatter=$(sed -n '/^---$/,/^---$/p' "$f" 2>/dev/null | head -30 || echo "")
            desc=$(echo "$frontmatter" | grep -i "description:" | head -1 | sed 's/.*description:\s*//' | sed 's/^"//;s/"$//' || echo "")
            model=$(echo "$frontmatter" | grep -i "model:" | head -1 | sed 's/.*model:\s*//' || echo "unknown")
            tools=$(echo "$frontmatter" | grep -i "tools:" | head -1 | sed 's/.*tools:\s*//' || echo "unknown")

            cat >> "$OUTPUT_DIR/subagent_$fname.json" <<EOF
{"name":"$fname","source":"$f","framework":"pi","type":"subagent","description":"$desc","model":"$model","tools":"$tools","file_age_days":$(file_age_days "$f")}
EOF
        done
        echo "   → Found $AGENT_COUNT Pi sub-agents"
    fi

    # Personas
    PERSONAS_FILE="$PI_DIR/personas/personas.json"
    if [ -f "$PERSONAS_FILE" ]; then
        PERSONA_COUNT=$(python3 -c "import json; print(len(json.load(open('$PERSONAS_FILE'))))" 2>/dev/null || echo 0)
        echo "   → Found $PERSONA_COUNT personas"
    fi

    # Scripts
    SCRIPTS_DIR="$PI_DIR/scripts"
    if [ -d "$SCRIPTS_DIR" ]; then
        SCRIPT_COUNT=$(count_files "$SCRIPTS_DIR")
        echo "   → Found $SCRIPT_COUNT scripts"
    fi
else
    echo "   → Pi Agent directory not found"
fi

# ---------------------------------------------------------------------------
# 2. Scan Claude Code Skills
# ---------------------------------------------------------------------------
echo ""
echo "📦 Scanning Claude Code Skills..."
CLAUDE_SKILLS_DIR="$HOME/.claude/skills"
CLAUDE_ARCHIVED_DIR="$HOME/.claude/skills-archived"

ACTIVE_SKILL_COUNT=0
ARCHIVED_SKILL_COUNT=0

if [ -d "$CLAUDE_SKILLS_DIR" ]; then
    for skill_dir in "$CLAUDE_SKILLS_DIR"/*/; do
        [ -d "$skill_dir" ] || continue
        ACTIVE_SKILL_COUNT=$((ACTIVE_SKILL_COUNT + 1))
    done
    echo "   → Found $ACTIVE_SKILL_COUNT active skills"
fi

if [ -d "$CLAUDE_ARCHIVED_DIR" ]; then
    for skill_dir in "$CLAUDE_ARCHIVED_DIR"/*/; do
        [ -d "$skill_dir" ] || continue
        ARCHIVED_SKILL_COUNT=$((ARCHIVED_SKILL_COUNT + 1))
    done
    echo "   → Found $ARCHIVED_SKILL_COUNT archived skills"
fi

# ---------------------------------------------------------------------------
# 3. Scan Codex Skills
# ---------------------------------------------------------------------------
echo ""
echo "📦 Scanning Codex CLI..."
CODEX_SKILLS_DIR="$HOME/.codex/skills"
CODEX_SKILL_COUNT=0
if [ -d "$CODEX_SKILLS_DIR" ]; then
    CODEX_SKILL_COUNT=$(count_dirs "$CODEX_SKILLS_DIR")
    echo "   → Found $CODEX_SKILL_COUNT Codex skills"
fi

# ---------------------------------------------------------------------------
# 4. Scan MCP Servers
# ---------------------------------------------------------------------------
echo ""
echo "📦 Scanning MCP Servers..."
MCP_FILE="$HOME/.pi/agent/mcp.json"
MCP_COUNT=0
if [ -f "$MCP_FILE" ]; then
    MCP_COUNT=$(python3 -c "
import json
d=json.load(open('$MCP_FILE'))
print(len(d.get('mcpServers', d)) if isinstance(d, dict) else len(d))
" 2>/dev/null || echo 0)
    echo "   → Found $MCP_COUNT MCP servers in Pi config"
fi

# ---------------------------------------------------------------------------
# 5. Scan Hooks
# ---------------------------------------------------------------------------
echo ""
echo "📦 Scanning Claude Code Hooks..."
HOOKS_DIR="$HOME/.claude/hooks"
HOOK_COUNT=0
if [ -d "$HOOKS_DIR" ]; then
    HOOK_COUNT=$(count_files "$HOOKS_DIR")
    echo "   → Found $HOOK_COUNT hooks"
fi

# ---------------------------------------------------------------------------
# 6. Scan External Agents
# ---------------------------------------------------------------------------
echo ""
echo "📦 Scanning External Agents..."
EXT_COUNT=0
for ext_dir in "d:/agent-tools" "d:/agent-browser" "$HOME/.agent-browser" "$HOME/pi-agent-toolkit"; do
    if [ -d "$ext_dir" ]; then
        EXT_COUNT=$((EXT_COUNT + 1))
        ext_name=$(basename "$ext_dir")
        has_agent_md=""
        [ -f "$ext_dir/CLAUDE.md" ] && has_agent_md="CLAUDE.md"
        [ -f "$ext_dir/AGENTS.md" ] && has_agent_md="$has_agent_md AGENTS.md"
        echo "   → $ext_name ($has_agent_md)"
    fi
done

# ---------------------------------------------------------------------------
# Generate structured inventory JSON
# ---------------------------------------------------------------------------
echo ""
echo "📝 Generating inventory JSON..."

python3 <<PYEOF
import json, os, glob, hashlib
from datetime import datetime

HOME = os.path.expanduser("~")
TIMESTAMP = "$TIMESTAMP"
OUTPUT = "$INVENTORY_JSON"

def file_hash(path):
    try:
        with open(path, 'rb') as f:
            return hashlib.md5(f.read(1024)).hexdigest()[:8]
    except:
        return "ERROR"

def safe_name(p):
    return os.path.basename(p).replace('.md','').replace('.json','').replace('.yaml','').replace('.yml','')

# ===================== BUILD INVENTORY =====================
inventory = {
    "meta": {
        "scanner": "ama-scan-v1.0",
        "timestamp": TIMESTAMP,
        "hostname": os.uname().nodename if hasattr(os, 'uname') else "windows"
    },
    "frameworks": {},
    "assets": {
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
    "relationships": [],
    "stats": {}
}

# --- Pi sub-agents ---
agents_dir = os.path.join(HOME, ".pi", "agent", "agents")
if os.path.isdir(agents_dir):
    for f in sorted(glob.glob(os.path.join(agents_dir, "*.md"))):
        name = safe_name(f)
        content = open(f, 'r', encoding='utf-8', errors='ignore').read()[:500]
        desc_line = ""
        model = "unknown"
        for line in content.split('\n'):
            if 'description' in line.lower() and not desc_line:
                desc_line = line.split(':',1)[-1].strip().strip('"')
            if 'model' in line.lower():
                model = line.split(':',1)[-1].strip().strip('"')
        inventory["assets"]["subagents"].append({
            "name": name,
            "framework": "pi",
            "type": "subagent",
            "source_path": f,
            "description": desc_line or name,
            "model": model,
            "hash": file_hash(f)
        })

# --- Claude active skills ---
skills_dir = os.path.join(HOME, ".claude", "skills")
if os.path.isdir(skills_dir):
    for d in sorted(glob.glob(os.path.join(skills_dir, "*/"))):
        name = os.path.basename(d.rstrip('/'))
        skill_md = os.path.join(d, "SKILL.md")
        is_symlink = os.path.islink(d) if hasattr(os.path, 'islink') else False
        inventory["assets"]["skills_active"].append({
            "name": name,
            "framework": "claude",
            "type": "skill",
            "source_path": d,
            "has_skill_md": os.path.exists(skill_md),
            "is_external": is_symlink,
            "hash": file_hash(skill_md) if os.path.exists(skill_md) else "NONE"
        })

# --- Claude archived skills ---
archived_dir = os.path.join(HOME, ".claude", "skills-archived")
if os.path.isdir(archived_dir):
    for d in sorted(glob.glob(os.path.join(archived_dir, "*/"))):
        name = os.path.basename(d.rstrip('/'))
        inventory["assets"]["skills_archived"].append({
            "name": name,
            "framework": "claude",
            "type": "skill_archived",
            "source_path": d,
            "hash": "ARCHIVED"
        })

# --- Codex skills ---
codex_dir = os.path.join(HOME, ".codex", "skills")
if os.path.isdir(codex_dir):
    for d in sorted(glob.glob(os.path.join(codex_dir, "*/"))):
        name = os.path.basename(d.rstrip('/'))
        if name.startswith('.'): continue
        inventory["assets"]["codex_skills"].append({
            "name": name,
            "framework": "codex",
            "type": "skill",
            "source_path": d,
            "hash": "CODEX"
        })

# --- MCP servers ---
mcp_file = os.path.join(HOME, ".pi", "agent", "mcp.json")
if os.path.exists(mcp_file):
    try:
        mcp_data = json.load(open(mcp_file, 'r'))
        servers = mcp_data.get("mcpServers", mcp_data)
        for sname, sconf in servers.items():
            if isinstance(sconf, dict):
                inventory["assets"]["mcp_servers"].append({
                    "name": sname,
                    "framework": "mcp",
                    "type": "mcp_server",
                    "command": sconf.get("command", "unknown"),
                    "args": sconf.get("args", []),
                    "source_path": mcp_file
                })
    except: pass

# --- Hooks ---
hooks_dir = os.path.join(HOME, ".claude", "hooks")
if os.path.isdir(hooks_dir):
    for f in sorted(glob.glob(os.path.join(hooks_dir, "*.py"))):
        name = safe_name(f)
        content = open(f, 'r', encoding='utf-8', errors='ignore').read()[:300]
        hook_type = "unknown"
        if "PreToolUse" in content: hook_type = "PreToolUse"
        if "SessionStart" in content: hook_type = "SessionStart"
        if "Stop" in content: hook_type = "Stop"
        inventory["assets"]["hooks"].append({
            "name": name,
            "framework": "claude",
            "type": "hook",
            "hook_type": hook_type,
            "source_path": f,
            "hash": file_hash(f)
        })

# --- Personas ---
personas_file = os.path.join(HOME, ".pi", "agent", "personas", "personas.json")
if os.path.exists(personas_file):
    try:
        pdata = json.load(open(personas_file, 'r'))
        for pname, pconf in pdata.items():
            inventory["assets"]["personas"].append({
                "name": pname,
                "framework": "pi",
                "type": "persona",
                "thinking": pconf.get("thinking", "unknown") if isinstance(pconf, dict) else "unknown",
                "source_path": personas_file
            })
    except: pass

# --- External agents ---
external_dirs = [
    ("d:/agent-tools", "python-agent"),
    ("d:/agent-browser", "browser-agent"),
    (os.path.join(HOME, ".agent-browser"), "browser-agent-clone"),
    (os.path.join(HOME, "pi-agent-toolkit"), "pi-toolkit"),
]
for ext_path, ext_type in external_dirs:
    if os.path.isdir(ext_path):
        has_files = []
        for check in ["CLAUDE.md", "AGENTS.md", "agent.py", "SKILL.md"]:
            if os.path.exists(os.path.join(ext_path, check)):
                has_files.append(check)
        inventory["assets"]["external_agents"].append({
            "name": os.path.basename(ext_path),
            "framework": "external",
            "type": ext_type,
            "source_path": ext_path,
            "key_files": has_files,
            "hash": "EXTERNAL"
        })

# --- Pi scripts ---
scripts_dir = os.path.join(HOME, ".pi", "agent", "scripts")
if os.path.isdir(scripts_dir):
    for f in sorted(glob.glob(os.path.join(scripts_dir, "*.sh"))):
        inventory["assets"]["scripts"].append({
            "name": safe_name(f),
            "framework": "pi",
            "type": "script",
            "source_path": f
        })

# --- Compute stats ---
s = inventory["assets"]
inventory["stats"] = {
    "total_assets": sum(len(v) for v in s.values()),
    "subagents": len(s["subagents"]),
    "skills_active": len(s["skills_active"]),
    "skills_archived": len(s["skills_archived"]),
    "codex_skills": len(s["codex_skills"]),
    "mcp_servers": len(s["mcp_servers"]),
    "hooks": len(s["hooks"]),
    "personas": len(s["personas"]),
    "external_agents": len(s["external_agents"]),
    "scripts": len(s["scripts"]),
    "frameworks_detected": ["pi", "claude", "codex", "mcp", "external"]
}

# --- Frameworks ---
inventory["frameworks"] = {
    "pi": {
        "root": os.path.join(HOME, ".pi", "agent"),
        "subagents": len(s["subagents"]),
        "personas": len(s["personas"]),
        "mcp_servers": len(s["mcp_servers"]),
        "scripts": len(s["scripts"]),
        "health": "OK"
    },
    "claude": {
        "root": os.path.join(HOME, ".claude"),
        "active_skills": len(s["skills_active"]),
        "archived_skills": len(s["skills_archived"]),
        "hooks": len(s["hooks"]),
        "health": "OK"
    },
    "codex": {
        "root": os.path.join(HOME, ".codex"),
        "skills": len(s["codex_skills"]),
        "health": "OK" if os.path.isdir(os.path.join(HOME, ".codex")) else "MISSING"
    },
    "external": {
        "agents": len(s["external_agents"]),
        "health": "OK"
    }
}

# --- Write ---
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(inventory, f, indent=2, ensure_ascii=False, default=str)

# --- Summary ---
stats = inventory["stats"]
print(f"✓ Inventory JSON written: {OUTPUT}")
print(f"  Total assets: {stats['total_assets']}")
print(f"  Sub-agents: {stats['subagents']}")
print(f"  Active skills: {stats['skills_active']}")
print(f"  Archived skills: {stats['skills_archived']}")
print(f"  Codex skills: {stats['codex_skills']}")
print(f"  MCP servers: {stats['mcp_servers']}")
print(f"  Hooks: {stats['hooks']}")
print(f"  Personas: {stats['personas']}")
print(f"  External agents: {stats['external_agents']}")
print(f"  Scripts: {stats['scripts']}")

# --- Detect issues ---
issues = []
if stats["skills_archived"] > 100:
    issues.append(f"⚠ {stats['skills_archived']} archived skills — consider cleanup")
if stats["skills_active"] > 100:
    issues.append(f"⚠ {stats['skills_active']} active skills — skill sprawl detected")
if stats["mcp_servers"] == 0:
    issues.append("⚠ No MCP servers detected")
if stats["hooks"] < 2:
    issues.append("⚠ Minimal hooks — consider adding PreToolUse guard")

if issues:
    print("\n🔔 Issues detected:")
    for i in issues:
        print(f"  {i}")
else:
    print("\n✅ No issues detected")
PYEOF

echo ""
echo "================================================"
echo "✅ AMA Scan complete!"
echo "   JSON: $INVENTORY_JSON"
echo "================================================"
