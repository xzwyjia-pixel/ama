"""Worker Registry — worker registration, discovery, and lookup.

Reference patterns:
  - Pi Agent agents/*.md YAML frontmatter — declarative worker definitions
  - GenericAgent llmcore.py reload_mykeys() — auto-discovery from config
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

from ama.config import get_workers_config
from ama.workers.base import BaseWorker, WorkerInfo

logger = logging.getLogger(__name__)


class WorkerRegistry:
    """Registry of all available Worker Agents.

    Usage:
        registry = WorkerRegistry()
        registry.load_from_config()        # Load from workers.json
        registry.register("content", ContentWorker(info))
        worker = registry.get_worker("writing")  # finds ContentWorker
    """

    def __init__(self) -> None:
        self._workers: dict[str, BaseWorker] = {}  # worker_type → instance
        self._task_map: dict[str, str] = {}  # task_type → worker_type

    def load_from_config(self) -> None:
        """Load and instantiate all enabled workers from config/workers.json."""
        config = get_workers_config()
        workers_cfg = config.get("workers", {})

        for worker_type, cfg in workers_cfg.items():
            if not cfg.get("enabled", True):
                logger.info("Worker '%s' is disabled, skipping", worker_type)
                continue

            info = WorkerInfo(
                worker_type=worker_type,
                description=cfg.get("description", ""),
                supported_task_types=cfg.get("supported_task_types", []),
                default_model=cfg.get("default_model", ""),
                fallback_model=cfg.get("fallback_model"),
                enabled=cfg.get("enabled", True),
                capability=cfg.get("capability", {}),
                max_retries=cfg.get("max_retries", 3),
                timeout_seconds=cfg.get("timeout_seconds", 120),
            )

            # Try to import and instantiate the worker class
            class_path = cfg.get("class", "")
            try:
                worker = self._instantiate_worker(class_path, info)
                self.register(worker_type, worker)
                logger.info("Worker '%s' loaded: %s", worker_type, info.description)
            except Exception as exc:
                logger.error("Failed to load worker '%s': %s", worker_type, exc)

    def _instantiate_worker(self, class_path: str, info: WorkerInfo) -> BaseWorker:
        """Import and instantiate a worker by its dotted class path."""
        if not class_path:
            raise ValueError(f"No class path for worker '{info.worker_type}'")

        module_path, class_name = class_path.rsplit(".", 1)
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            return cls(info)
        except (ImportError, AttributeError) as e:
            # Fallback: try to import from ama.workers
            if not module_path.startswith("ama."):
                module = importlib.import_module(f"ama.{module_path}")
                cls = getattr(module, class_name)
                return cls(info)
            raise ImportError(f"Cannot import {class_path}: {e}") from e

    def register(self, worker_type: str, worker: BaseWorker) -> None:
        """Register a worker instance."""
        self._workers[worker_type] = worker
        # Build task_type → worker_type mapping
        for task_type in worker.info.supported_task_types:
            self._task_map[task_type] = worker_type

    def unregister(self, worker_type: str) -> bool:
        """Remove a worker from the registry."""
        worker = self._workers.pop(worker_type, None)
        if worker:
            for task_type in worker.info.supported_task_types:
                self._task_map.pop(task_type, None)
            return True
        return False

    def get_worker(self, task_type: str) -> BaseWorker | None:
        """Find the right worker for a task type.

        First tries exact task_type match, then falls back to
        worker_type match.
        """
        # Direct task_type → worker_type mapping
        worker_type = self._task_map.get(task_type)
        if worker_type:
            return self._workers.get(worker_type)

        # Try matching by worker_type itself (e.g., "content" matches "writing")
        for w_type, worker in self._workers.items():
            if task_type in worker.info.supported_task_types:
                return worker

        # Try partial match (e.g., "coding" → code worker,
        # "writing" → content worker)
        partial_map = {
            "code": ["coding", "debugging", "testing", "deployment"],
            "content": ["writing", "translation", "summary", "social_media"],
            "trading": ["market_analysis", "trading_signal", "risk_assessment"],
            "data": ["scraping", "cleaning", "analysis", "reporting"],
            "media": ["image_gen", "video_gen", "audio_gen"],
            "commerce": ["customer_service", "listing", "pricing", "order"],
        }
        for w_type, task_types in partial_map.items():
            if task_type in task_types and w_type in self._workers:
                return self._workers[w_type]

        return None

    def list_workers(self) -> list[BaseWorker]:
        """List all registered workers."""
        return list(self._workers.values())

    def get_enabled_workers(self) -> list[BaseWorker]:
        """List only enabled workers."""
        return [w for w in self._workers.values() if w.info.enabled]

    def health_check_all(self) -> dict[str, bool]:
        """Run health checks on all workers (synchronous wrapper)."""
        import asyncio
        results = {}
        for w_type, worker in self._workers.items():
            try:
                results[w_type] = asyncio.get_event_loop().run_until_complete(
                    worker.health_check(),
                )
            except Exception:
                results[w_type] = False
        return results

    @property
    def worker_count(self) -> int:
        return len(self._workers)

    def __repr__(self) -> str:
        workers = ", ".join(
            f"{w.worker_type}({'✓' if w.info.enabled else '✗'})"
            for w in self._workers.values()
        )
        return f"<WorkerRegistry: {workers}>"
