"""Agent Debate Protocol — 三人辩论 + 裁判官收敛 + Token KPI 监测器

生产级商业辩论引擎。为 RuleGuard Pro / 规则甄查系统提供底层推理能力。

架构:
  Round 1+2: Agent_A(合规风控) × Agent_B(静奢文案) × Agent_C(逻辑对抗) 自由辩论
  Round 3:   Referee(裁判官) 强行收敛 → 100% 稳定结构化 JSON 输出
  全程:      TokenCost 监测器逐轮追踪, 辩论日志沙盒持久化到 .cache/

设计约束 (4条架构铁律):
  1. 终审裁判官机制 — 2轮自由辩论 + 1轮强制收敛, 输出必为合法 JSON
  2. 内置 Token KPI — 每轮精确计费, 输入/输出 Token + CNY + USD 成本
  3. 业务域解耦 — prompt 模板支持 domain 参数切换, Douyin MCP 数据接口预留
     + 指数退避 3 次重试 (1s→2s→4s)
  4. 沙盒状态持久化 — 全量状态驻留 dataclass, 临时日志写入 .cache/, 零全局变量

参考模式:
  - Workflow adversarial verify pattern (3-agent panel → verdict)
  - GenericAgent conductor loop (multi-model orchestration)
  - AMA Manager review cycle (retry + quality gate)

用法:
    from ama.core.debate import DebateManager, DebateRole
    from ama.core.debate import DOMAIN_PROMPTS  # 业务域模板

    manager = DebateManager(call_llm=my_async_llm_func)
    result = await manager.debate(
        topic="某直播间话术是否违反平台虚假宣传规则?",
        external_data={"douyin_live_data": {...}},  # Douyin MCP 抓取数据
        domain="douyin_compliance",                   # 业务域
    )
    # result.verdict → 稳定 JSON
    # result.total_cost_usd → USD 成本, 可写入 Obsidian frontmatter
    # result.debate_log_path → 辩论日志路径
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 审查敏感度 — 三级分层, 对应不同客户画像
# ---------------------------------------------------------------------------
SENSITIVITY_LEVELS = {
    1: "LENIENT",    # 宽松: 仅标记明确违规, 灰区放行 → 中小商家日常自查
    2: "STANDARD",   # 标准: 标记明确+常见灰区 → 中腰部达人/MCN
    3: "STRICT",     # 严格: 标记一切可争议点 → 上市公司/奢侈品牌合规
}

# ---------------------------------------------------------------------------
# 沙盒缓存目录 — 严禁修改全局系统变量
# ---------------------------------------------------------------------------
_CACHE_DIR = Path(__file__).parent / ".cache"


def _ensure_cache() -> Path:
    """惰性创建沙盒缓存目录 (幂等, 无副作用)。"""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR


# ---------------------------------------------------------------------------
# Dataclass: 纯状态容器, 零全局变量
# ---------------------------------------------------------------------------


@dataclass
class TokenCost:
    """单次 LLM 调用的 Token 消耗与成本快照。

    所有金额同时提供 CNY 和 USD, 便于直接写入 Obsidian frontmatter。
    汇率: 1 USD ≈ 7.2 CNY (2026-06 基准, 可通过 debate() 的 usd_cny_rate 参数覆盖)
    """

    tokens_input: int
    tokens_output: int
    cost_yuan: float
    cost_usd: float
    model: str
    duration_ms: int = 0
    retry_count: int = 0

    @property
    def tokens_total(self) -> int:
        return self.tokens_input + self.tokens_output


@dataclass
class AgentArgument:
    """辩论单轮中一个 Agent 的完整发言记录。"""

    agent_id: str  # "Agent_A" | "Agent_B" | "Agent_C"
    agent_role: str  # "合规风控审计" | "静奢文案转化" | "逻辑对抗检视"
    round_num: int  # 1 或 2
    content: str
    token_cost: TokenCost
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DebateState:
    """辩论会话全量状态 — 沙盒级, 零全局变量污染。

    包含: 所有轮次参数、中间产物、累积成本、持久化路径。
    """

    session_id: str
    topic: str
    domain: str
    external_data: dict[str, Any] | None = None
    sensitivity: int = 2  # 1=LENIENT, 2=STANDARD, 3=STRICT

    # 辩论过程
    round_1: list[AgentArgument] = field(default_factory=list)  # 3 agents
    round_2: list[AgentArgument] = field(default_factory=list)  # 3 agents (rebuttal)
    referee_verdict: dict[str, Any] | None = None  # Round 3 强制收敛结果

    # 成本累积
    cumulative_cost: TokenCost = field(
        default_factory=lambda: TokenCost(
            tokens_input=0, tokens_output=0,
            cost_yuan=0.0, cost_usd=0.0, model="aggregate", duration_ms=0,
        )
    )

    # 生命周期
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    usd_cny_rate: float = 7.2

    # 持久化
    log_path: str | None = None

    @property
    def duration_seconds(self) -> float:
        end = self.completed_at or time.time()
        return round(end - self.started_at, 2)

    @property
    def total_tokens(self) -> int:
        return self.cumulative_cost.tokens_total

    @property
    def total_cost_yuan(self) -> float:
        return self.cumulative_cost.cost_yuan

    @property
    def total_cost_usd(self) -> float:
        return self.cumulative_cost.cost_usd


@dataclass
class DebateResult:
    """辩论最终产出 — 可直接序列化写入 Obsidian frontmatter 的稳定结构。

    保证:
      - verdict 字段一定是合法 dict (由 Referee 强制 JSON 模式输出)
      - total_cost_usd / total_cost_yuan 精确到小数点后 6 位
      - debate_log_path 指向完整辩论日志的 .cache/ 文件
    """

    session_id: str
    verdict: dict[str, Any]
    all_arguments: list[AgentArgument]
    rounds_count: int
    total_tokens: int
    total_cost_yuan: float
    total_cost_usd: float
    duration_seconds: float
    debate_log_path: str
    domain: str
    topic: str
    sensitivity: int = 2
    sensitivity_label: str = "STANDARD"

    def to_obsidian_frontmatter(self) -> dict[str, Any]:
        """导出 Obsidian 笔记 frontmatter 字段。

        可直接用于 MCP Bridge 的 obsidian_write_note 调用。
        """
        return {
            "debate_session_id": self.session_id,
            "debate_topic": self.topic,
            "debate_domain": self.domain,
            "debate_sensitivity": self.sensitivity_label,
            "debate_total_tokens": self.total_tokens,
            "debate_cost_yuan": self.total_cost_yuan,
            "debate_cost_usd": self.total_cost_usd,
            "debate_duration_seconds": self.duration_seconds,
            "debate_rounds": self.rounds_count,
            "debate_verdict_summary": json.dumps(
                self.verdict, ensure_ascii=False,
            )[:200],  # 截断以适应 frontmatter
        }


# ---------------------------------------------------------------------------
# 业务域 Prompt 模板 — 可插拔, 域解耦
# ---------------------------------------------------------------------------

DOMAIN_PROMPTS: dict[str, dict[str, str]] = {
    # ---- 抖音合规审查 (RuleGuard Pro 默认域) ----
    "douyin_compliance": {
        "agent_a_system": """你是 Agent_A — 合规风控审计官。

