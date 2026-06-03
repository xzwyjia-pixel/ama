#!/usr/bin/env python
"""ZhenAudit 甄查 API — RuleGuard Pro 商业化 FastAPI 服务。

将 AMA Debate Protocol (三方辩论+裁判官收敛) 包装为付费 API。
每个请求独立创建 DebateManager 实例, 沙盒隔离, 无状态共享。

启动:
  uvicorn ruleguard_server:app --host 0.0.0.0 --port 8000 --reload

生产:
  uvicorn ruleguard_server:app --host 0.0.0.0 --port 8000 --workers 4

依赖:
  - ama/core/debate.py (Agent Debate Protocol)
  - ruleguard_quota.py   (IP+Cookie 双层限额)
  - DEEPSEEK_API_KEY 环境变量 (LLM 调用)
  - fastapi, uvicorn, pydantic
"""

from __future__ import annotations

import sys
from pathlib import Path

# 确保 ama 包可导入 (项目根目录加入 sys.path)
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ama.core.debate import (
    DebateManager,
    DebateResult,
    SENSITIVITY_LEVELS,
    create_debate_manager,
)
from ruleguard_quota import (
    QuotaManager,
    get_quota_manager,
    generate_visitor_id,
    COOKIE_NAME,
    COOKIE_MAX_AGE,
    PRICING_INFO,
)

# ──────────────────────────────────────────────
# FastAPI 应用
# ──────────────────────────────────────────────

app = FastAPI(
    title="ZhenAudit 甄查 API",
    description="RuleGuard Pro 商业化合规审查 API — 基于三方 AI Agent 辩论引擎",
    version="1.0.0",
)

# ──────────────────────────────────────────────
# 请求/响应模型
# ──────────────────────────────────────────────


class AuditRequest(BaseModel):
    text: str = Field(..., description="待审查的文本内容 (直播间话术/文案/商品描述等)")
    sensitivity: int = Field(
        2,
        ge=1,
        le=3,
        description="审查敏感度: 1=LENIENT(仅明确违规), 2=STANDARD(含常见灰区), 3=STRICT(一切可争议点)",
    )
    user_id: str = Field(..., description="用户唯一标识, 用于配额管理和计费")


class AuditResponse(BaseModel):
    status: str
    data: dict | None = None
    cost: dict | None = None
    quota: dict | None = None
    session_id: str | None = None

    model_config = {"json_schema_extra": {
        "example": {
            "status": "success",
            "data": {
                "verdict": {"is_violation": True, "risk_level": "HIGH", "reason": "..."},
            },
            "cost": {"tokens": 12450, "cost_yuan": 0.05, "cost_usd": 0.007},
            "quota": {"daily_limit": 3, "ip_remaining": 2, "cookie_remaining": 2},
            "session_id": "debate-a1b2c3d4e5f6",
        }
    }}


class HealthResponse(BaseModel):
    status: str
    version: str
    debate_engine: str


# ──────────────────────────────────────────────
# 核心桥接函数 — 连接 FastAPI 与 Debate Protocol
# ──────────────────────────────────────────────


async def run_audit_flow(
    text: str,
    sensitivity: int = 2,
    domain: str = "douyin_compliance",
) -> DebateResult:
    """将 API 请求参数桥接到 AMA Debate Protocol 引擎。

    每次调用创建独立的 DebateManager 实例, 确保请求间沙盒隔离。
    若 DEEPSEEK_API_KEY 未设置, 抛出 HTTPException 503。

    Args:
        text: 待审查文本
        sensitivity: 1=LENIENT, 2=STANDARD, 3=STRICT
        domain: 业务域标识

    Returns:
        DebateResult: 包含 verdict, all_arguments, 成本明细等
    """
    try:
        manager = create_debate_manager(sensitivity=sensitivity)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"辩论引擎初始化失败: {e}",
        )

    try:
        result = await manager.debate(
            topic=text,
            domain=domain,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"辩论执行异常: {e}",
        )


# ──────────────────────────────────────────────
# 商业化配额拦截器 — IP + Cookie 双层限额
# ──────────────────────────────────────────────


