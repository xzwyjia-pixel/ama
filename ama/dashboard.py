"""AMA Web Dashboard — real-time system monitoring and revenue tracking.

Lightweight HTTP server with single-page dashboard.
No external frontend dependencies — pure HTML/CSS/JS inline.

Usage:
    python -m ama.main --dashboard        # Start on http://localhost:8080
    python -m ama.main --dashboard --port 9000
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AMA 中控台</title>
<style>
:root {
  --bg: #0f1117; --card: #1a1d27; --border: #2a2d3a;
  --text: #e1e4e8; --muted: #8b949e; --green: #3fb950;
  --red: #f85149; --blue: #58a6ff; --yellow: #d29922;
  --purple: #a371f7;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: var(--bg); color: var(--text); line-height: 1.5; }
.header { background: var(--card); border-bottom: 1px solid var(--border);
          padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; }
.header h1 { font-size: 20px; font-weight: 600; }
.status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
              background: var(--green); margin-right: 8px; }
.container { max-width: 1200px; margin: 0 auto; padding: 24px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 16px; margin-bottom: 24px; }
.card { background: var(--card); border: 1px solid var(--border);
        border-radius: 8px; padding: 16px; }
.card h3 { font-size: 13px; color: var(--muted); text-transform: uppercase;
           letter-spacing: 0.5px; margin-bottom: 8px; }
.card .value { font-size: 28px; font-weight: 700; }
.card .sub { font-size: 12px; color: var(--muted); margin-top: 4px; }
.green { color: var(--green); } .red { color: var(--red); }
.blue { color: var(--blue); } .yellow { color: var(--yellow); }
.purple { color: var(--purple); }
table { width: 100%; border-collapse: collapse; margin-top: 12px; }
th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border);
         font-size: 13px; }
th { color: var(--muted); font-weight: 500; }
tr:hover { background: rgba(255,255,255,0.03); }
.tag { display: inline-block; padding: 2px 8px; border-radius: 12px;
       font-size: 11px; font-weight: 500; }
.tag-success { background: rgba(63,185,80,0.15); color: var(--green); }
.tag-fail { background: rgba(248,81,73,0.15); color: var(--red); }
.bar-container { background: var(--border); border-radius: 4px;
                 height: 8px; margin-top: 8px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 4px; transition: width 0.3s ease; }
.bar-green { background: var(--green); } .bar-yellow { background: var(--yellow); }
.bar-red { background: var(--red); }
.chart-row { display: flex; gap: 12px; align-items: center; margin-top: 8px; }
.chart-label { font-size: 12px; color: var(--muted); min-width: 60px; }
.chart-bar { flex: 1; }
.refresh { font-size: 12px; color: var(--muted); }
.worker-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
.worker-card { background: var(--card); border: 1px solid var(--border);
               border-radius: 6px; padding: 12px; text-align: center; }
.worker-card .name { font-weight: 600; font-size: 14px; }
.worker-card .tasks { font-size: 24px; font-weight: 700; margin: 4px 0; }
.worker-card .cost { font-size: 12px; color: var(--muted); }
</style>
</head>
<body>
<div class="header">
  <div>
    <span class="status-dot" id="status-dot"></span>
    <h1 style="display:inline">AMA 业务中控台</h1>
  </div>
  <span class="refresh">Auto-refresh: 10s | <span id="clock">--</span></span>
</div>
<div class="container">
  <!-- Metrics Row -->
  <div class="grid" id="metrics"></div>

  <!-- Workers + Budget -->
  <div class="grid">
    <div class="card">
      <h3>Workers</h3>
      <div class="worker-grid" id="workers"></div>
    </div>
    <div class="card">
      <h3>今日预算</h3>
      <div id="budget"></div>
    </div>
  </div>

  <!-- Recent Tasks -->
  <div class="card" style="margin-bottom:24px">
    <h3>最近任务</h3>
    <table><thead><tr>
      <th>时间</th><th>任务ID</th><th>类型</th><th>模型</th><th>花费</th><th>状态</th>
    </tr></thead><tbody id="recent-tasks"></tbody></table>
  </div>

  <!-- Revenue Estimate -->
  <div class="card">
    <h3>预估收益 (基于当前产品定价)</h3>
    <div id="revenue"></div>
  </div>
</div>

<script>
const API = '/api/status';

async function refresh() {
  try {
    const resp = await fetch(API);
    const data = await resp.json();
    render(data);
  } catch(e) {
    console.error('API error:', e);
  }
}

function render(data) {
  const s = data.system || {};
  const b = s.budget || {};
  const r = data.router || {};
  const workers = data.workers || [];
  const tasks = data.recent_tasks || [];
  const revenue = data.revenue_estimate || {};

  // Metrics
  document.getElementById('metrics').innerHTML = `
    <div class="card">
      <h3>今日任务</h3>
      <div class="value blue">${s.queue?.total || 0}</div>
      <div class="sub">待处理: ${s.queue?.pending || 0}</div>
    </div>
    <div class="card">
      <h3>总花费</h3>
      <div class="value ${b.percent > 80 ? 'red' : b.percent > 50 ? 'yellow' : 'green'}">CNY ${b.spent?.toFixed(4) || '0.00'}</div>
      <div class="sub">预算: CNY ${b.daily?.toFixed(2) || '50.00'}</div>
    </div>
    <div class="card">
      <h3>模型路由</h3>
      <div class="value purple">${r.total_routes || 0}</div>
      <div class="sub">降级: ${r.fallbacks || 0}次</div>
    </div>
    <div class="card">
      <h3>活跃Worker</h3>
      <div class="value green">${workers.length}</div>
      <div class="sub">${workers.map(w => w.name).join(', ') || '无'}</div>
    </div>
  `;

  // Budget bar
  const pct = b.percent || 0;
  document.getElementById('budget').innerHTML = `
    <div class="value ${pct > 80 ? 'red' : pct > 50 ? 'yellow' : 'green'}">${pct.toFixed(1)}%</div>
    <div class="sub">CNY ${b.spent?.toFixed(4) || '0'} / CNY ${b.daily?.toFixed(2) || '50'} 剩余: CNY ${b.remaining?.toFixed(2) || '50'}</div>
    <div class="bar-container"><div class="bar-fill ${pct > 80 ? 'bar-red' : pct > 50 ? 'bar-yellow' : 'bar-green'}" style="width:${Math.min(pct, 100)}%"></div></div>
    ${b.alert ? '<div class="sub red" style="margin-top:4px">[!] 预算警报已触发</div>' : ''}
  `;

  // Workers
  document.getElementById('workers').innerHTML = workers.map(w => `
    <div class="worker-card">
      <div class="name">${w.name}</div>
      <div class="tasks blue">${w.tasks || 0}</div>
      <div class="cost">CNY ${w.cost?.toFixed(4) || '0.00'}</div>
    </div>
  `).join('');

  // Recent tasks
  document.getElementById('recent-tasks').innerHTML = tasks.slice(0, 15).map(t => `
    <tr>
      <td>${t.timestamp?.slice(11,19) || '--'}</td>
      <td>${(t.task_id || '').slice(0, 12)}...</td>
      <td>${t.worker_type || '--'}</td>
      <td>${(t.model || '').split('/').pop() || '--'}</td>
      <td>CNY ${t.cost_yuan?.toFixed(6) || '0'}</td>
      <td><span class="tag ${t.success ? 'tag-success' : 'tag-fail'}">${t.success ? 'OK' : 'FAIL'}</span></td>
    </tr>
  `).join('') || '<tr><td colspan="6" style="color:var(--muted)">暂无任务记录</td></tr>';

  // Revenue estimate
  document.getElementById('revenue').innerHTML = `
    <div class="chart-row">
      <div class="chart-label">AI Tool Suite (¥99)</div>
      <div class="chart-bar">
        <div class="bar-container"><div class="bar-fill bar-green" style="width:${Math.min((revenue.suite_sold || 0) * 10, 100)}%"></div></div>
      </div>
      <span>${revenue.suite_sold || 0} 已售</span>
    </div>
    <div class="chart-row">
      <div class="chart-label">AI Roundtable (¥49)</div>
      <div class="chart-bar">
        <div class="bar-container"><div class="bar-fill bar-blue" style="width:${Math.min((revenue.roundtable_sold || 0) * 10, 100)}%"></div></div>
      </div>
      <span>${revenue.roundtable_sold || 0} 已售</span>
    </div>
    <div class="chart-row">
      <div class="chart-label">审核规则库 (¥29)</div>
      <div class="chart-bar">
        <div class="bar-container"><div class="bar-fill bar-purple" style="width:${Math.min((revenue.rules_sold || 0) * 10, 100)}%"></div></div>
      </div>
      <span>${revenue.rules_sold || 0} 已售</span>
    </div>
    <div style="margin-top:16px; padding-top:12px; border-top:1px solid var(--border)">
      <div class="value green">CNY ${(revenue.total || 0).toFixed(2)}</div>
      <div class="sub">预估总收入 | ROI: ${revenue.roi || '0'}x</div>
    </div>
  `;
}

document.getElementById('clock').textContent = new Date().toLocaleTimeString('zh-CN');
setInterval(() => {
  document.getElementById('clock').textContent = new Date().toLocaleTimeString('zh-CN');
}, 1000);
refresh();
setInterval(refresh, 10000);
</script>
</body>
</html>"""


