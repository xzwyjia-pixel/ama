#!/usr/bin/env python3
"""RuleGuard Pro 辩论协议实战测试 — 三段真实文案"""
import json, sys, os

# 确保模块可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ama.core.debate import DebateManager, LOCAL_CONFIG

# ④ 如果本地代理没启动, 回退到直连
PROXY_URL = LOCAL_CONFIG["api_base_url"]
DIRECT_URL = "https://api.deepseek.com/v1/chat/completions"

def check_proxy():
    import requests
    try:
        r = requests.get("http://127.0.0.1:5000/v1/models", timeout=3)
        return r.status_code == 200
    except:
        return False

if not check_proxy():
    print("[WARN] Proxy 127.0.0.1:5000 not running, using direct DeepSeek API")
    LOCAL_CONFIG["api_base_url"] = DIRECT_URL
else:
    print("[OK] Local proxy connected")

# ============================================================
# 三段测试文案 (不同风险等级)
# ============================================================
TEST_CASES = [
    {
        "id": "case-1-医疗擦边",
        "platform": "douyin",
        "content": "这款益生菌真的太牛了！我吃了三天，肠胃问题全好了，连便秘都根治了。市面上最好的肠道产品，没有之一！赶紧下单，现在买一送一，错过等半年！",
    },
    {
        "id": "case-2-金融收益承诺",
        "platform": "douyin",
        "content": "教你一个稳赚不赔的方法，跟着我做副业，零基础也能月入3万！我上个月刚提了辆保时捷，就是靠这个项目。私信我发资料，名额有限只有50个！",
    },
    {
        "id": "case-3-相对正常",
        "platform": "wechat",
        "content": "最近用AI工具做内容生产，效率确实提升了不少。以前写一篇要3小时，现在30分钟搞定初稿，人工再花15分钟润色就可以发布。大家如果有兴趣可以试试这个思路。",
    },
]

# ============================================================
# 执行
# ============================================================
print("=" * 60)
print("RuleGuard Pro — 多维辩论裁决测试")
print("=" * 60)

manager = DebateManager()
all_reports = []

for case in TEST_CASES:
    print(f"\n{'─' * 50}")
    print(f"[TEST] {case['id']} | 平台: {case['platform']}")
    print(f"[CONTENT] 原文: {case['content'][:80]}...")
    print(f"{'─' * 50}")

    result = manager.debate(
        content=case["content"],
        platform=case["platform"],
        content_id=case["id"],
    )

    verdict = result.referee_verdict
    cost = result.cost_breakdown

    print(f"\n  [VERDICT] 裁决: {verdict.final_risk_level.upper()} | 评分: {verdict.overall_score}/100")
    print(f"  [COST] 消耗: {cost['total_tokens']} tokens | ${cost['total_cost_usd']:.6f} (CNY{cost['total_cost_cny']:.4f})")
    print(f"  [RISK] 风险分解: 法律={verdict.risk_breakdown.get('legal','?')} 平台={verdict.risk_breakdown.get('platform_policy','?')} 舆论={verdict.risk_breakdown.get('public_opinion','?')}")

    if verdict.must_fix:
        print(f"  [FIX] 必须修复 ({len(verdict.must_fix)}项):")
        for fix in verdict.must_fix[:3]:
            print(f"     - {fix.get('issue','')} → {fix.get('fix','')} [{fix.get('deadline','')}]")

    if verdict.approved_copy:
        print(f"  [PASS] 通过文案: {verdict.approved_copy[:120]}...")

    print(f"  [SUMMARY] {verdict.debate_summary}")

    all_reports.append(manager.export_full_report(result))

# ============================================================
# 汇总
# ============================================================
total_tokens = sum(r["cost_summary"]["total_tokens"] for r in all_reports)
total_cost = sum(r["cost_summary"]["total_cost_usd"] for r in all_reports)

print(f"\n{'=' * 60}")
print(f"[DONE] 测试完成: {len(TEST_CASES)} 条文案")
print(f"[COST] 总消耗: {total_tokens} tokens | ${total_cost:.6f} (CNY{total_cost * 7.25:.4f})")
print(f"{'=' * 60}")

# 保存完整报告
report_path = "quick_test_results.json"
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(all_reports, f, ensure_ascii=False, indent=2)
print(f"\n[FILE] 完整报告: {report_path}")
