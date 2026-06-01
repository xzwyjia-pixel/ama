# Agent Management Agent (AMA) — 架构设计 v1.0

> **定位**: 元代理 (Meta-Agent) — 管理所有 agent 的 agent
> **原则**: 减法本能 (删>加), 杠杆优先 (20%→80%), 自愈闭环 (卡死自kill)
> **设计日期**: 2026-06-01

---

## 0. 现状盘点

### 0.1 Agent 资产清单

```
电脑内 Agent 总数: 280+

┌──────────────────────────────────────────────────────────────┐
│ 框架层 (3个)                                                  │
│   Pi Coding Agent v0.77      ~/.pi/agent/     FSM + 9子代理   │
│   Claude Code (Anthropic)    ~/.claude/       130+ 技能       │
│   Codex CLI (OpenAI)         ~/.codex/        37 技能         │
├──────────────────────────────────────────────────────────────┤
│ 子代理层 (9个)                                                │
│   code-explorer   doc-writer    test-writer                   │
│   security-auditor  refactorer   lite-reviewer                │
│   thermo-nuclear-code-quality  thermo-nuclear-review          │
├──────────────────────────────────────────────────────────────┤
│ 技能层 (268个)                                                │
│   活跃技能: 130+   归档技能: 141    Codex 技能: 37              │
├──────────────────────────────────────────────────────────────┤
│ 角色层 (6个)                                                  │
│   precise quick teacher architect minimalist debugger         │
├──────────────────────────────────────────────────────────────┤
│ 工具层                                                        │
│   MCP 服务器: 8    Hooks: 3    Workspaces: 3                  │
│   Scripts: 12      Prompts: 5   Themes: 4                     │
├──────────────────────────────────────────────────────────────┤
│ 外部连接                                                      │
│   飞书 抖音 豆包 Marvis Obsidian                               │
└──────────────────────────────────────────────────────────────┘
```

### 0.2 核心痛点

1. **无统一注册表** — 3个框架各自管理, 技能分散在 5+ 个目录
2. **无健康监控** — agent 挂了不知道, 技能过期不清理
3. **无智能路由** — 用户手动选择 agent/技能, 无自动匹配
4. **无生命周期** — 安装/启用/禁用/归档/删除全靠手工
5. **无配置管理** — 3个框架的 settings 各自为政, 互相冲突
6. **无协同机制** — 多 agent 并行无协调, 资源抢占
7. **无审计追踪** — 哪个 agent 做了什么, 无统一日志

---

## 1. 总体架构 (7层)

```
                          ┌──────────────────────┐
                          │   用户 / 上层系统      │
                          └──────────┬───────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────┐
│                            AMA 元代理                                   │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │ L7 可观测性  │  │ L6 安全治理  │  │ L5 协同编排  │  │ L4 配置管理  │   │
│  │ 仪表板/日志  │  │ 权限/审计    │  │ 并行/依赖    │  │ 集中/继承    │   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │
│         │                │                │                │           │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐   │
│  │ L3 生命周期  │  │ L2 智能路由  │  │ L1 健康监控  │  │ L0 资产发现  │   │
│  │ 安装/启停    │  │ 意图→Agent  │  │ 心跳/指标    │  │ 扫描/注册    │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              ▼                      ▼                      ▼
       ┌──────────┐          ┌──────────┐          ┌──────────┐
       │ Pi Agent │          │Claude Code│         │ Codex CLI │
       └──────────┘          └──────────┘          └──────────┘
```

---

## 2. 逐层设计

### L0 — 资产发现与注册 (Agent Inventory)

**职责**: 自动扫描、注册、索引所有 agent 资产

```
扫描器 (Scanner)
├── Pi Agent 扫描器    → ~/.pi/agent/agents/*.md
├── Claude Code 扫描器  → ~/.claude/skills/*/SKILL.md
│                       → ~/.claude/skills-archived/*/SKILL.md
├── Codex 扫描器        → ~/.codex/skills/*/
├── MCP 扫描器          → mcp.json, settings.json 中的 MCP 配置
├── Hook 扫描器         → ~/.claude/hooks/*.py
└── 外部工具扫描器       → d:/agent-tools/, agent-browser/
```

**注册表 Schema** (SQLite ~/.pi/agent/ama-registry.db):

