#!/usr/bin/env python3
"""
AMA Production Server v1.0
Features: daemon mode, file logging, PID management, graceful shutdown,
          health checks, static caching, CORS, rate limiting stubs.

Usage:
  python ama-server-prod.py              # foreground (for debugging)
  python ama-server-prod.py --daemon     # background daemon
  python ama-server-prod.py --stop       # stop running daemon
  python ama-server-prod.py --status     # check if daemon is running
"""
import json, os, sys, io, sqlite3, hashlib, time, signal, argparse
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ============================================================
# Configuration
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PUBLIC_DIR = os.path.join(PROJECT_ROOT, "public")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
DB_PATH = os.path.join(DATA_DIR, "ama-registry.db")
INVENTORY_PATH = os.path.join(DATA_DIR, "agent-inventory-latest.json")
PID_FILE = os.path.join(PROJECT_ROOT, "ama-server.pid")
LOG_FILE = os.path.join(LOGS_DIR, f"ama-server-{datetime.now().strftime('%Y%m%d')}.log")

PORT = int(os.environ.get("AMA_PORT", "8765"))
HOST = os.environ.get("AMA_HOST", "0.0.0.0")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PUBLIC_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# ============================================================
# Logging
# ============================================================
class Logger:
    def __init__(self, logfile):
        self.logfile = logfile

    def log(self, level, msg):
        ts = datetime.now().isoformat()[:19]
        line = f"[{ts}] [{level:5s}] {msg}"
        print(line)
        try:
            with open(self.logfile, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        except:
            pass

    def info(self, msg): self.log("INFO", msg)
    def warn(self, msg): self.log("WARN", msg)
    def error(self, msg): self.log("ERROR", msg)

logger = Logger(LOG_FILE)

# ============================================================
# Database
# ============================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, framework TEXT NOT NULL,
            agent_type TEXT NOT NULL, status TEXT DEFAULT 'active',
            description TEXT DEFAULT '', source_path TEXT, version TEXT DEFAULT '1.0.0',
            price REAL DEFAULT 0.0, installs INTEGER DEFAULT 0, rating REAL DEFAULT 0.0,
            discovered_at TEXT, last_seen_at TEXT, metadata TEXT DEFAULT '{}'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT,
            action TEXT, timestamp TEXT DEFAULT (datetime('now')),
            details TEXT, ip TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS server_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT (datetime('now')),
            endpoint TEXT, method TEXT, status_code INTEGER,
            response_ms INTEGER, ip TEXT
        )
    """)
    conn.commit()
    return conn

def seed_from_inventory(conn):
    if not os.path.exists(INVENTORY_PATH):
        logger.warn("No inventory found — run ama-scan.py first")
        return 0
    inv = json.load(open(INVENTORY_PATH, 'r', encoding='utf-8'))
    assets = inv["scan_results"]
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
        if cat not in category_map: continue
        framework, atype, price = category_map[cat]
        for item in items:
            name = item.get("name", "unknown")
            agent_id = hashlib.md5(f"{framework}:{atype}:{name}".encode()).hexdigest()[:12]
            desc = item.get("description", name)
            cur = conn.execute("SELECT id FROM agents WHERE id = ?", (agent_id,))
            if not cur.fetchone():
                conn.execute("""
                    INSERT INTO agents (id, name, framework, agent_type, description, source_path, price, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (agent_id, name, framework, atype, desc[:200],
                      item.get("source_path", ""), price, json.dumps(item, ensure_ascii=False)))
                count += 1
            else:
                conn.execute("UPDATE agents SET last_seen_at = datetime('now') WHERE id = ?", (agent_id,))
    conn.commit()
    return count

# ============================================================
# API Logic
# ============================================================
def api_list_agents(params, conn):
    framework = (params.get("framework", [None]) or [None])[0]
    agent_type = (params.get("type", [None]) or [None])[0]
    status = (params.get("status", ["active"]) or ["active"])[0]
    search = (params.get("search", [None]) or [None])[0]
    sort = (params.get("sort", ["name"]) or ["name"])[0]
    limit = min(int((params.get("limit", ["50"]) or ["50"])[0]), 500)
    offset = int((params.get("offset", ["0"]) or ["0"])[0])

    query = "SELECT * FROM agents WHERE 1=1"
    args = []
    if framework and framework != "all":
        query += " AND framework = ?"; args.append(framework)
    if agent_type and agent_type != "all":
        query += " AND agent_type = ?"; args.append(agent_type)
    if status and status != "all":
        query += " AND status = ?"; args.append(status)
    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        args.extend([f"%{search}%", f"%{search}%"])

    count_row = conn.execute(query.replace("SELECT *", "SELECT COUNT(*)"), args).fetchone()
    total = count_row[0] if count_row else 0

    valid_sorts = {"name": "name", "price": "price", "installs": "installs DESC", "rating": "rating DESC"}
    query += f" ORDER BY {valid_sorts.get(sort, 'name')} LIMIT ? OFFSET ?"
    args.extend([limit, offset])

    rows = conn.execute(query, args).fetchall()
    cols = [d[0] for d in conn.execute("PRAGMA table_info(agents)")]
    agents = []
    for row in rows:
        a = dict(zip(cols, row))
        a["metadata"] = json.loads(a.get("metadata", "{}"))
        agents.append(a)
    return {"total": total, "limit": limit, "offset": offset, "agents": agents}

