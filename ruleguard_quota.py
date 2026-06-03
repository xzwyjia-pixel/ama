#!/usr/bin/env python
"""ZhenAudit 配额管理器 — IP + Cookie 双层限额, 每日 3 次免费审查。

策略 (双 key 独立计数, 任一超限即拦截):
  1. IP 限流 — 防止多浏览器/无痕模式刷量
  2. Cookie 限流 — 防止同 IP 下多用户共享配额
  3. 日重置 — 每日 0 点自动清零 (按 UTC+8 日历日)

存储: 文件 JSON (data/quotas/{date}.json), 零外部依赖, 适合 MVP 阶段。
生产扩容时可替换为 Redis Sorted Set (ZINCRBY + TTL)。

集成方式:
    from ruleguard_quota import QuotaManager
    quota = QuotaManager()
    if not quota.check(ip, cookie_id):
        raise HTTPException(status_code=402, ...)
    # ... 执行审查 ...
    quota.record(ip, cookie_id)
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# ──────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────

FREE_DAILY_LIMIT = 3  # 每日免费审查次数
TZ_SHANGHAI = timezone(timedelta(hours=8))  # UTC+8
DATA_DIR = Path(__file__).parent / "data" / "quotas"

# 付费方案提示 (402 响应体)
PRICING_INFO = {
    "plans": [
        {"name": "Starter", "price_cny": 99, "audits_per_month": 100, "overage_cny": 1.5},
        {"name": "Pro", "price_cny": 499, "audits_per_month": 1000, "overage_cny": 0.8},
        {"name": "Enterprise", "price_cny": 2999, "audits_per_month": -1, "overage_cny": 0},  # -1 = 无限
    ],
    "contact": "sales@zhenaudit.io",
    "upgrade_url": "/pricing",
}


# ──────────────────────────────────────────────
# QuotaManager
# ──────────────────────────────────────────────


class QuotaManager:
    """线程安全的文件型配额管理器。"""

    def __init__(
        self,
        daily_limit: int = FREE_DAILY_LIMIT,
        data_dir: str | Path | None = None,
    ) -> None:
        self.daily_limit = daily_limit
        self._data_dir = Path(data_dir) if data_dir else DATA_DIR
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    # ── 公开 API ──────────────────────────

    def check(self, ip: str, cookie_id: str | None = None) -> bool:
        """检查是否还有剩余额度。

        Args:
            ip: 客户端 IP (必填, 从 X-Forwarded-For 或 request.client.host 获取)
            cookie_id: 浏览器 Cookie 标识 (可选, 用于精确追踪)

        Returns:
            True 表示有剩余额度, False 表示已用尽
        """
        today = self._today_key()
        data = self._load(today)

        # IP 维度检查
        ip_key = f"ip:{ip}"
        ip_count = data.get(ip_key, {}).get("count", 0)
        if ip_count >= self.daily_limit:
            return False

        # Cookie 维度检查 (如果传入)
        if cookie_id:
            cookie_key = f"cookie:{cookie_id}"
            cookie_count = data.get(cookie_key, {}).get("count", 0)
            if cookie_count >= self.daily_limit:
                return False

        return True

    def record(self, ip: str, cookie_id: str | None = None) -> dict:
        """记录一次审查, 返回剩余额度快照。

        调用方应在审查成功后调用此方法 (fail-open: 审查失败不扣额度)。
        """
        today = self._today_key()
        now_iso = datetime.now(TZ_SHANGHAI).isoformat()

        remaining = {"ip_remaining": self.daily_limit, "cookie_remaining": self.daily_limit}

        with self._lock:
            data = self._load(today)

            # IP key
            ip_key = f"ip:{ip}"
            ip_entry = data.get(ip_key, {"count": 0})
            ip_entry["count"] += 1
            ip_entry["last_request"] = now_iso
            data[ip_key] = ip_entry
            remaining["ip_remaining"] = max(0, self.daily_limit - ip_entry["count"])

            # Cookie key
            if cookie_id:
                cookie_key = f"cookie:{cookie_id}"
                cookie_entry = data.get(cookie_key, {"count": 0})
                cookie_entry["count"] += 1
                cookie_entry["last_request"] = now_iso
                data[cookie_key] = cookie_entry
                remaining["cookie_remaining"] = max(0, self.daily_limit - cookie_entry["count"])

            self._save(today, data)

        return remaining

    def remaining(self, ip: str, cookie_id: str | None = None) -> dict:
        """查询剩余额度 (不扣减)。"""
        today = self._today_key()
        data = self._load(today)

        ip_count = data.get(f"ip:{ip}", {}).get("count", 0)
        result = {"ip_remaining": max(0, self.daily_limit - ip_count)}

        if cookie_id:
            cookie_count = data.get(f"cookie:{cookie_id}", {}).get("count", 0)
            result["cookie_remaining"] = max(0, self.daily_limit - cookie_count)

        return result

    # ── 内部 ──────────────────────────────

    def _today_key(self) -> str:
        """返回今日日期字符串 (UTC+8), 用作文件名。"""
        return datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    def _file_path(self, date_key: str) -> Path:
        return self._data_dir / f"{date_key}.json"

    def _load(self, date_key: str) -> dict:
        """加载当日配额文件 (不存在则返回空 dict)。"""
        fp = self._file_path(date_key)
        if not fp.exists():
            return {}
        try:
            return json.loads(fp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, date_key: str, data: dict) -> None:
        """原子写入: 先写临时文件再 rename。"""
        fp = self._file_path(date_key)
        tmp = fp.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(fp)  # 原子替换 (同文件系统)

    # ── 运维 ──────────────────────────────

    def cleanup_old(self, keep_days: int = 30) -> int:
        """清理超过 keep_days 天的配额文件, 返回删除数量。"""
        cutoff = datetime.now(TZ_SHANGHAI) - timedelta(days=keep_days)
        deleted = 0
        for fp in self._data_dir.glob("*.json"):
            try:
                date_str = fp.stem
                file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=TZ_SHANGHAI)
                if file_date < cutoff:
                    fp.unlink()
                    deleted += 1
            except (ValueError, OSError):
                continue
        return deleted


# ──────────────────────────────────────────────
# 单例工厂
# ──────────────────────────────────────────────

_quota_instance: QuotaManager | None = None


def get_quota_manager() -> QuotaManager:
    """获取全局 QuotaManager 单例。"""
    global _quota_instance
    if _quota_instance is None:
        _quota_instance = QuotaManager()
    return _quota_instance


# ──────────────────────────────────────────────
# Cookie 工具
# ──────────────────────────────────────────────

def generate_visitor_id() -> str:
    """生成唯一访客 ID (UUID4), 用于 Set-Cookie。"""
    return uuid.uuid4().hex


COOKIE_NAME = "_zid"  # ZhenAudit ID
COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # 1 年