```sql
-- 核心 agent 表
CREATE TABLE agents (
    id          TEXT PRIMARY KEY,        -- uuid
    name        TEXT NOT NULL,           -- 唯一名称
    framework   TEXT NOT NULL,           -- 'pi' | 'claude' | 'codex' | 'mcp' | 'external'
    type        TEXT NOT NULL,           -- 'skill' | 'subagent' | 'persona' | 'mcp_server' | 'hook' | 'script'
    status      TEXT DEFAULT 'active',   -- 'active' | 'inactive' | 'archived' | 'error'
    version     TEXT,
    source_path TEXT NOT NULL,           -- 文件系统路径
    discovered_at TEXT,                  -- 首次发现时间
    last_seen_at TEXT,                   -- 最后扫描时间
    hash        TEXT,                    -- 内容 hash (检测变更)
    metadata    JSON                     -- {trigger_keywords, tools, model, thinking_level, ...}
);

-- 依赖关系表
CREATE TABLE agent_dependencies (
    agent_id    TEXT REFERENCES agents(id),
    depends_on  TEXT REFERENCES agents(id),
    dep_type    TEXT  -- 'requires' | 'optional' | 'conflicts'
);

-- 使用统计表
CREATE TABLE agent_usage (
    agent_id    TEXT REFERENCES agents(id),
    invoked_at  TEXT,
    task_desc   TEXT,
    success     BOOLEAN,
    duration_ms INTEGER,
    tokens_used INTEGER,
    error_msg   TEXT
);
```

**实现文件**: `~/.pi/agent/extensions/ama-scanner.ts`

---

### L1 — 健康监控 (Health & Monitoring)

**职责**: 心跳检测、性能指标、异常告警

```
健康检查维度:
├── 可用性 (Availability)
│   ├── Agent 文件是否存在
│   ├── MCP 服务器是否可达 (TCP ping)
│   ├── API Key 是否有效
│   └── 依赖是否满足
│
├── 性能 (Performance)
│   ├── 平均响应时间
│   ├── Token 消耗/会话
│   ├── 成功率
│   └── 缓存命中率 (DeepSeek prefix cache)
│
├── 安全 (Security)
│   ├── 过期 API Key
│   ├── 权限越界检测
│   ├── 已知漏洞 (CVE)
│   └── 敏感信息泄露扫描
│
└── 新鲜度 (Freshness)
    ├── 最后使用时间
    ├── 版本是否过期
    └── 归档候选 (>90天未使用)
```

**断路器模式** (参考现有 `notifications.json`):

```json
{
  "agent_id": "security-auditor",
  "circuit_breaker": {
    "failure_threshold": 3,
    "timeout_ms": 30000,
    "state": "closed",
    "consecutive_failures": 0,
    "last_failure_at": null
  }
}
```

**健康检查命令**:
- `ama health` — 全量健康扫描
- `ama health <agent-name>` — 单 agent 检查
- `ama watch` — 持续监控模式

**实现文件**: `~/.pi/agent/scripts/ama-health-check.sh`

---

### L2 — 智能路由 (Smart Router)

**职责**: 意图识别 → Agent 匹配 → 最优调度

```
用户输入
  │
  ▼
┌─────────────────┐
│ 意图分类器       │  ← 基于 trigger keywords + LLM 语义匹配
│ (Intent Parser)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 候选排序器       │  ← score = pri × 匹配度 × 健康状态 × 历史成功率
│ (Ranker)         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 调度决策         │
│ (Dispatcher)     │
│                  │
│  • 单 agent 直派  │
│  • 多 agent 并行  │
│  • 多 agent 串行  │
│  • 降级 fallback  │
└────────┬────────┘
         │
         ▼
    执行 & 反馈 → 更新 agent_usage 表
```

**路由规则引擎** (扩展现有 `skills-registry.json`):

```json
{
  "route_id": "r_001",
  "intent": "code_review",
  "primary": {
    "agent": "code-review",
    "framework": "claude",
    "threshold": 0.8
  },
  "fallback": [
    {"agent": "thermo-nuclear-review-subagent", "framework": "pi"},
    {"agent": "lite-reviewer", "framework": "pi", "model": "qwen2.5:14b"}
  ],
  "parallel_optional": ["security-auditor"],
  "cooldown_ms": 5000
}
```