def api_get_agent(agent_id, conn):
    row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
    if not row: return None
    cols = [d[0] for d in conn.execute("PRAGMA table_info(agents)")]
    a = dict(zip(cols, row))
    a["metadata"] = json.loads(a.get("metadata", "{}"))
    return a

def api_agent_action(agent_id, action, conn, ip="127.0.0.1"):
    valid_actions = {"install": "active", "enable": "active", "disable": "inactive", "archive": "archived"}
    if action not in valid_actions:
        return {"error": f"Invalid action: {action}"}
    row = conn.execute("SELECT id, name FROM agents WHERE id = ?", (agent_id,)).fetchone()
    if not row: return {"error": "Agent not found"}
    new_status = valid_actions[action]
    conn.execute("UPDATE agents SET status = ?, last_seen_at = datetime('now') WHERE id = ?", (new_status, agent_id))
    if action == "install":
        conn.execute("UPDATE agents SET installs = installs + 1 WHERE id = ?", (agent_id,))
    conn.execute("INSERT INTO activity_log (agent_id, action, details, ip) VALUES (?, ?, ?, ?)",
                 (agent_id, action, f"Status changed to {new_status}", ip))
    conn.commit()
    return {"success": True, "agent_id": agent_id, "action": action, "new_status": new_status}

def api_stats(conn):
    total = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM agents WHERE status='active'").fetchone()[0]
    by_framework = {r[0]: r[1] for r in conn.execute("SELECT framework, COUNT(*) FROM agents GROUP BY framework")}
    by_type = {r[0]: r[1] for r in conn.execute("SELECT agent_type, COUNT(*) FROM agents GROUP BY agent_type")}
    total_installs = conn.execute("SELECT SUM(installs) FROM agents").fetchone()[0] or 0
    recent = conn.execute("SELECT action, agent_id, timestamp FROM activity_log ORDER BY id DESC LIMIT 20").fetchall()
    # Server uptime
    uptime_seconds = time.time() - SERVER_START_TIME if 'SERVER_START_TIME' in globals() else 0
    return {
        "total_agents": total, "active": active,
        "inactive": conn.execute("SELECT COUNT(*) FROM agents WHERE status='inactive'").fetchone()[0],
        "archived": conn.execute("SELECT COUNT(*) FROM agents WHERE status='archived'").fetchone()[0],
        "by_framework": by_framework, "by_type": by_type,
        "total_installs": total_installs,
        "uptime_seconds": round(uptime_seconds),
        "recent_activity": [{"action": r[0], "agent_id": r[1], "time": r[2]} for r in recent]
    }

# ============================================================
# HTTP Server
# ============================================================
SERVER_START_TIME = time.time()
METRICS = {"requests_total": 0, "requests_by_endpoint": {}, "errors_total": 0}

class AMAHandler(BaseHTTPRequestHandler):
    db_conn = None
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass  # Use our logger instead

    def _log_request(self, status_code, response_ms=0):
        METRICS["requests_total"] += 1
        ep = self.path.split("?")[0]
        METRICS["requests_by_endpoint"][ep] = METRICS["requests_by_endpoint"].get(ep, 0) + 1
        if status_code >= 400:
            METRICS["errors_total"] += 1

    def _client_ip(self):
        return self.client_address[0] if self.client_address else "unknown"

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode('utf-8')
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)
        self._log_request(status)

    def serve_static(self, filepath, cache_max_age=3600):
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".png": "image/png", ".svg": "image/svg+xml",
            ".ico": "image/x-icon", ".woff2": "font/woff2",
        }
        ext = os.path.splitext(filepath)[1].lower()
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_types.get(ext, "application/octet-stream"))
            self.send_header("Content-Length", len(content))
            self.send_header("Cache-Control", f"public, max-age={cache_max_age}")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
            self._log_request(200)
        except FileNotFoundError:
            self.send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        start = time.time()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        try:
            # Static routes
            if path == "/" or path == "/store":
                return self.serve_static(os.path.join(PUBLIC_DIR, "store.html"))
            if path == "/calculator":
                return self.serve_static(os.path.join(PUBLIC_DIR, "index.html"))
            if path == "/health" or path == "/api/health":
                return self.send_json({
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "uptime_seconds": round(time.time() - SERVER_START_TIME),
                    "metrics": {
                        "requests_total": METRICS["requests_total"],
                        "errors_total": METRICS["errors_total"]
                    }
                })

            # API routes
            if path == "/api/agents":
                return self.send_json(api_list_agents(params, self.db_conn))
            if path == "/api/stats":
                return self.send_json(api_stats(self.db_conn))
            if path.startswith("/api/agents/"):
                agent_id = path.split("/")[-1]
                agent = api_get_agent(agent_id, self.db_conn)
                if agent: return self.send_json(agent)
                return self.send_json({"error": "Agent not found"}, 404)

            # 404
            return self.send_json({"error": "Not found"}, 404)
        except Exception as e:
            logger.error(f"GET {path}: {e}")
            return self.send_json({"error": "Internal server error"}, 500)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        ip = self._client_ip()

        try:
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len) if content_len else b"{}"
            try: data = json.loads(body)
            except: data = {}

            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[0] == "api" and parts[1] == "agents":
                return self.send_json(api_agent_action(parts[2], parts[3], self.db_conn, ip))
            return self.send_json({"error": "Not found"}, 404)
        except Exception as e:
            logger.error(f"POST {path}: {e}")
            return self.send_json({"error": "Internal server error"}, 500)