def build_api_data(manager) -> dict:
    """Build the API response from the ManagerAgent state."""
    try:
        sys_status = manager.system_status()
    except Exception:
        sys_status = {"queue": {}, "budget": {}, "running": False}

    try:
        report = manager.daily_report()
    except Exception:
        report = type("R", (), {"total_tasks": 0, "total_cost_yuan": 0.0, "by_worker": {}})

    try:
        recent = manager.recent_activity(15)
    except Exception:
        recent = []

    try:
        router_stats = manager.model_router.stats
    except Exception:
        router_stats = type("R", (), {"total_routes": 0, "fallback_triggered": 0, "by_model": {}})

    # Worker stats
    workers_data = []
    if manager.registry:
        for w in manager.registry.list_workers():
            try:
                workers_data.append({
                    "name": w.worker_type,
                    "tasks": w.stats.get("total_tasks", 0),
                    "cost": w.stats.get("total_cost_yuan", 0.0),
                })
            except Exception:
                workers_data.append({"name": w.worker_type, "tasks": 0, "cost": 0.0})

    return {
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": 0,  # To be set by server
        "system": {
            "running": sys_status.get("running", False),
            "queue": sys_status.get("queue", {}),
            "budget": sys_status.get("budget", {}),
        },
        "router": {
            "total_routes": router_stats.total_routes,
            "fallbacks": router_stats.fallback_triggered,
            "by_model": router_stats.by_model,
        },
        "workers": workers_data,
        "recent_tasks": recent,
        "revenue_estimate": {
            "suite_sold": 0,
            "roundtable_sold": 0,
            "rules_sold": 0,
            "total": 0,
            "roi": "0.0",
        },
    }


def start_dashboard(manager, host: str = "127.0.0.1", port: int = 8080):
    """Start the web dashboard in a background thread.

    Usage:
        start_dashboard(manager)
        # Dashboard available at http://localhost:8080
    """
    import threading

    class DashboardHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Suppress access logs

        def do_GET(self):
            if self.path == "/" or self.path == "/index.html":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
            elif self.path == "/api/status":
                data = build_api_data(manager)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not Found")

    server = HTTPServer((host, port), DashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    logger.info("Dashboard started at http://%s:%d", host, port)
    print(f"\n  AMA Dashboard: http://{host}:{port}\n")

    return server