**与现有关键区别**:
- 现有 `skills-registry.json` 是静态的 keyword→skill 映射
- AMA Router 增加: 健康状态加权、历史成功率、动态 fallback、并行调度

**实现文件**: `~/.pi/agent/extensions/ama-router.ts`

---

### L3 — 生命周期管理 (Lifecycle)

**职责**: Agent 的 CRUD + 状态机

```
Agent 状态机:
                    ┌─────────┐
          install → │  active  │
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ┌────────┐ ┌────────┐ ┌────────┐
         │paused  │ │ error  │ │ update │
         └───┬────┘ └───┬────┘ └───┬────┘
             │          │          │
             ▼          ▼          ▼
         ┌────────┐ ┌────────┐ ┌────────┐
         │active  │ │active  │ │active  │
         └────────┘ └────────┘ └────────┘
                         │
                    ┌────┴─────┐
                    ▼          ▼
              ┌─────────┐ ┌──────────┐
              │ archive │ │  delete  │
              └─────────┘ └──────────┘
```

**操作命令**:
```
ama install <source-path>     # 注册新 agent
ama enable  <agent-name>      # 激活
ama disable <agent-name>      # 暂停
ama update  <agent-name>      # 更新版本
ama archive <agent-name>      # 归档 (>90天未用自动候选)
ama delete  <agent-name>      # 删除 (需确认)
ama list    [--status=active|archived|error] [--framework=pi|claude|codex]
```

**归档规则**:
- 连续两次季度审视未触发 → 归档候选
- 归档前 30 天告警 → 未恢复则自动归档
- 归档保留 180 天 → 超期提示删除

**实现文件**: `~/.pi/agent/extensions/ama-lifecycle.ts`

---

### L4 — 配置管理 (Config Manager)

**职责**: 3 个框架的统一配置层, 消除冲突

```
配置继承链:
                    ┌──────────────────┐
                    │  AMA 全局配置      │  ← 全局默认 (model, provider, safety)
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       ┌──────────┐  ┌──────────┐  ┌──────────┐
       │ Pi 配置   │  │Claude配置 │  │ Codex配置 │  ← 框架级覆盖
       └─────┬────┘  └─────┬────┘  └─────┬────┘
             │              │              │
             ▼              ▼              ▼
       ┌──────────┐  ┌──────────┐  ┌──────────┐
       │Agent 配置 │  │Skill 配置 │  │Skill 配置 │  ← Agent 级覆盖
       └──────────┘  └──────────┘  └──────────┘
```

**冲突检测规则**:
```
- 同一 API Key 用于不同 provider → 告警
- 同一端口被多个 MCP 占用 → 告警
- 同一路径被不同 agent 声明写入 → 告警
- 安全规则冲突 (一个允许, 一个禁止) → 取最严格
```

**统一配置格式** (`ama-config.yaml`):

```yaml
# 全局默认
defaults:
  provider: deepseek
  model: deepseek-v4-pro
  max_thinking_tokens: 8000
  safety_level: strict

# 框架覆盖
frameworks:
  pi:
    config_path: ~/.pi/agent/settings.json
    model_override: null  # 使用全局
  claude:
    config_path: ~/.claude/settings.json
    model_override: opus  # Claude 专用
  codex:
    config_path: ~/.codex/config.toml
    model_override: deepseek-v4-pro

# Agent 级权限边界
agents:
  security-auditor:
    allow_paths: ["src/", "config/"]
    deny_paths: ["~/.ssh/", "/etc/"]
    allow_tools: [read, grep, glob]
    deny_tools: [write, edit, bash_write]
    rate_limit: {max_invocations_per_hour: 20}

# 环境变量 (敏感信息不存明文, 引用系统 keychain)
secrets:
  DEEPSEEK_API_KEY: "${KEYCHAIN:deepseek}"
  ANTHROPIC_API_KEY: "${KEYCHAIN:anthropic}"
```

**实现文件**: `~/.pi/agent/extensions/ama-config.ts`

---

### L5 — 协同编排 (Orchestration)

**职责**: 多 Agent 并行/串行调度, 依赖解析