# ============================================================
# Daemon Management
# ============================================================
def write_pid():
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

def read_pid():
    try:
        with open(PID_FILE, 'r') as f:
            return int(f.read().strip())
    except:
        return None

def remove_pid():
    try: os.remove(PID_FILE)
    except: pass

def is_running():
    pid = read_pid()
    if pid is None: return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        remove_pid()
        return False

def stop_daemon():
    pid = read_pid()
    if pid is None:
        print("No PID file found — server is not running")
        return False
    try:
        if sys.platform == 'win32':
            os.kill(pid, signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM to PID {pid}")
        time.sleep(1)
        if is_running():
            os.kill(pid, signal.SIGKILL)
            print("Force killed after timeout")
        remove_pid()
        return True
    except (OSError, ProcessLookupError):
        print("Process not found — cleaning up PID file")
        remove_pid()
        return False

# ============================================================
# Main
# ============================================================
def run_server():
    global SERVER_START_TIME
    SERVER_START_TIME = time.time()

    # Init DB
    conn = init_db()
    logger.info(f"Database: {DB_PATH}")

    # Seed from inventory
    seeded = seed_from_inventory(conn)
    if seeded:
        logger.info(f"Seeded {seeded} new agents from inventory")

    total = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM agents WHERE status='active'").fetchone()[0]
    logger.info(f"Catalog: {total} agents ({active} active)")

    # Inject DB into handler
    AMAHandler.db_conn = conn

    # Start server
    server = HTTPServer((HOST, PORT), AMAHandler)
    server.socket.setsockopt(6, 1, 1)  # TCP_NODELAY

    logger.info(f"AMA Store: http://localhost:{PORT}/store")
    logger.info(f"Calculator: http://localhost:{PORT}/calculator")
    logger.info(f"API:       http://localhost:{PORT}/api/agents")
    logger.info(f"Health:    http://localhost:{PORT}/health")
    logger.info(f"PID: {os.getpid()}")

    write_pid()

    def shutdown_handler(signum, frame):
        logger.info("Shutting down...")
        server.shutdown()
        conn.close()
        remove_pid()
        logger.info("Server stopped")
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        shutdown_handler(None, None)

def main():
    global PORT
    parser = argparse.ArgumentParser(description="AMA Production Server")
    parser.add_argument("--daemon", action="store_true", help="Run as background daemon")
    parser.add_argument("--stop", action="store_true", help="Stop running daemon")
    parser.add_argument("--status", action="store_true", help="Check daemon status")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port (default: {PORT})")
    args = parser.parse_args()

    PORT = args.port

    if args.stop:
        stop_daemon()
        return

    if args.status:
        if is_running():
            pid = read_pid()
            uptime = "unknown"
            try:
                # Try to get health info
                import urllib.request
                resp = urllib.request.urlopen(f"http://localhost:{PORT}/health", timeout=3)
                health = json.loads(resp.read())
                uptime = f"{health.get('uptime_seconds', 0)}s"
            except: pass
            print(f"Server is RUNNING (PID: {pid}, Uptime: {uptime}, Port: {PORT})")
        else:
            print("Server is STOPPED")
        return

    if args.daemon:
        if is_running():
            print(f"Server is already running (PID: {read_pid()})")
            return
        if sys.platform == 'win32':
            # Windows daemon: use pythonw to detach
            import subprocess
            script = os.path.abspath(__file__)
            subprocess.Popen(
                [sys.executable.replace('python.exe', 'pythonw.exe'), script, '--port', str(PORT)],
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            print(f"AMA Server started in background on port {PORT}")
            time.sleep(2)
            if is_running():
                print(f"  PID: {read_pid()}")
                print(f"  Store: http://localhost:{PORT}/store")
            else:
                print("  Warning: Server may not have started correctly. Check logs/")
        else:
            # Unix daemon
            pid = os.fork()
            if pid > 0:
                print(f"AMA Server started in background (PID: {pid}) on port {PORT}")
                return
            os.setsid()
            run_server()
    else:
        print("=" * 55)
        print("  AMA Agent Store — Production Server")
        print("=" * 55)
        run_server()

if __name__ == "__main__":
    main()