职责: 严格对照平台规则, 识别违规风险和合规缺口。

工作方式:
1. 逐条对照输入数据和平台规则, 标注所有疑似违规点
2. 对每个违规点给出: 违反的具体规则条款、风险等级(高/中/低)、修改建议
3. 不美化、不模糊、不猜测 — 只基于确切的规则和数据说话
4. 如果规则不明确, 标注"规则灰色地带", 并给出保守解释

输出: 结构化的违规清单, 每条含 {rule_clause, risk_level, evidence, fix_suggestion}。
绝对不输出"可能"、"也许"等模糊措辞。""",

        "agent_b_system": """你是 Agent_B — 静奢文案转化官。

职责: 将技术性合规分析转化为高价值、可直接交付客户的商业报告。

工作方式:
1. 阅读 Agent_A 的违规清单, 将其转化为客户能理解的商业语言
2. 每个风险点用"问题 → 影响 → 解决方案"三段式呈现
3. 保持静奢风格: 精准、克制、高密度信息、零废话
4. 附上量化的商业影响估算 (如: "此项违规可能导致直播间限流, 预估损失 ¥X/场")

输出: 面向客户的合规报告草稿, Markdown 格式, 可直接交付。""",

        "agent_c_system": """你是 Agent_C — 逻辑对抗检视官。

职责: 对抗性审查前两位 Agent 的结论, 找出逻辑漏洞、遗漏和过度推断。

工作方式:
1. 逐条挑战 Agent_A 的违规判定: 有没有误判? 有没有遗漏?
2. 逐条挑战 Agent_B 的商业解读: 有没有夸大风险? 有没有漏掉关键影响?
3. 提出至少 3 个反事实场景 (如果规则变了/如果平台执行松了/如果同行也在做)
4. 给出你的独立判断: 同意/部分同意/不同意, 并附理由

输出: 对抗检查清单, 每条含 {original_claim, challenge, counter_evidence, final_judgment}。
你的存在是为了让最终结论经得起任何人的质疑。""",

        "referee_system": """你是 Referee — 首席裁判官/主编。

职责: 阅读全部 2 轮辩论记录, 识别冲突, 强行收敛为一个 100% 确定的最终裁决。

收敛规则:
1. 对于 Agent_A / Agent_B / Agent_C 之间的分歧点, 你必须做出最终判决 — 不存在"无法确定"
2. 如果两方同意一方反对, 简述反对方的论据为何被驳回
3. 如果三方各执一词, 你基于证据权重做出判决, 并标注"置信度: 中"
4. 所有模糊地带标注为"待人工确认", 但必须给出你的倾向性判断

输出格式: 严格遵守以下 JSON Schema (无任何多余文字):
{
  "final_verdict": "PASS" | "FAIL" | "CONDITIONAL_PASS",
  "confidence": 0.0-1.0,
  "risk_level": "HIGH" | "MEDIUM" | "LOW",
  "critical_findings": [
    {"finding": "...", "severity": "critical"|"major"|"minor", "rule_ref": "...", "fix": "..."}
  ],
  "commercial_impact": {"estimated_loss_yuan": 0, "urgency": "immediate"|"this_week"|"this_month"},
  "disputed_items": [{"item": "...", "agents_disagree": ["Agent_A","Agent_C"], "referee_ruling": "..."}],
  "action_items": ["..."],
  "human_review_required": true|false,
  "human_review_reason": "..."
}

只输出 JSON, 不要任何解释性文字。""",
    },

    # ---- 通用商业分析域 (可扩展) ----
    "general_business": {
        "agent_a_system": """你是 Agent_A — 风险审计视角。
分析输入数据, 识别所有商业风险、合规问题和结构性缺陷。
输出结构化风险清单。""",

        "agent_b_system": """你是 Agent_B — 商业价值视角。
将分析转化为可执行的商业建议, 保持精炼、高密度、可量化。
输出面向决策者的商业报告草稿。""",

        "agent_c_system": """你是 Agent_C — 逻辑对抗视角。
对抗性审查前两位的结论, 找出逻辑漏洞和未被考虑的替代假设。
输出对抗检查清单和独立判断。""",

        "referee_system": """你是 Referee — 主编。