def _get_client_ip(request: Request) -> str:
    """从请求中提取客户端真实 IP。

    优先取 X-Forwarded-For (最左第一个, Nginx/Caddy 反代场景),
    回退到 X-Real-IP, 最后取 request.client.host (直连场景)。
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"


def _get_or_set_visitor_id(request: Request, response: Response) -> str:
    """获取或创建访客 Cookie (_zid)。

    若请求已携带有效 _zid Cookie 则直接返回,
    否则生成新 UUID 并 Set-Cookie。
    """
    visitor_id = request.cookies.get(COOKIE_NAME)
    if visitor_id:
        return visitor_id
    visitor_id = generate_visitor_id()
    response.set_cookie(
        key=COOKIE_NAME,
        value=visitor_id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,  # 开发阶段 HTTP; 生产改 True (HTTPS only)
    )
    return visitor_id


# ──────────────────────────────────────────────
# API 端点
# ──────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点 — 用于 K8s liveness probe / 负载均衡器探活。"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "debate_engine": "AMA Debate Protocol v2.0",
    }


@app.get("/v1/quota")
async def api_quota(request: Request, response: Response):
    """查询剩余免费审查额度 (不扣减)。

    返回 IP 和 Cookie 两个维度的剩余次数,
    只要任一维度归零即触发 402 拦截。
    """
    quota = get_quota_manager()
    ip = _get_client_ip(request)
    visitor_id = _get_or_set_visitor_id(request, response)

    remaining = quota.remaining(ip, visitor_id)
    return {
        "status": "success",
        "quota": {
            "daily_limit": quota.daily_limit,
            "ip_remaining": remaining["ip_remaining"],
            "cookie_remaining": remaining["cookie_remaining"],
            "effective_remaining": min(
                remaining["ip_remaining"], remaining["cookie_remaining"]
            ),
        },
    }


@app.post("/v1/audit", response_model=AuditResponse)
async def api_audit(req: AuditRequest, request: Request, response: Response):
    """内容合规审查 — 核心付费 API。

    流程:
      1. 参数校验 (Pydantic 自动)
      2. IP + Cookie 双层限额拦截 (每日免费 3 次)
      3. 桥接到 AMA Debate Protocol 三方辩论引擎
      4. 记录配额消耗 + 返回结构化审查结果 + Token 成本明细
    """
    # ── 1. 获取客户端身份 ──
    ip = _get_client_ip(request)
    visitor_id = _get_or_set_visitor_id(request, response)

    # ── 2. 商业化限额拦截 ──
    quota = get_quota_manager()
    if not quota.check(ip, visitor_id):
        remaining = quota.remaining(ip, visitor_id)
        return JSONResponse(
            status_code=402,
            content={
                "status": "quota_exhausted",
                "detail": "免费额度已用完 (3次/天)，请订阅方案解锁无限审查",
                "quota": {
                    "daily_limit": quota.daily_limit,
                    "ip_remaining": remaining["ip_remaining"],
                    "cookie_remaining": remaining["cookie_remaining"],
                },
                "pricing": PRICING_INFO,
            },
        )

    # ── 3. 执行辩论审查 ──
    result = await run_audit_flow(
        text=req.text,
        sensitivity=req.sensitivity,
    )

    # ── 4. 记录配额消耗 (审查成功才扣, fail-open 不扣额度) ──
    remaining = quota.record(ip, visitor_id)

    # ── 5. 构建响应 ──
    sensitivity_label = SENSITIVITY_LEVELS.get(req.sensitivity, "STANDARD")
    return {
        "status": "success",
        "data": {
            "verdict": result.verdict,
            "sensitivity": sensitivity_label,
            "domain": result.domain,
        },
        "cost": {
            "tokens": result.total_tokens,
            "cost_yuan": round(result.total_cost_yuan, 6),
            "cost_usd": round(result.total_cost_usd, 6),
            "duration_seconds": result.duration_seconds,
        },
        "quota": {
            "daily_limit": quota.daily_limit,
            "ip_remaining": remaining["ip_remaining"],
            "cookie_remaining": remaining["cookie_remaining"],
            "effective_remaining": min(
                remaining["ip_remaining"], remaining["cookie_remaining"]
            ),
        },
        "session_id": result.session_id,
    }


# ──────────────────────────────────────────────
# 直接启动 (开发用)
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "ruleguard_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