```
编排模式:
┌─────────────────────────────────────────────┐
│ 1. 并行扇出 (Fan-out)                        │
│    适用: 独立任务, 无共享状态                   │
│    agent A ──┐                               │
│    agent B ──┼── parallel ──→ merge results  │
│    agent C ──┘                               │
├─────────────────────────────────────────────┤
│ 2. 串行管道 (Pipeline)                        │
│    适用: 有依赖关系的任务                       │
│    agent A ──→ agent B ──→ agent C           │
│    (设计)      (实现)      (审查)              │
├─────────────────────────────────────────────┤
│ 3. DAG 有向无环图                             │
│    适用: 复杂依赖                              │
│    A ──→ B ──→ D                             │
│    └──→ C ──→ D                              │
├─────────────────────────────────────────────┤
│ 4. 竞争/投票 (Competitive)                     │
│    适用: 需要多方验证的场景                      │
│    agent A ──┐                               │
│    agent B ──┼── 各自独立 ──→ 投票/择优        │
│    agent C ──┘                               │
└─────────────────────────────────────────────┘
```

**编排 DSL** (声明式, 类似现有 Workflow 脚本):

```yaml
# ama-orchestrate.yaml
workflow: security_audit_and_fix
description: "全量安全审计 + 自动修复 + 验证"

phases:
  - name: scan
    parallel:
      - agent: security-auditor
        scope: "src/"
        schema: VULN_SCHEMA
      - agent: secrets-scan
        scope: "."
        schema: SECRET_SCHEMA
      - agent: dep-auditor
        scope: "package.json"
        schema: DEP_SCHEMA

  - name: triage
    pipeline:
      - deduplicate: {by: [file, line]}
      - prioritize: {by: severity}
      - filter: {severity: [critical, high]}

  - name: fix
    parallel:
      for_each: "$triage.results"
      agent: code
      prompt: "Fix this vulnerability: $item.description"
      safety: {max_changes_per_agent: 5}

  - name: verify
    parallel:
      for_each: "$fix.results"
      agent: thermo-nuclear-review-subagent
      prompt: "Verify fix: $item.diff"
      schema: VERIFY_SCHEMA
```

**实现文件**: `~/.pi/agent/extensions/ama-orchestrator.ts`

---

### L6 — 安全治理 (Security & Governance)

**职责**: 权限边界、审计日志、合规检查

```
安全模型 (最小权限原则):

┌────────────────────────────────────────────┐
│                AMA 元代理                   │
│  权限: 管理所有 agent (最高权限)              │
│  限制: 不能修改自己的 damage-control 规则     │
├────────────────────────────────────────────┤
│              管理 Agent                     │
│  权限: 启停 agent, 修改路由规则               │
│  限制: 不能执行被管理 agent 的实际任务         │
├────────────────────────────────────────────┤
│              工作 Agent                     │
│  权限: 仅限声明所需的工具和路径               │
│  限制: 受 damage-control-rules.yaml 约束     │
└────────────────────────────────────────────┘
```

**审计日志格式**:

```json
{
  "event_id": "evt_20260601_001",
  "timestamp": "2026-06-01T20:30:00Z",
  "actor": "ama-orchestrator",
  "action": "agent.invoke",
  "target": "security-auditor",
  "parameters": {"scope": "src/", "depth": "full"},
  "result": "success",
  "duration_ms": 12340,
  "tokens": {"input": 5000, "output": 1200, "cache_hit": 3000},
  "permissions_checked": ["read:src/", "bash:rg"],
  "permissions_denied": []
}
```

**合规检查清单** (每次 agent 调用前):
- [ ] API Key 未过期
- [ ] 请求路径在 agent 允许范围内
- [ ] 请求工具在 agent 允许列表内
- [ ] 未触发 rate limit
- [ ] 断路器状态为 closed
- [ ] 依赖 agent 均可用

**实现文件**: `~/.pi/agent/extensions/ama-security.ts`

---

### L7 — 可观测性 (Observability)

**职责**: 指标采集、仪表板、事后分析

```
指标维度:
├── 系统级
│   ├── 活跃 agent 数
│   ├── 错误率 (按 agent/framework)
│   ├── 平均调度延迟
│   └── 资源占用 (磁盘/内存)
│
├── 业务级
│   ├── 任务完成率
│   ├── 用户满意度 (隐式: 无回退=满意)
│   ├── 最常用 agent Top 10
│   └── 最常失败 agent Top 10
│
└── 成本级
    ├── Token 消耗 (按 agent/会话)
    ├── API 调用费用估算
    ├── 缓存命中率
    └── 节省成本 (vs 无缓存)
```