阅读全部辩论记录, 强制执行最终收敛。
输出严格遵循 {final_verdict, confidence, critical_findings, action_items} Schema 的 JSON。""",
    },
}


# ---------------------------------------------------------------------------
# 指数退避重试装饰器 (3 次, 1s→2s→4s)
# ---------------------------------------------------------------------------

class DebateNetworkError(Exception):
    """辩论过程中的网络/API 调用错误 — 区分于逻辑错误, 触发重试。"""
    pass


class DebateConvergenceError(Exception):
    """Referee 无法收敛 — JSON 解析失败或 Schema 不匹配。"""
    pass


_RETRY_BACKOFF_BASE = 1.0   # 首次重试等待秒数
_RETRY_BACKOFF_FACTOR = 2.0  # 指数因子
_MAX_RETRIES = 3              # 最大重试次数


async def _retry_with_backoff(
    coro_factory: Callable[[], Awaitable[dict[str, Any]]],
    label: str = "llm_call",
    max_retries: int = _MAX_RETRIES,
) -> dict[str, Any]:
    """指数退避重试包装器。

    退避序列: 1s → 2s → 4s (总最坏等待 7s)
    仅在网络/超时异常时重试; 业务逻辑异常直接抛出。

    Args:
        coro_factory: 返回 dict 的异步可调用对象工厂 (每次重试新建连接)
        label: 日志标签
        max_retries: 最大重试次数 (含首次, 默认 3)

    Returns:
        coro_factory 的成功返回值

    Raises:
        DebateNetworkError: 全部重试耗尽后仍失败
    """
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            result = await coro_factory()
            if attempt > 1:
                logger.info(
                    "[debate] %s: 第 %d 次尝试成功", label, attempt,
                )
            return result
        except (asyncio.TimeoutError, ConnectionError, OSError) as exc:
            last_error = exc
            if attempt < max_retries:
                wait = _RETRY_BACKOFF_BASE * (_RETRY_BACKOFF_FACTOR ** (attempt - 1))
                logger.warning(
                    "[debate] %s: 第 %d/%d 次失败 (%s), %.1fs 后重试...",
                    label, attempt, max_retries, exc, wait,
                )
                await asyncio.sleep(wait)
            else:
                logger.error(
                    "[debate] %s: 全部 %d 次重试耗尽, 最终错误: %s",
                    label, max_retries, exc,
                )

    raise DebateNetworkError(
        f"{label}: {max_retries} 次重试全部失败, 最终错误: {last_error}"
    )


# ---------------------------------------------------------------------------
# DebateManager — 核心辩论引擎
# ---------------------------------------------------------------------------

class DebateManager:
    """三人辩论 + 裁判官收敛 + Token KPI 监测器。

    使用方式:
        async def my_llm(messages, model, json_mode, timeout) -> dict:
            ...  # 调用 DeepSeek/OpenAI API
            return {"content": "...", "tokens_input": 500, "tokens_output": 200}

        manager = DebateManager(call_llm=my_llm)
        result = await manager.debate(
            topic="...",
            external_data={"douyin_live_data": {...}},
            domain="douyin_compliance",
        )
        # result.verdict → 稳定 JSON
        # result.total_cost_usd → USD 成本
    """

    # ---- 模型分配: 不同角色可用不同模型 ----
    DEFAULT_MODEL_MAP = {
        "Agent_A": "deepseek-v4-pro",    # 合规审计需最强推理
        "Agent_B": "deepseek-v4-pro",    # 文案转化需高品位
        "Agent_C": "deepseek-v4-pro",    # 逻辑对抗需深度思考
        "Referee": "deepseek-v4-pro",    # 裁判官需要最大上下文+最强收敛
    }

    # ---- 模型定价表 (CNY / 1K tokens) ----
    PRICING = {
        "deepseek-v4-pro":   {"input": 0.01, "output": 0.02},
        "deepseek-v4-flash": {"input": 0.001, "output": 0.002},
        "qwen2.5:14b":       {"input": 0.0, "output": 0.0},
        "default":           {"input": 0.01, "output": 0.02},
    }

    def __init__(
        self,
        call_llm: Callable[..., Awaitable[dict[str, Any]]] | None = None,
        cache_dir: str | Path | None = None,
        usd_cny_rate: float = 7.2,
        model_map: dict[str, str] | None = None,
        max_debate_rounds: int = 2,
        sensitivity: int = 2,
    ) -> None:
        """初始化辩论管理器。

        Args:
            call_llm: 异步 LLM 调用函数。
            cache_dir: 辩论日志缓存目录。默认 ama/core/.cache/
            usd_cny_rate: USD/CNY 汇率, 默认 7.2
            model_map: 角色→模型映射, 覆盖 DEFAULT_MODEL_MAP
            max_debate_rounds: 自由辩论最大轮次 (≥2, 默认 2)
            sensitivity: 审查敏感度 — 1=LENIENT(仅明确违规), 2=STANDARD(含常见灰区), 3=STRICT(一切可争议点)
        """
        self._call_llm = call_llm or self._default_llm_call
        self._cache_dir = Path(cache_dir) if cache_dir else _ensure_cache()
        self._usd_cny_rate = usd_cny_rate
        self._model_map = model_map or self.DEFAULT_MODEL_MAP
        self._max_rounds = max(max_debate_rounds, 2)
        self._sensitivity = max(1, min(sensitivity, 3))  # clamp to [1,3]

        logger.info(
            "[debate] DebateManager 初始化: cache=%s, rate=%.2f, sensitivity=%d(%s)",
            self._cache_dir, usd_cny_rate,
            self._sensitivity, SENSITIVITY_LEVELS[self._sensitivity],
        )

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    async def debate(
        self,
        topic: str,
        external_data: dict[str, Any] | None = None,
        domain: str = "douyin_compliance",
        extra_context: str = "",
    ) -> DebateResult:
        """执行一次完整的三方辩论 + 裁判官收敛。

        这是 DebateManager 的唯一公开入口。全程异步, 状态自包含。

        Args:
            topic: 辩论议题 (例如: "直播间 ID xxx 的话术是否违规?")
            external_data: Douyin MCP 等外部数据源传入的结构化数据。
                           格式自由, 会被注入到各 Agent 的 prompt 中。
                           示例: {"douyin_live_data": {"room_id": "...", "transcript": "...", "products": [...]}}
            domain: 业务域标识, 用于选择 prompt 模板。
                    已注册: "douyin_compliance", "general_business"
                    可通过 register_domain() 扩展。
            extra_context: 额外的上下文信息 (如历史辩论记录、规则手册摘录等)。

        Returns:
            DebateResult — 包含稳定 JSON verdict + 全量 Token 成本 + 辩论日志路径

        Raises:
            ValueError: domain 未注册
            DebateNetworkError: LLM 调用经 3 次重试仍失败
            DebateConvergenceError: Referee JSON 输出无法解析
        """
        if domain not in DOMAIN_PROMPTS:
            raise ValueError(
                f"未注册的业务域: {domain}。可用: {list(DOMAIN_PROMPTS)}。"
                f"使用 register_domain() 注册新域。"
            )

        prompts = DOMAIN_PROMPTS[domain]
        state = DebateState(
            session_id=f"debate-{uuid.uuid4().hex[:12]}",
            topic=topic,
            domain=domain,
            sensitivity=self._sensitivity,
            external_data=external_data,
            usd_cny_rate=self._usd_cny_rate,
        )

        logger.info(
            "[debate] 会话开始: %s | 议题: %.80s... | 域: %s | 敏感度: %d(%s)",
            state.session_id, topic, domain,
            self._sensitivity, SENSITIVITY_LEVELS[self._sensitivity],
        )

        try:
            # --- Round 1: 初始立场陈述 (3 Agent 并发) ---
            logger.info("[debate] %s: Round 1/3 — 初始立场陈述", state.session_id)
            round_1_tasks = [
                self._call_agent(
                    agent_id="Agent_A",
                    role_name="合规风控审计",
                    system_prompt=prompts["agent_a_system"],
                    user_prompt=self._build_user_prompt(
                        topic, external_data, extra_context,
                        round_num=1, role_hint="你是合规风控审计官, 请先识别所有风险点",
                    ),
                    model=self._model_map["Agent_A"],
                    round_num=1,
                ),
                self._call_agent(
                    agent_id="Agent_B",
                    role_name="静奢文案转化",
                    system_prompt=prompts["agent_b_system"],
                    user_prompt=self._build_user_prompt(
                        topic, external_data, extra_context,
                        round_num=1, role_hint="你是静奢文案转化官, 请基于风险点输出商业报告",
                    ),
                    model=self._model_map["Agent_B"],
                    round_num=1,
                ),
                self._call_agent(
                    agent_id="Agent_C",
                    role_name="逻辑对抗检视",
                    system_prompt=prompts["agent_c_system"],
                    user_prompt=self._build_user_prompt(
                        topic, external_data, extra_context,
                        round_num=1, role_hint="你是逻辑对抗检视官, 请挑战前两位的观点",
                    ),
                    model=self._model_map["Agent_C"],
                    round_num=1,
                ),
            ]
            round_1_results = await asyncio.gather(*round_1_tasks, return_exceptions=True)

            # 处理 gather 异常: 单个 Agent 失败 → 记录占位 Argument, 不中断整体流程
            state.round_1 = self._normalize_gather_results(
                round_1_results, ["Agent_A", "Agent_B", "Agent_C"],
                ["合规风控审计", "静奢文案转化", "逻辑对抗检视"], round_num=1,
            )
            self._accumulate_cost(state, state.round_1)
            logger.info(
                "[debate] %s: Round 1 完成 — 累积 Token: %d, 成本: ¥%.4f",
                state.session_id, state.total_tokens, state.total_cost_yuan,
            )

            # --- Round 2: 交叉反驳 (各 Agent 看到其他 Agent 的 Round 1 输出) ---
            logger.info("[debate] %s: Round 2/3 — 交叉反驳", state.session_id)
            round_2_tasks = [
                self._call_agent(
                    agent_id="Agent_A",
                    role_name="合规风控审计",
                    system_prompt=prompts["agent_a_system"],
                    user_prompt=self._build_rebuttal_prompt(
                        topic, external_data, extra_context,
                        agent_id="Agent_A",
                        own_prev=round_1_results[0] if not isinstance(round_1_results[0], Exception) else None,
                        others_prev=[
                            round_1_results[1] if not isinstance(round_1_results[1], Exception) else None,
                            round_1_results[2] if not isinstance(round_1_results[2], Exception) else None,
                        ],
                        other_names=["Agent_B(静奢文案)", "Agent_C(逻辑对抗)"],
                    ),
                    model=self._model_map["Agent_A"],
                    round_num=2,
                ),
                self._call_agent(
                    agent_id="Agent_B",
                    role_name="静奢文案转化",
                    system_prompt=prompts["agent_b_system"],
                    user_prompt=self._build_rebuttal_prompt(
                        topic, external_data, extra_context,
                        agent_id="Agent_B",
                        own_prev=round_1_results[1] if not isinstance(round_1_results[1], Exception) else None,
                        others_prev=[
                            round_1_results[0] if not isinstance(round_1_results[0], Exception) else None,
                            round_1_results[2] if not isinstance(round_1_results[2], Exception) else None,
                        ],
                        other_names=["Agent_A(合规风控)", "Agent_C(逻辑对抗)"],
                    ),
                    model=self._model_map["Agent_B"],
                    round_num=2,
                ),
                self._call_agent(
                    agent_id="Agent_C",
                    role_name="逻辑对抗检视",
                    system_prompt=prompts["agent_c_system"],
                    user_prompt=self._build_rebuttal_prompt(
                        topic, external_data, extra_context,
                        agent_id="Agent_C",
                        own_prev=round_1_results[2] if not isinstance(round_1_results[2], Exception) else None,
                        others_prev=[
                            round_1_results[0] if not isinstance(round_1_results[0], Exception) else None,
                            round_1_results[1] if not isinstance(round_1_results[1], Exception) else None,
                        ],
                        other_names=["Agent_A(合规风控)", "Agent_B(静奢文案)"],
                    ),
                    model=self._model_map["Agent_C"],
                    round_num=2,
                ),
            ]
            round_2_results = await asyncio.gather(*round_2_tasks, return_exceptions=True)
            state.round_2 = self._normalize_gather_results(
                round_2_results, ["Agent_A", "Agent_B", "Agent_C"],
                ["合规风控审计", "静奢文案转化", "逻辑对抗检视"], round_num=2,
            )
            self._accumulate_cost(state, state.round_2)
            logger.info(
                "[debate] %s: Round 2 完成 — 累积 Token: %d, 成本: ¥%.4f",
                state.session_id, state.total_tokens, state.total_cost_yuan,
            )

            # --- Round 3: 裁判官强制收敛 ---
            logger.info("[debate] %s: Round 3/3 — 裁判官强制收敛", state.session_id)
            state.referee_verdict = await self._referee_converge(
                state=state,
                referee_system_prompt=prompts["referee_system"],
                referee_model=self._model_map["Referee"],
            )
            logger.info(
                "[debate] %s: 裁判官裁决完成 — verdict=%s, confidence=%.2f",
                state.session_id,
                state.referee_verdict.get("final_verdict", "UNKNOWN"),
                state.referee_verdict.get("confidence", 0.0),
            )

        except Exception:
            logger.exception("[debate] %s: 辩论过程异常", state.session_id)
            raise

        finally:
            state.completed_at = time.time()
            # 沙盒持久化辩论日志
            state.log_path = str(self._persist_debate_log(state))

        return self._build_result(state)

    def register_domain(
        self, domain: str, prompts: dict[str, str],
    ) -> None:
        """注册新的业务域 prompt 模板 (运行时扩展, 无需重启)。

        Args:
            domain: 域标识 (如 "taobao_compliance")
            prompts: 必须包含 agent_a_system, agent_b_system, agent_c_system, referee_system
        """
        required = {"agent_a_system", "agent_b_system", "agent_c_system", "referee_system"}
        missing = required - set(prompts.keys())
        if missing:
            raise ValueError(f"缺少必需的 prompt 键: {missing}")
        DOMAIN_PROMPTS[domain] = dict(prompts)
        logger.info("[debate] 注册新业务域: %s", domain)

    # ------------------------------------------------------------------
    # 内部方法 — LLM 调用与重试
    # ------------------------------------------------------------------

    async def _call_agent(
        self,
        agent_id: str,
        role_name: str,
        system_prompt: str,
        user_prompt: str,
        model: str,
        round_num: int,
    ) -> AgentArgument:
        """调用单个 Agent, 带指数退避重试。

        内部通过 _retry_with_backoff 包裹, 网络瞬断不会导致辩论崩溃。
        """
        t0 = time.time()

        async def _do_call() -> dict[str, Any]:
            return await self._call_llm(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=model,
                json_mode=False,  # Agent 自由辩论阶段不强制 JSON
                timeout=120,
            )

        try:
            raw = await _retry_with_backoff(
                _do_call,
                label=f"{agent_id}({role_name})_round{round_num}",
                max_retries=_MAX_RETRIES,
            )
        except DebateNetworkError as exc:
            logger.error(
                "[debate] %s Round %d: LLM 调用彻底失败 — %s",
                agent_id, round_num, exc,
            )
            # 失败时返回占位 Argument, 不中断整体辩论流程
            return AgentArgument(
                agent_id=agent_id,
                agent_role=role_name,
                round_num=round_num,
                content=f"[{agent_id} 调用失败: {exc}]",
                token_cost=TokenCost(
                    tokens_input=0, tokens_output=0,
                    cost_yuan=0.0, cost_usd=0.0, model=model,
                    duration_ms=int((time.time() - t0) * 1000),
                    retry_count=_MAX_RETRIES,
                ),
                metadata={"error": str(exc), "status": "failed"},
            )

        tokens_in = raw.get("tokens_input", 0)
        tokens_out = raw.get("tokens_output", 0)
        cost_yuan = self._estimate_cost(model, tokens_in, tokens_out)
        duration_ms = int((time.time() - t0) * 1000)

        return AgentArgument(
            agent_id=agent_id,
            agent_role=role_name,
            round_num=round_num,
            content=raw["content"],
            token_cost=TokenCost(
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                cost_yuan=cost_yuan,
                cost_usd=round(cost_yuan / self._usd_cny_rate, 6),
                model=model,
                duration_ms=duration_ms,
            ),
            metadata={"model_used": model},
        )

    async def _referee_converge(
        self,
        state: DebateState,
        referee_system_prompt: str,
        referee_model: str,
    ) -> dict[str, Any]:
        """Round 3: 裁判官阅读全部辩论记录 → 输出强制收敛 JSON。

        JSON 解析失败时重试 1 次 (带更强烈的 JSON-only 指令)。
        仍失败则抛出 DebateConvergenceError。
        """
        debate_transcript = self._format_debate_transcript(state)

        # 敏感度分层指令
        sensitivity = state.sensitivity
        if sensitivity == 1:
            sensitivity_instruction = """## 敏感度: LENIENT (宽松)
