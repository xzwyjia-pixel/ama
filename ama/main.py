"""AMA CLI Entry Point — command-line interface for the Agent-Management-Agent.

Usage:
    python -m ama.main "task description"    # Submit a task
    python -m ama.main --interactive          # Interactive mode
    python -m ama.main --status               # Show system status
    python -m ama.main --report               # Daily cost report
    python -m ama.main --test                 # Run self-test
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime

from ama.config import get_settings
from ama.core.manager import ManagerAgent
from ama.workers.base import TaskInput, TaskPriority
from ama.workers.registry import WorkerRegistry

# ── Force UTF-8 on Windows ────────────────────────────────────
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Encoding-safe symbols ──────────────────────────────────────
_ICON_OK = "[OK]"
_ICON_FAIL = "[FAIL]"
_ICON_WARN = "[WARN]"
_YUAN = "CNY"

# ── Logging setup ────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(
            "c:/Users/25454/业务中控台/ama/logs/ama.log",
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("ama")


# ── Worker factory (manual registration — no dynamic imports for now) ─

def _create_registry() -> WorkerRegistry:
    """Create and populate a worker registry with available workers."""
    from ama.workers.base import WorkerInfo
    from ama.workers.content import ContentWorker
    from ama.workers.code import CodeWorker
    from ama.workers.commerce import CommerceWorker

    registry = WorkerRegistry()

    # Content worker
    registry.register("content", ContentWorker(WorkerInfo(
        worker_type="content",
        description="Content creation — writing, translation, social media",
        supported_task_types=["writing", "translation", "summary", "social_media"],
        default_model="deepseek/flash",
        fallback_model="ollama/qwen2.5:14b",
        capability={"creativity": 8, "accuracy": 6, "speed": 7},
    )))

    # Code worker
    registry.register("code", CodeWorker(WorkerInfo(
        worker_type="code",
        description="Software development via Claude Code CLI",
        supported_task_types=["coding", "debugging", "testing", "deployment"],
        default_model="deepseek/pro-1m",
        fallback_model="deepseek/flash",
        capability={"creativity": 5, "accuracy": 9, "speed": 4},
    )))

    # Commerce worker
    registry.register("commerce", CommerceWorker(WorkerInfo(
        worker_type="commerce",
        description="AI shop operations — listing, pricing, customer service",
        supported_task_types=["listing", "pricing", "customer_service", "order"],
        default_model="deepseek/flash",
        fallback_model="ollama/qwen2.5:14b",
        capability={"commerce": 9, "customer_service": 7, "speed": 8},
        timeout_seconds=120,
    )))

    logger.info("Registry created with %d workers", registry.worker_count)
    return registry


# ── CLI Commands ─────────────────────────────────────────────

async def cmd_submit(manager: ManagerAgent, description: str) -> None:
    """Submit a task and wait for result."""
    # Auto-detect task type from keywords
    task_type = _detect_task_type(description)
    complexity = _estimate_complexity(description)

    print(f"\n📋 任务类型: {task_type} | 复杂度: {complexity}/10")
    print(f"📝 描述: {description[:100]}{'...' if len(description) > 100 else ''}")

    task_id = await manager.submit(
        task_type=task_type,
        description=description,
        complexity=complexity,
    )

    print(f"\n⏳ 处理中... (task_id: {task_id})")

    try:
        output = await manager.wait(task_id, timeout=300)
        _print_result(output)
    except asyncio.TimeoutError:
        print(f"\n⏰ 任务超时 (task_id: {task_id})")
    except KeyboardInterrupt:
        print("\n⚠️  已取消")


async def cmd_status(manager: ManagerAgent) -> None:
    """Show system status."""
    status = manager.system_status()
    print("\n===== AMA 系统状态 =====")
    print(f"版本: {status['version']}")
    print(f"运行中: {status['running']}")
    print(f"\n--- 队列 ---")
    print(f"待处理: {status['queue']['pending']}")
    print(f"总数: {status['queue']['total']}")
    print(f"\n--- 预算 ---")
    print(f"今日预算: ¥{status['budget']['daily']:.2f}")
    print(f"已花费: ¥{status['budget']['spent']:.4f}")
    print(f"剩余: ¥{status['budget']['remaining']:.4f}")
    print(f"使用率: {status['budget']['percent']}%")
    if status['budget']['alert']:
        print("⚠️  预算警报已触发!")
    print(f"\n--- 路由统计 ---")
    print(f"总路由: {status['router']['total_routes']}")
    print(f"降级次数: {status['router']['fallbacks']}")
    print(f"模型分布: {status['router']['by_model']}")
    print(f"\n--- Workers ---")
    print(f"活跃: {status['workers']}")


async def cmd_report(manager: ManagerAgent) -> None:
    """Show daily cost report."""
    report = manager.daily_report()
    print(f"\n===== 日报 {report.date} =====")
    print(f"任务: {report.total_tasks} (成功: {report.successful_tasks}, 失败: {report.failed_tasks})")
    print(f"总Token: {report.total_tokens:,}")
    print(f"总花费: ¥{report.total_cost_yuan:.4f}")
    if report.by_worker:
        print("\n按Worker:")
        for w, s in report.by_worker.items():
            print(f"  {w}: {s['tasks']}任务 ¥{s['cost_yuan']:.4f} {s['tokens']}tokens")
    if report.by_model:
        print("\n按模型:")
        for m, s in report.by_model.items():
            print(f"  {m}: {s['tasks']}任务 ¥{s['cost_yuan']:.4f}")

    # Recent activity
    print("\n--- 最近活动 ---")
    for r in manager.recent_activity(10):
        status_icon = "✅" if r["success"] else "❌"
        print(f"  {status_icon} {r['task_id'][:12]}... [{r['worker_type']}] "
              f"¥{r['cost_yuan']:.4f} — {r['timestamp']}")


async def cmd_interactive(manager: ManagerAgent) -> None:
    """Run interactive task submission loop."""
    print("\n===== AMA 交互模式 =====")
    print("输入任务描述 (或 /status, /report, /quit)")
    print("示例: '用中文写一篇500字关于AI Agent的博客'\n")

    while True:
        try:
            user_input = input("AMA> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        if user_input in ("/quit", "/q", "/exit"):
            break
        elif user_input == "/status":
            await cmd_status(manager)
        elif user_input == "/report":
            await cmd_report(manager)
        elif user_input.startswith("/"):
            print(f"未知命令: {user_input}")
        else:
            await cmd_submit(manager, user_input)

    print("\n👋 再见!")


async def cmd_test(manager: ManagerAgent) -> None:
    """Run a quick self-test."""
    print("\n===== AMA 自检 =====")

    # Test 1: Configuration
    try:
        settings = get_settings()
        print(f"✅ 配置: v{settings.get('ama_version', '?')}")
    except Exception as e:
        print(f"❌ 配置: {e}")
        return

    # Test 2: Model Router
    router = manager.model_router
    print(f"✅ 模型路由器: {len(router.models)}个模型 — "
          f"{', '.join(router.models.keys())}")

    # Test 3: Worker Health
    print("检查Worker健康状态...")
    for worker in manager.registry.list_workers():
        try:
            healthy = await worker.health_check()
            icon = "✅" if healthy else "⚠️"
            print(f"  {icon} {worker.worker_type}: {'健康' if healthy else '不可用'}")
        except Exception as e:
            print(f"  ❌ {worker.worker_type}: {e}")

    # Test 4: Database
    try:
        report = manager.daily_report()
        print(f"✅ 数据库: {report.total_tasks}条历史记录")
    except Exception as e:
        print(f"❌ 数据库: {e}")

    # Test 5: Budget
    budget = manager.cost_tracker.check_budget()
    print(f"✅ 预算: ¥{budget.spent_today_yuan:.4f} / ¥{budget.daily_budget_yuan:.2f} "
          f"({budget.percent_used}%)")

    print("\n自检完成!")


# ── Helpers ──────────────────────────────────────────────────

def _detect_task_type(description: str) -> str:
    """Detect task type from Chinese/English keywords."""
    desc_lower = description.lower()
    keywords = {
        "writing": ["写", "文章", "博客", "blog", "write", "article", "文案", "copywriting"],
        "translation": ["翻译", "translate", "译", "localization"],
        "summary": ["摘要", "总结", "概括", "summarize", "summary", "tl;dr"],
        "social_media": ["小红书", "抖音", "微博", "公众号", "tweet", "post", "社媒"],
        "coding": ["代码", "编程", "开发", "code", "program", "develop", "函数", "function"],
        "debugging": ["修复", "bug", "错误", "debug", "fix", "调试"],
        "testing": ["测试", "test", "单元测试", "unit test"],
        "market_analysis": ["股票", "分析", "行情", "stock", "market", "走势"],
        "trading_signal": ["交易", "信号", "买卖", "trade", "signal", "buy", "sell"],
        "image_gen": ["生成图", "画", "图片", "image", "generate", "draw"],
    }
    for task_type, kws in keywords.items():
        if any(kw in desc_lower for kw in kws):
            # Map to worker category
            if task_type in ("writing", "translation", "summary", "social_media"):
                return task_type
            elif task_type in ("coding", "debugging", "testing"):
                return task_type
            elif task_type in ("market_analysis", "trading_signal"):
                return task_type
            elif task_type in ("image_gen",):
                return task_type
    return "writing"  # default


def _estimate_complexity(description: str) -> int:
    """Quick complexity estimate based on description length and keywords."""
    score = 3
    if len(description) > 100:
        score += 1
    if len(description) > 500:
        score += 1
    if any(kw in description for kw in ["架构", "系统", "system", "architecture", "复杂"]):
        score += 2
    if any(kw in description for kw in ["简单", "simple", "快速", "quick"]):
        score -= 1
    return max(1, min(10, score))


def _print_result(output) -> None:
    """Pretty-print a task output."""
    print(f"\n{'='*50}")
    if output.success:
        print(f"✅ 任务成功 | "
              f"模型: {output.model_used} | "
              f"耗时: {output.duration_ms}ms | "
              f"花费: ¥{output.cost_yuan:.4f}")
        print(f"{'='*50}")
        result_str = str(output.result)
        if len(result_str) > 500:
            print(result_str[:500])
            print(f"... (总计 {len(result_str)} 字符)")
        else:
            print(result_str)
    else:
        print(f"❌ 任务失败 | 错误: {output.error}")
    print(f"{'='*50}\n")


# ── Pipeline Commands ─────────────────────────────────────────

async def cmd_pipeline(manager: ManagerAgent, args: list[str]) -> None:
    """Run revenue pipelines (shop / content)."""
    pipeline_type = args[0] if args else "shop"

    if pipeline_type == "shop":
        await _run_shop_pipeline(manager)
    elif pipeline_type == "content":
        await _run_content_pipeline(manager, args[1:])
    else:
        print(f"Unknown pipeline: {pipeline_type}. Use 'shop' or 'content'.")


async def _run_shop_pipeline(manager: ManagerAgent) -> None:
    """Run the shop automation pipeline."""
    from ama.pipelines.shop import ShopPipeline

    import aiohttp, os
    api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN",
                             os.environ.get("DEEPSEEK_API_KEY", ""))

    async def llm_call(prompt: str, json_mode: bool = False) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        body = {
            "model": "deepseek-v4-flash",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.deepseek.com/v1/chat/completions",
                json=body, headers=headers,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    pipeline = ShopPipeline(llm_call_func=llm_call if api_key else None)
    results = await pipeline.generate_all()
    out = pipeline.export("c:/Users/25454/业务中控台/ama/output/listings")
    print(f"\n📁 输出目录: {out}")
    print(f"📄 可复制文案: {out}/all_listings.md")


async def _run_content_pipeline(
    manager: ManagerAgent, args: list[str],
) -> None:
    """Run the content operations pipeline."""
    from ama.pipelines.content import ContentPipeline, TOPIC_POOL

    import aiohttp, os
    api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN",
                             os.environ.get("DEEPSEEK_API_KEY", ""))

    async def llm_call(prompt: str, json_mode: bool = False) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        body = {
            "model": "deepseek-v4-flash",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.deepseek.com/v1/chat/completions",
                json=body, headers=headers,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    pipeline = ContentPipeline(llm_call_func=llm_call if api_key else None)

    # Parse --topic and --count from args
    topic = None
    count = 1
    for i, arg in enumerate(args):
        if arg == "--topic" and i + 1 < len(args):
            topic = args[i + 1]
        elif arg == "--count" and i + 1 < len(args):
            count = int(args[i + 1])

    if topic:
        piece = await pipeline.create_piece(topic, "wechat_article")
        out = pipeline.export_piece(piece, "c:/Users/25454/业务中控台/ama/output/content")
        print(f"\n📁 输出: {out}")
    else:
        topics = TOPIC_POOL[:count]
        pieces = await pipeline.batch_create(topics, "wechat_article")
        pipeline.export_all("c:/Users/25454/业务中控台/ama/output/content")
        print(f"\n📁 已生成 {len(pieces)} 篇内容 → ama/output/content/")


# ── Dashboard Command ─────────────────────────────────────────

async def cmd_dashboard(manager: ManagerAgent, args: list[str]) -> None:
    """Start the web dashboard."""
    from ama.dashboard import start_dashboard

    port = 8080
    for i, arg in enumerate(args):
        if arg == "--port" and i + 1 < len(args):
            port = int(args[i + 1])

    server = start_dashboard(manager, port=port)

    print("Dashboard running. Press Ctrl+C to stop.")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        server.shutdown()
        print("\nDashboard stopped.")


# ── Schedule Command ──────────────────────────────────────────

async def cmd_schedule(manager: ManagerAgent, args: list[str]) -> None:
    """Start the task scheduler."""
    from ama.scheduler import TaskScheduler

    async def execute_task(task):
        """Execute a scheduled task through the Manager."""
        from ama.scheduler import ScheduledTask
        action = task.action
        if action == "report":
            await cmd_report(manager)
        elif action == "health":
            await cmd_test(manager)
        elif action == "pipeline":
            pipeline_type = task.action_params.get("pipeline", "shop")
            if pipeline_type == "shop":
                await _run_shop_pipeline(manager)
            elif pipeline_type == "content":
                await _run_content_pipeline(manager, [])
        else:
            print(f"Unknown action: {action}")

    scheduler = TaskScheduler(execute_func=execute_task)
    scheduler.load_builtins()
    scheduler.load_from_db()

    run_once = "--once" in args
    print(f"\n  Task Scheduler ({'run-once' if run_once else 'continuous'})")
    print(f"  {len(scheduler._tasks)} tasks loaded:")
    for t in scheduler._tasks.values():
        print(f"    - {t.name} (next: {t.next_run})")

    try:
        await scheduler.start(run_once=run_once)
    except KeyboardInterrupt:
        scheduler.stop()
        print("\nScheduler stopped.")


# ── Main ─────────────────────────────────────────────────────

async def main() -> None:
    """Main CLI entry point."""
    settings = get_settings()

    # Create manager
    manager = ManagerAgent(settings=settings)
    registry = _create_registry()
    manager.register_workers(registry)

    # Parse args
    args = sys.argv[1:]

    if not args:
        # Default: interactive mode
        await cmd_interactive(manager)
    elif args[0] == "--interactive" or args[0] == "-i":
        await cmd_interactive(manager)
    elif args[0] == "--status" or args[0] == "-s":
        await cmd_status(manager)
    elif args[0] == "--report" or args[0] == "-r":
        await cmd_report(manager)
    elif args[0] == "--test" or args[0] == "-t":
        await cmd_test(manager)
    elif args[0] == "--dashboard" or args[0] == "-d":
        await cmd_dashboard(manager, args[1:])
    elif args[0] == "--pipeline":
        await cmd_pipeline(manager, args[1:])
    elif args[0] == "--schedule":
        await cmd_schedule(manager, args[1:])
    else:
        # Treat all arguments as a task description
        description = " ".join(args)
        await cmd_submit(manager, description)

    manager.stop()
    # Cleanup worker sessions
    for worker in registry.list_workers():
        if hasattr(worker, "close"):
            try:
                await worker.close()
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(main())