**仪表板命令**:
```
ama dashboard          # 全量仪表板
ama stats [agent]      # 单 agent 统计
ama cost [--monthly]   # 成本分析
ama post-mortem <id>   # 故障事后分析
```

**实现文件**: `~/.pi/agent/extensions/ama-observability.ts`

---

## 3. 实现路线图

```
Phase 1 (Week 1-2): 最小可用 — L0 + L1
├── 实现 Scanner: 扫描所有 agent 目录, 生成注册表
├── 实现 Registry DB: SQLite schema + 基本 CRUD
├── 实现 Health Check: 文件存在性 + MCP 可达性
└── 交付: `ama list`, `ama health`

Phase 2 (Week 3-4): 路由 + 生命周期 — L2 + L3
├── 实现 Router: 意图→agent 匹配 (基于现有 skills-registry.json)
├── 实现 Lifecycle: install/enable/disable/archive/delete
└── 交付: `ama route "review my code"`, `ama archive old-skill`

Phase 3 (Week 5-6): 配置 + 安全 — L4 + L6
├── 实现 Config Manager: 统一配置层 + 冲突检测
├── 实现 Security: 权限边界检查 + 审计日志
└── 交付: `ama config validate`, `ama audit --last=24h`

Phase 4 (Week 7-8): 编排 + 可观测 — L5 + L7
├── 实现 Orchestrator: 并行/串行/DAG 编排
├── 实现 Dashboard: 指标聚合 + 可视化
└── 交付: `ama orchestrate security-audit.yaml`, `ama dashboard`

Phase 5 (Week 9-10): 打磨
├── 断路器自愈
├── 自动归档建议
├── 跨框架 fallback
└── 性能优化 (缓存、增量扫描)
```

---

## 4. 目录结构

```
~/.pi/agent/
├── extensions/
│   ├── ama-scanner.ts          # L0: 资产发现
│   ├── ama-health.ts           # L1: 健康监控
│   ├── ama-router.ts           # L2: 智能路由
│   ├── ama-lifecycle.ts        # L3: 生命周期
│   ├── ama-config.ts           # L4: 配置管理
│   ├── ama-orchestrator.ts     # L5: 协同编排
│   ├── ama-security.ts         # L6: 安全治理
│   └── ama-observability.ts    # L7: 可观测性
├── scripts/
│   ├── ama-health-check.sh     # 健康检查脚本
│   ├── ama-scan.sh             # 资产扫描脚本
│   └── ama-cleanup.sh          # 归档清理脚本
├── ama-registry.db             # SQLite 注册表
├── ama-config.yaml             # 统一配置
└── ama-orchestrate.yaml        # 编排定义
```

---

## 5. 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 存储 | SQLite | 零依赖, 单文件, 够用 |
| 配置格式 | YAML | 可读性 > JSON, 现有 damage-control 已是 YAML |
| 扩展语言 | TypeScript (.ts) | 与现有 ecosystem-manager.ts 一致 |
| 通信方式 | 文件系统 + 命令行 | 无网络依赖, 符合 Pi Agent 设计哲学 |
| 安全模型 | 继承现有 damage-control-rules.yaml | 不重复造轮子, 扩展而非替代 |
| 路由算法 | 加权匹配 (pri × 匹配度 × 健康) | 简单可解释, 不需要 ML |
| 编排引擎 | 声明式 YAML → TS 执行 | 与 Workflow DSL 对齐 |

---

## 6. 风险与缓解

| 风险 | 概率 | 缓解 |
|------|------|------|
| 扫描器遗漏 agent | 中 | 多路径扫描 + 手动注册入口 |
| 3 框架 API 不兼容 | 高 | 适配器模式, 每框架独立 driver |
| 配置冲突难以自动解决 | 中 | 检测→告警→人工裁决, 不自动修改 |
| 元代理自身故障 | 低 | AMA 自身也注册到注册表, 有 health check |
| Token 消耗增加 | 中 | 增量扫描 + 缓存, 每次扫描 < 500 tokens |