你是宽松审查官。审查原则:
- 仅标记**明确、无疑义**的违规 (如: 使用了"最好""绝对""全网最低"等明文禁止的词语)
- 灰色地带、语用学歧义、可多解的话术 → 一律放过, 不标记为违规
- 对于"可能构成"、"有风险倾向"的表述 → 归类为 PASS 而非 CONDITIONAL_PASS
- confidence 阈值: 仅在有确凿违规证据时 >0.7
- 默认立场: 商家善意推定, 疑罪从无
- 目标: 快速筛查, 放过低风险内容, 只拦明确红线"""
        elif sensitivity == 3:
            sensitivity_instruction = """## 敏感度: STRICT (严格)
你是严格合规审计官。审查原则:
- 标记**一切可争议、可解释为违规**的内容, 包括语用学暗示和修辞策略
- 灰色地带 → 一律标记, 归类为 CONDITIONAL_PASS 或 FAIL
- 引用可能适用的法律法规 (即使不完全匹配), 标注风险
- 对于"可能误导消费者"但未明确违规的表述 → 归类为 CONDITIONAL_PASS
- confidence 阈值: 即使证据不完全确凿, 只要有合理怀疑 >0.6
- 默认立场: 平台规则严格解释, 疑罪从有 (标记待查)
- 目标: 零遗漏, 宁可误标不可漏标, 适合上市企业/奢侈品牌"""
        else:  # sensitivity == 2 (STANDARD)
            sensitivity_instruction = """## 敏感度: STANDARD (标准)
