#!/usr/bin/env python3
"""
AMA Agent Store Server v1.0 — MVP Backend
Zero-dependency: uses Python stdlib only (http.server + sqlite3 + json)

Endpoints:
  GET  /api/agents              — list all agents (with filter/search)
  GET  /api/agents/<id>         — agent detail
  POST /api/agents/<id>/install — install/register an agent
  POST /api/agents/<id>/enable  — enable an agent
  POST /api/agents/<id>/disable — disable an agent
  POST /api/agents/<id>/archive — archive an agent
  GET  /api/stats               — summary statistics
  GET  /api/health              — health check
  GET  /                        — serves store.html
"""
import json, os, sys, io, sqlite3, hashlib, time, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PUBLIC_DIR = os.path.join(PROJECT_ROOT, "public")
DB_PATH = os.path.join(DATA_DIR, "ama-registry.db")
INVENTORY_PATH = os.path.join(DATA_DIR, "agent-inventory-latest.json")

os.makedirs(DATA_DIR, exist_ok=True)

# ====================================================================
# Database Layer
# ====================================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            framework TEXT NOT NULL,
            agent_type TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            description TEXT DEFAULT '',
            source_path TEXT,
            version TEXT DEFAULT '1.0.0',
            price REAL DEFAULT 0.0,
            installs INTEGER DEFAULT 0,
            rating REAL DEFAULT 0.0,
            discovered_at TEXT,
            last_seen_at TEXT,
            metadata TEXT DEFAULT '{}'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT,
            action TEXT,
            timestamp TEXT DEFAULT (datetime('now')),
            details TEXT
        )
    """)
    conn.commit()
    return conn

def seed_from_inventory(conn):
    """Import agents from the scan inventory into the store database."""
    if not os.path.exists(INVENTORY_PATH):
        print("No inventory found. Run ama-scan.py first.")
        return

    inv = json.load(open(INVENTORY_PATH, 'r', encoding='utf-8'))
    assets = inv["scan_results"]

    # Map inventory categories to store entries
    category_map = {
        "subagents":        ("pi", "subagent", 4.9),
        "skills_active":    ("claude", "skill", 9.9),
        "skills_archived":  ("claude", "skill_archived", 0),
        "codex_skills":     ("codex", "skill", 4.9),
        "mcp_servers":      ("mcp", "mcp_server", 14.9),
        "hooks":            ("claude", "hook", 2.9),
        "personas":         ("pi", "persona", 2.9),
        "external_agents":  ("external", "agent", 19.9),
        "scripts":          ("pi", "script", 0),
    }

    count = 0
    for cat, items in assets.items():
        if cat not in category_map:
            continue
        framework, atype, price = category_map[cat]
        for item in items:
            name = item.get("name", "unknown")
            agent_id = hashlib.md5(f"{framework}:{atype}:{name}".encode()).hexdigest()[:12]
            source_path = item.get("source_path", "")
            desc = item.get("description", name)

            # Check if exists
            cur = conn.execute("SELECT id FROM agents WHERE id = ?", (agent_id,))
            exists = cur.fetchone()

            if not exists:
                conn.execute("""
                    INSERT INTO agents (id, name, framework, agent_type, status,
                                       description, source_path, price, metadata)
                    VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?)
                """, (agent_id, name, framework, atype,
                      desc[:200], source_path, price,
                      json.dumps(item, ensure_ascii=False)))
                count += 1
            else:
                # Update last_seen
                conn.execute("UPDATE agents SET last_seen_at = datetime('now') WHERE id = ?", (agent_id,))

    conn.commit()
    print(f"Seeded {count} new agents into store database")

# ====================================================================
# API Handlers
# ====================================================================
def api_list_agents(params, conn):
    """List agents with optional filters."""
    framework = params.get("framework", [None])[0]
    agent_type = params.get("type", [None])[0]
    status = params.get("status", ["active"])[0]
    search = params.get("search", [None])[0]
    sort = params.get("sort", ["name"])[0]
    limit = min(int(params.get("limit", [50])[0]), 200)
    offset = int(params.get("offset", [0])[0])

    query = "SELECT * FROM agents WHERE 1=1"
    args = []

    if framework:
        query += " AND framework = ?"
        args.append(framework)
    if agent_type:
        query += " AND agent_type = ?"
        args.append(agent_type)
    if status:
        query += " AND status = ?"
        args.append(status)
    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        args.extend([f"%{search}%", f"%{search}%"])

    # Count total
    count_q = query.replace("SELECT *", "SELECT COUNT(*)")
    total = conn.execute(count_q, args).fetchone()[0]

    # Sort & paginate
    valid_sorts = {"name": "name", "price": "price", "installs": "installs DESC", "rating": "rating DESC"}
    order = valid_sorts.get(sort, "name")
    query += f" ORDER BY {order} LIMIT ? OFFSET ?"
    args.extend([limit, offset])

    rows = conn.execute(query, args).fetchall()
    cols = [d[0] for d in conn.execute("PRAGMA table_info(agents)")]

    agents = []
    for row in rows:
        agent = dict(zip(cols, row))
        agent["metadata"] = json.loads(agent.get("metadata", "{}"))
        agents.append(agent)

    return {"total": total, "limit": limit, "offset": offset, "agents": agents}

def api_get_agent(agent_id, conn):
    row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
    if not row:
        return None
    cols = [d[0] for d in conn.execute("PRAGMA table_info(agents)")]
    agent = dict(zip(cols, row))
    agent["metadata"] = json.loads(agent.get("metadata", "{}"))
    return agent

def api_agent_action(agent_id, action, conn):
    """Handle lifecycle actions: install, enable, disable, archive."""
    valid_actions = {
        "install": "active",
        "enable": "active",
        "disable": "inactive",
        "archive": "archived",
    }
    if action not in valid_actions:
        return {"error": f"Invalid action: {action}"}

    new_status = valid_actions[action]

    # Check agent exists
    row = conn.execute("SELECT id, name FROM agents WHERE id = ?", (agent_id,)).fetchone()
    if not row:
        return {"error": "Agent not found"}

    # Update status
    conn.execute("UPDATE agents SET status = ?, last_seen_at = datetime('now') WHERE id = ?",
                 (new_status, agent_id))

    # If installing, increment installs
    if action == "install":
        conn.execute("UPDATE agents SET installs = installs + 1 WHERE id = ?", (agent_id,))

    # Log activity
    conn.execute("INSERT INTO activity_log (agent_id, action, details) VALUES (?, ?, ?)",
                 (agent_id, action, f"Status changed to {new_status}"))
    conn.commit()

    return {"success": True, "agent_id": agent_id, "action": action, "new_status": new_status}

def api_stats(conn):
    total = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM agents WHERE status = 'active'").fetchone()[0]
    inactive = conn.execute("SELECT COUNT(*) FROM agents WHERE status = 'inactive'").fetchone()[0]
    archived = conn.execute("SELECT COUNT(*) FROM agents WHERE status = 'archived'").fetchone()[0]

    by_framework = {}
    for row in conn.execute("SELECT framework, COUNT(*) FROM agents GROUP BY framework"):
        by_framework[row[0]] = row[1]

    by_type = {}
    for row in conn.execute("SELECT agent_type, COUNT(*) FROM agents GROUP BY agent_type"):
        by_type[row[0]] = row[1]

    total_installs = conn.execute("SELECT SUM(installs) FROM agents").fetchone()[0] or 0
    recent = conn.execute(
        "SELECT action, agent_id, timestamp FROM activity_log ORDER BY id DESC LIMIT 10"
    ).fetchall()

    return {
        "total_agents": total,
        "active": active,
        "inactive": inactive,
        "archived": archived,
        "by_framework": by_framework,
        "by_type": by_type,
        "total_installs": total_installs,
        "recent_activity": [{"action": r[0], "agent_id": r[1], "time": r[2]} for r in recent]
    }

# ====================================================================
# HTTP Server
# ====================================================================
class AMAStoreHandler(BaseHTTPRequestHandler):
    db_conn = None

    def log_message(self, format, *args):
        pass  # Quiet

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode('utf-8')
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def serve_static(self, filepath):
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            ct = "text/html; charset=utf-8"
            if filepath.endswith(".css"): ct = "text/css"
            elif filepath.endswith(".js"): ct = "application/javascript"
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        # Static files
        if path == "/" or path == "/store":
            return self.serve_static(os.path.join(PUBLIC_DIR, "store.html"))
        if path == "/calculator":
            return self.serve_static(os.path.join(PUBLIC_DIR, "index.html"))

        # API routes
        if path == "/api/agents":
            return self.send_json(api_list_agents(params, self.db_conn))
        if path == "/api/stats":
            return self.send_json(api_stats(self.db_conn))
        if path == "/api/health":
            return self.send_json({"status": "healthy", "timestamp": datetime.now().isoformat()})

        # Agent detail
        if path.startswith("/api/agents/"):
            agent_id = path.split("/")[-1]
            agent = api_get_agent(agent_id, self.db_conn)
            if agent:
                return self.send_json(agent)
            return self.send_json({"error": "Agent not found"}, 404)

        return self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Read body
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len else b"{}"
        try:
            data = json.loads(body)
        except:
            data = {}

        # Action endpoints: /api/agents/<id>/<action>
        parts = path.strip("/").split("/")
        if len(parts) == 4 and parts[0] == "api" and parts[1] == "agents":
            agent_id = parts[2]
            action = parts[3]
            return self.send_json(api_agent_action(agent_id, action, self.db_conn))

        return self.send_json({"error": "Not found"}, 404)

# ====================================================================
# Main
# ====================================================================
def main():
    print("=" * 60)
    print("AMA Agent Store Server v1.0")
    print("=" * 60)

    # Init DB
    conn = init_db()
    print(f"  Database: {DB_PATH}")

    # Seed from inventory
    seed_from_inventory(conn)

    # Print stats
    total = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM agents WHERE status='active'").fetchone()[0]
    print(f"  Store catalog: {total} agents ({active} active)")

    # Inject connection into handler
    AMAStoreHandler.db_conn = conn

    # Start server
    port = 8765
    server = HTTPServer(("0.0.0.0", port), AMAStoreHandler)
    print(f"\n  Store:  http://localhost:{port}/store")
    print(f"  Calc:   http://localhost:{port}/calculator")
    print(f"  API:    http://localhost:{port}/api/agents")
    print(f"\nPress Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
        conn.close()

if __name__ == "__main__":
    main()
