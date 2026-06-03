"""Media Worker — image/video/audio generation via ComfyUI.

Sends prompts to ComfyUI's REST API (POST /api/prompt) and polls for results.

Reference patterns:
  - ComfyUI server.py: PromptServer with REST + WebSocket API
  - POST /api/prompt → prompt_id, GET /api/history/{id} → output images
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import aiohttp

from ama.workers.base import BaseWorker, TaskInput, TaskOutput, WorkerInfo

logger = logging.getLogger(__name__)

# Default ComfyUI server address
COMFYUI_BASE = "http://127.0.0.1:8188"


class MediaWorker(BaseWorker):
    """Media generation worker — wraps ComfyUI for image/video/audio.

    Connects to a running ComfyUI instance and submits generation prompts.
    Requires ComfyUI to be running: python main.py --listen 0.0.0.0
    """

    worker_type = "media"

    def __init__(self, info: WorkerInfo) -> None:
        super().__init__(info)
        self._base_url = info.default_model if "comfyui" in info.default_model else COMFYUI_BASE
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def execute(self, task: TaskInput) -> TaskOutput:
        t0 = time.monotonic()

        try:
            session = await self._get_session()

            # Step 1: Build ComfyUI prompt JSON
            prompt_json = task.context.get("_comfyui_prompt")
            if prompt_json is None:
                prompt_json = self._build_simple_prompt(task)

            # Step 2: Submit prompt
            prompt_id = await self._submit_prompt(session, prompt_json)
            if not prompt_id:
                return self._build_output(
                    task_id=task.task_id, result=None, success=False,
                    model_used="comfyui/local", start_time=t0,
                    error="Failed to submit prompt to ComfyUI",
                    needs_human=True,
                )

            # Step 3: Poll for completion
            result = await self._wait_for_result(session, prompt_id)

            # Step 4: Return output
            output_paths = result.get("outputs", [])
            success = len(output_paths) > 0

            return self._build_output(
                task_id=task.task_id,
                result={
                    "prompt_id": prompt_id,
                    "outputs": output_paths,
                    "status": result.get("status", "unknown"),
                },
                success=success,
                model_used="comfyui/local",
                tokens_used=0,  # ComfyUI doesn't use LLM tokens
                cost_yuan=0.0,  # Local generation
                start_time=t0,
                confidence=0.9 if success else 0.0,
                error=None if success else "No outputs generated",
            )

        except asyncio.TimeoutError:
            return self._build_output(
                task_id=task.task_id, result=None, success=False,
                model_used="comfyui/local", start_time=t0,
                error=f"ComfyUI generation timed out after {self.info.timeout_seconds}s",
                needs_human=True,
            )
        except Exception as exc:
            logger.error("MediaWorker error: %s", exc)
            return self._build_output(
                task_id=task.task_id, result=None, success=False,
                model_used="comfyui/local", start_time=t0,
                error=str(exc), needs_human=True,
            )

    async def health_check(self) -> bool:
        """Check if ComfyUI server is running."""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base_url}/queue",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                return resp.status == 200
        except Exception:
            return False

    def estimate_cost(self, task: TaskInput) -> float:
        """Local ComfyUI — zero API cost (only electricity)."""
        return 0.0

    # ── ComfyUI API ────────────────────────────────────────────

    async def _submit_prompt(self, session: aiohttp.ClientSession,
                             prompt: dict) -> str | None:
        """Submit a prompt to ComfyUI. Returns prompt_id."""
        body = {
            "prompt": prompt,
            "client_id": f"ama-media-{int(time.time())}",
        }
        async with session.post(
            f"{self._base_url}/api/prompt",
            json=body,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                logger.error("ComfyUI submit error: %s", await resp.text())
                return None
            data = await resp.json()
            prompt_id = data.get("prompt_id")
            logger.info("ComfyUI prompt submitted: %s", prompt_id)
            return prompt_id

    async def _wait_for_result(self, session: aiohttp.ClientSession,
                               prompt_id: str) -> dict[str, Any]:
        """Poll ComfyUI history until the prompt completes or times out."""
        poll_interval = 2.0
        max_wait = self.info.timeout_seconds
        elapsed = 0.0

        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            async with session.get(
                f"{self._base_url}/api/history/{prompt_id}",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    continue
                data = await resp.json()

            if prompt_id in data:
                history_entry = data[prompt_id]
                status = history_entry.get("status", {})
                if status.get("completed", False):
                    # Extract output file paths
                    outputs = []
                    for node_id, node_output in history_entry.get("outputs", {}).items():
                        for img_info in node_output.get("images", []):
                            filename = img_info.get("filename", "")
                            outputs.append(
                                f"{self._base_url}/view?filename={filename}&type=output"
                            )
                    return {"status": "completed", "outputs": outputs}

                elif status.get("status_str") == "error":
                    return {"status": "error", "outputs": []}

            # Update poll interval (adaptive: start fast, slow down)
            poll_interval = min(poll_interval * 1.2, 10.0)

        return {"status": "timeout", "outputs": []}

    # ── Prompt building ─────────────────────────────────────────

    def _build_simple_prompt(self, task: TaskInput) -> dict:
        """Build a simple txt2img ComfyUI prompt JSON.

        This is a minimal default workflow. In production, you'd use
        pre-built workflow templates or let an LLM construct the JSON.
        """
        positive = task.description
        negative = task.context.get("negative_prompt", "bad quality, blurry, distorted")
        seed = task.context.get("seed", 42)
        steps = task.context.get("steps", 20)
        cfg_scale = task.context.get("cfg_scale", 7.0)
        width = task.context.get("width", 512)
        height = task.context.get("height", 512)

        return {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"},
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": positive, "clip": ["1", 1]},
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative, "clip": ["1", 1]},
            },
            "4": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1},
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed, "steps": steps, "cfg": cfg_scale,
                    "sampler_name": "euler", "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0],
                },
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
            },
            "7": {
                "class_type": "PreviewImage",
                "inputs": {"images": ["6", 0]},
            },
        }

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