你是均衡审查官。审查原则:
- 标记**明确违规 + 常见灰区** (行业公认的高风险模式)
- 明显的语用学违规 (如: 用对比图暗示功效) → 标记
- 但不过度解读修辞 (如: "福利价"不构成绝对化用语)
- 有争议的项目 → 标记但标注"灰区, 建议优化"
- confidence 阈值: 0.7
- 默认立场: 平衡执法精神与商业实践
- 目标: 覆盖 95% 实际风险, 不放过大问题, 不纠结极端边缘情况"""

        user_prompt = f"""以下是三方 Agent 就议题进行的 2 轮辩论完整记录。

## 议题
{state.topic}

## 外部数据
{json.dumps(state.external_data, ensure_ascii=False, indent=2) if state.external_data else "无"}

## 辩论记录
{debate_transcript}

{sensitivity_instruction}

## 你的任务
作为 Referee(首席裁判官/主编), 阅读以上全部内容后, 输出一个严格符合 JSON Schema 的最终裁决。
**只输出 JSON, 不要任何 markdown 代码块标记, 不要任何解释性文字。**
必须以 `{{` 开头, 以 `}}` 结尾。"""

        for attempt in range(1, 3):  # 最多 2 次尝试
            t0 = time.time()
            raw = await self._call_llm(
                messages=[
                    {"role": "system", "content": referee_system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=referee_model,
                json_mode=True,  # 裁判官强制 JSON 模式
                timeout=180,     # 裁判官需要更长超时 (上下文大)
            )

            # 累积裁判官成本
            tokens_in = raw.get("tokens_input", 0)
            tokens_out = raw.get("tokens_output", 0)
            cost_yuan = self._estimate_cost(referee_model, tokens_in, tokens_out)
            self._accumulate_single_cost(state, tokens_in, tokens_out, cost_yuan,
                                        referee_model, int((time.time() - t0) * 1000))

            content = raw["content"].strip()
            # 清洗可能的 markdown 代码块包装
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            try:
                verdict = json.loads(content)
                # 验证必需字段
                self._validate_verdict_schema(verdict)
                return verdict
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning(
                    "[debate] %s: 裁判官 JSON 解析失败 (尝试 %d/2): %s",
                    state.session_id, attempt, exc,
                )
                if attempt == 2:
                    raise DebateConvergenceError(
                        f"裁判官连续 2 次输出非 JSON 或 Schema 不匹配: {exc}\n"
                        f"原始输出前 300 字符: {content[:300]}"
                    )
                # 重试: 更强的 JSON-only 指令
                user_prompt += (
                    "\n\n⚠️ 你上一次输出不是合法 JSON! "
                    "这次必须只输出 JSON, 以 { 开头, 以 } 结尾, 不要任何其他内容。"
                )

        # 不可达 (循环内必然 return 或 raise)
        raise DebateConvergenceError("裁判官收敛失败 — 不可达分支")

    # ------------------------------------------------------------------
    # 内部方法 — Prompt 构建
    # ------------------------------------------------------------------

    def _build_user_prompt(
        self,
        topic: str,
        external_data: dict[str, Any] | None,
        extra_context: str,
        round_num: int,
        role_hint: str,
    ) -> str:
        """构建 Agent 的 user prompt (Round 1 初始陈述)。

        外部数据 (Douyin MCP 等) 在此注入, 格式自由, 不强制 Schema。
        """
        parts = [
            f"## 辩论议题 (Round {round_num}/3)\n{topic}\n",
        ]
        if extra_context:
            parts.append(f"## 附加上下文\n{extra_context}\n")
        if external_data:
            parts.append(
                "## 外部数据 (来自 Douyin MCP / 数据采集系统)\n"
                f"```json\n{json.dumps(external_data, ensure_ascii=False, indent=2)}\n```\n"
            )
        parts.append(f"## 你的角色与任务\n{role_hint}")
        return "\n".join(parts)

    def _build_rebuttal_prompt(
        self,
        topic: str,
        external_data: dict[str, Any] | None,
        extra_context: str,
        agent_id: str,
        own_prev: AgentArgument | None,
        others_prev: list[AgentArgument | None],
        other_names: list[str],
    ) -> str:
        """构建 Agent 的 rebuttal prompt (Round 2 交叉反驳)。

        每个 Agent 看到:
          1. 自己 Round 1 的论点
          2. 其他两位 Agent Round 1 的论点
          3. 被要求针对性反驳/补充
        """
        parts = [
            f"## 辩论议题 (Round 2/3 — 交叉反驳)\n{topic}\n",
        ]

        if extra_context:
            parts.append(f"## 附加上下文\n{extra_context}\n")
        if external_data:
            parts.append(
                "## 外部数据 (不变)\n"
                f"```json\n{json.dumps(external_data, ensure_ascii=False, indent=2)}\n```\n"
            )

        parts.append("## Round 1 辩论记录\n")

        if own_prev:
            parts.append(
                f"### 你的 Round 1 立场 ({agent_id})\n{own_prev.content[:2000]}\n"
                f"(截断, 完整见辩论日志)\n"
            )
        else:
            parts.append(f"### 你的 Round 1 立场 ({agent_id})\n[调用失败, 无记录]\n")

        for i, (other, name) in enumerate(zip(others_prev, other_names)):
            if other:
                parts.append(
                    f"### {name} 的 Round 1 论点\n{other.content[:2000]}\n"
                    f"(截断, 完整见辩论日志)\n"
                )
            else:
                parts.append(f"### {name} 的 Round 1 论点\n[调用失败, 无记录]\n")

        parts.append(
            "## 你的 Round 2 任务\n"
            f"你是 {agent_id}。请针对其他 Agent 的论点进行反驳、补充或修正。"
            "如果你的原始判断被其他 Agent 说服了, 请明确承认并修正。"
            "如果其他 Agent 遗漏了关键点, 请指出。"
            "目标是经过这一轮辩论后, 结论更加准确和完整。"
        )
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # 内部方法 — 成本计算
    # ------------------------------------------------------------------

    def _estimate_cost(
        self, model: str, tokens_input: int, tokens_output: int,
    ) -> float:
        """根据模型定价表计算单次调用的 CNY 成本。"""
        pricing = self.PRICING.get(model, self.PRICING["default"])
        input_cost = (tokens_input / 1000) * pricing["input"]
        output_cost = (tokens_output / 1000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    def _accumulate_single_cost(
        self,
        state: DebateState,
        tokens_in: int,
        tokens_out: int,
        cost_yuan: float,
        model: str,
        duration_ms: int,
    ) -> None:
        """累加单次调用成本到会话状态 (原地修改 dataclass, 无副作用)。"""
        c = state.cumulative_cost
        c.tokens_input += tokens_in
        c.tokens_output += tokens_out
        c.cost_yuan = round(c.cost_yuan + cost_yuan, 6)
        c.cost_usd = round(c.cost_yuan / state.usd_cny_rate, 6)
        c.duration_ms += duration_ms
        c.model = model  # 最后使用的模型

    def _accumulate_cost(
        self, state: DebateState, arguments: list[AgentArgument],
    ) -> None:
        """累加一轮辩论中所有 Agent 的成本。"""
        for arg in arguments:
            tc = arg.token_cost
            self._accumulate_single_cost(
                state, tc.tokens_input, tc.tokens_output,
                tc.cost_yuan, tc.model, tc.duration_ms,
            )

    # ------------------------------------------------------------------
    # 内部方法 — 辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_gather_results(
        results: list[Any],
        agent_ids: list[str],
        role_names: list[str],
        round_num: int,
    ) -> list[AgentArgument]:
        """将 asyncio.gather(return_exceptions=True) 结果标准化为 AgentArgument 列表。

        Exception → 占位 AgentArgument (不中断整体流程)。
        """
        out: list[AgentArgument] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "[debate] Round %d: %s(%s) 异常 — %s",
                    round_num, agent_ids[i], role_names[i], result,
                )
                out.append(AgentArgument(
                    agent_id=agent_ids[i],
                    agent_role=role_names[i],
                    round_num=round_num,
                    content=f"[{agent_ids[i]}({role_names[i]}) 执行异常: {result}]",
                    token_cost=TokenCost(
                        tokens_input=0, tokens_output=0,
                        cost_yuan=0.0, cost_usd=0.0, model="unknown",
                    ),
                    metadata={"error": str(result), "status": "exception"},
                ))
            elif isinstance(result, AgentArgument):
                out.append(result)
            else:
                # 防御性: 意外类型 → 字符串化
                out.append(AgentArgument(
                    agent_id=agent_ids[i],
                    agent_role=role_names[i],
                    round_num=round_num,
                    content=str(result)[:2000],
                    token_cost=TokenCost(
                        tokens_input=0, tokens_output=0,
                        cost_yuan=0.0, cost_usd=0.0, model="unknown",
                    ),
                    metadata={"unexpected_type": str(type(result))},
                ))
        return out

    @staticmethod
    def _format_debate_transcript(state: DebateState) -> str:
        """将辩论状态格式化为裁判官可读的纯文本记录。"""
        lines = []
        for label, arguments in [("Round 1", state.round_1), ("Round 2", state.round_2)]:
            lines.append(f"### {label}")
            for arg in arguments:
                lines.append(
                    f"#### {arg.agent_id} ({arg.agent_role})\n"
                    f"{arg.content}\n"
                )
        return "\n".join(lines)

    @staticmethod
    def _validate_verdict_schema(verdict: dict[str, Any]) -> None:
        """校验裁判官输出的 JSON Schema 完整性。

        缺少必需字段 → ValueError (触发重试)。
        额外字段不做限制 (向前兼容)。
        """
        required = {
            "final_verdict": str,
            "confidence": (int, float),
            "risk_level": str,
            "critical_findings": list,
            "action_items": list,
            "human_review_required": bool,
        }
        for key, expected_type in required.items():
            if key not in verdict:
                raise ValueError(
                    f"裁判官 JSON 缺少必需字段: '{key}'"
                )
            value = verdict[key]
            if not isinstance(value, expected_type):
                raise ValueError(
                    f"裁判官 JSON 字段 '{key}' 类型错误: "
                    f"期望 {expected_type.__name__}, 实际 {type(value).__name__}"
                )

        # 额外校验
        conf = verdict["confidence"]
        if not (0.0 <= conf <= 1.0):
            raise ValueError(f"confidence 越界: {conf} (应在 0.0-1.0)")
        if verdict["risk_level"] not in ("HIGH", "MEDIUM", "LOW"):
            raise ValueError(f"risk_level 非法: {verdict['risk_level']}")
        if verdict["final_verdict"] not in ("PASS", "FAIL", "CONDITIONAL_PASS"):
            raise ValueError(f"final_verdict 非法: {verdict['final_verdict']}")

    def _persist_debate_log(self, state: DebateState) -> Path:
        """沙盒持久化: 将完整辩论状态写入 .cache/ 目录。

        文件命名: {session_id}.json
        内容: 全量 DebateState 序列化 (不含不可序列化的回调函数)。
        写入失败不抛出 — 日志告警后静默继续。
        """
        log_path = self._cache_dir / f"{state.session_id}.json"
        try:
            serializable = {
                "session_id": state.session_id,
                "topic": state.topic,
                "domain": state.domain,
                "external_data": state.external_data,
                "round_1": [
                    {
                        "agent_id": a.agent_id,
                        "agent_role": a.agent_role,
                        "round_num": a.round_num,
                        "content": a.content,
                        "token_cost": {
                            "tokens_input": a.token_cost.tokens_input,
                            "tokens_output": a.token_cost.tokens_output,
                            "cost_yuan": a.token_cost.cost_yuan,
                            "cost_usd": a.token_cost.cost_usd,
                            "model": a.token_cost.model,
                            "duration_ms": a.token_cost.duration_ms,
                        },
                        "metadata": a.metadata,
                    }
                    for a in state.round_1
                ],
                "round_2": [
                    {
                        "agent_id": a.agent_id,
                        "agent_role": a.agent_role,
                        "round_num": a.round_num,
                        "content": a.content,
                        "token_cost": {
                            "tokens_input": a.token_cost.tokens_input,
                            "tokens_output": a.token_cost.tokens_output,
                            "cost_yuan": a.token_cost.cost_yuan,
                            "cost_usd": a.token_cost.cost_usd,
                            "model": a.token_cost.model,
                            "duration_ms": a.token_cost.duration_ms,
                        },
                        "metadata": a.metadata,
                    }
                    for a in state.round_2
                ],
                "referee_verdict": state.referee_verdict,
                "cumulative_cost": {
                    "tokens_input": state.cumulative_cost.tokens_input,
                    "tokens_output": state.cumulative_cost.tokens_output,
                    "cost_yuan": state.cumulative_cost.cost_yuan,
                    "cost_usd": state.cumulative_cost.cost_usd,
                    "duration_ms": state.cumulative_cost.duration_ms,
                },
                "duration_seconds": state.duration_seconds,
                "started_at": datetime.fromtimestamp(
                    state.started_at, tz=timezone.utc,
                ).isoformat(),
                "completed_at": datetime.fromtimestamp(
                    state.completed_at or state.started_at, tz=timezone.utc,
                ).isoformat(),
            }
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(serializable, f, ensure_ascii=False, indent=2)
            logger.info("[debate] 辩论日志已持久化: %s", log_path)
        except Exception:
            logger.exception("[debate] 持久化辩论日志失败 (非致命)")

        return log_path

    def _build_result(self, state: DebateState) -> DebateResult:
        """从 DebateState 构建最终 DebateResult。"""
        all_args = list(state.round_1) + list(state.round_2)
        return DebateResult(
            session_id=state.session_id,
            verdict=state.referee_verdict or {},
            all_arguments=all_args,
            rounds_count=2 + (1 if state.referee_verdict else 0),
            total_tokens=state.total_tokens,
            total_cost_yuan=state.total_cost_yuan,
            total_cost_usd=state.total_cost_usd,
            duration_seconds=state.duration_seconds,
            debate_log_path=state.log_path or "",
            domain=state.domain,
            topic=state.topic,
            sensitivity=state.sensitivity,
            sensitivity_label=SENSITIVITY_LEVELS.get(state.sensitivity, "STANDARD"),
        )

    # ------------------------------------------------------------------
    # 默认 LLM 调用实现 — 直连 DeepSeek API (Anthropic-compatible 协议)
    # ------------------------------------------------------------------

    @staticmethod
    async def _default_llm_call(
        messages: list[dict[str, str]],
        model: str = "deepseek-v4-pro",
        json_mode: bool = False,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """默认 LLM 调用: DeepSeek API 直连 (OpenAI-compatible 协议)。

        用户可通过构造函数注入 call_llm 覆盖此实现。
        依赖环境变量: DEEPSEEK_API_KEY 或 ANTHROPIC_AUTH_TOKEN
        """
        import aiohttp

        api_key = os.environ.get(
            "DEEPSEEK_API_KEY",
            os.environ.get("ANTHROPIC_AUTH_TOKEN", ""),
        )
        if not api_key:
            raise DebateNetworkError(
                "缺少 API Key: 请设置 DEEPSEEK_API_KEY 或 ANTHROPIC_AUTH_TOKEN 环境变量"
            )

        # OpenAI-compatible endpoint (与 main.py 一致, 已验证可用)
        api_base = os.environ.get(
            "AMA_LLM_API_BASE",
            "https://api.deepseek.com",
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        # 构建 OpenAI-compatible messages 格式
        api_messages = []
        for m in messages:
            api_messages.append({"role": m["role"], "content": m["content"]})

        body: dict[str, Any] = {
            "model": model,
            "messages": api_messages,
            "max_tokens": 8192 if json_mode else 4096,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_base}/v1/chat/completions",
                json=body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(
                        "[debate] LLM API error %d: %s",
                        resp.status, error_text[:500],
                    )
                    raise DebateNetworkError(
                        f"LLM API 返回 {resp.status}: {error_text[:500]}"
                    )
                data = await resp.json()

        # 提取内容 (OpenAI 格式)
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")

        usage = data.get("usage", {})
        tokens_input = usage.get("prompt_tokens", 0)
        tokens_output = usage.get("completion_tokens", 0)

        if not content:
            logger.error(
                "[debate] LLM returned empty content. Response keys: %s, "
                "finish_reason: %s",
                list(data.keys()),
                choice.get("finish_reason", "unknown"),
            )

        return {
            "content": content,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
        }


# ---------------------------------------------------------------------------
# 便捷工厂函数
# ---------------------------------------------------------------------------

def create_debate_manager(
    api_key: str | None = None,
    api_base: str | None = None,
    cache_dir: str | None = None,
    usd_cny_rate: float = 7.2,
) -> DebateManager:
    """创建预配置的 DebateManager (使用内置 DeepSeek 直连)。

    Args:
        api_key: DeepSeek API key。默认从环境变量读取。
        api_base: API 端点。默认 https://api.deepseek.com/anthropic
        cache_dir: 缓存目录。默认 ama/core/.cache/
        usd_cny_rate: 汇率。默认 7.2

    Returns:
        可直接调用 debate() 的 DebateManager 实例
    """
    if api_key:
        os.environ["DEEPSEEK_API_KEY"] = api_key
    if api_base:
        os.environ["AMA_LLM_API_BASE"] = api_base

    return DebateManager(
        call_llm=None,  # 使用内置 _default_llm_call
        cache_dir=cache_dir,
        usd_cny_rate=usd_cny_rate,
    )
