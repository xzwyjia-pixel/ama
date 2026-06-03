"""Code Worker — software development via Claude Code / Codex CLI.

Wraps the Claude Code CLI as a subprocess for code generation,
debugging, testing, and deployment tasks.

Reference patterns:
  - Claude Code CLI (winget Anthropic.ClaudeCode)
  - Codex CLI (winget OpenAI.Codex)
  - GenericAgent ga.py do_code_run() — subprocess execution with timeout
"""

from __future__ import annotations

import asyncio
import logging
import os
import time

from ama.workers.base import BaseWorker, TaskInput, TaskOutput, WorkerInfo

logger = logging.getLogger(__name__)

# Available code agent CLIs
CODE_AGENTS = {
    "claude": {
        "command": "claude",
        "flags": ["-p", "--output-format", "text"],
        "env_key": None,
    },
    "codex": {
        "command": "codex",
        "flags": ["exec", "--prompt"],
        "env_key": None,
    },
}

# Default to Claude Code
DEFAULT_AGENT = "claude"


class CodeWorker(BaseWorker):
    """Software development worker — wraps CLI agent tools.

    Dispatches coding tasks to Claude Code or Codex CLI,
    capturing output and tracking cost.
    """

    worker_type = "code"

    def __init__(self, info: WorkerInfo) -> None:
        super().__init__(info)
        self._agent = DEFAULT_AGENT

    async def execute(self, task: TaskInput) -> TaskOutput:
        t0 = time.monotonic()
        model_id = task.context.get("_model_id", self.info.default_model)
        agent_cfg = CODE_AGENTS.get(self._agent, CODE_AGENTS[DEFAULT_AGENT])

        prompt = self._build_code_prompt(task)
        cmd = [agent_cfg["command"]] + agent_cfg["flags"] + [prompt]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=task.context.get("cwd") or os.getcwd(),
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.info.timeout_seconds,
            )

            result_text = stdout.decode("utf-8", errors="replace")
            error_text = stderr.decode("utf-8", errors="replace") if stderr else ""

            success = proc.returncode == 0 and len(result_text) > 10
            # Estimate tokens based on character count
            est_tokens = len(prompt) // 4 + len(result_text) // 4
            cost = self._calc_cost(model_id, est_tokens)

            return self._build_output(
                task_id=task.task_id,
                result=result_text.strip() or error_text.strip(),
                success=success,
                model_used=f"{model_id}+{self._agent}",
                tokens_used=est_tokens,
                cost_yuan=cost,
                start_time=t0,
                confidence=0.85 if success else 0.3,
                error=error_text.strip() if not success else None,
                needs_human=not success,
            )

        except asyncio.TimeoutError:
            return self._build_output(
                task_id=task.task_id,
                result=None,
                success=False,
                model_used=model_id,
                start_time=t0,
                error=f"Timeout after {self.info.timeout_seconds}s",
                needs_human=True,
            )
        except FileNotFoundError:
            return self._build_output(
                task_id=task.task_id,
                result=None,
                success=False,
                model_used=model_id,
                start_time=t0,
                error=f"Agent CLI '{agent_cfg['command']}' not found. Ensure Claude Code is installed.",
                needs_human=True,
            )
        except Exception as exc:
            logger.error("CodeWorker error: %s", exc)
            return self._build_output(
                task_id=task.task_id,
                result=None,
                success=False,
                model_used=model_id,
                start_time=t0,
                error=str(exc),
                needs_human=True,
            )

    async def health_check(self) -> bool:
        """Check if Claude Code or Codex CLI is available."""
        for agent_name in ["claude", "codex"]:
            try:
                proc = await asyncio.create_subprocess_exec(
                    agent_name, "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.wait()
                if proc.returncode == 0:
                    self._agent = agent_name
                    return True
            except FileNotFoundError:
                continue
        return False

    def estimate_cost(self, task: TaskInput) -> float:
        model_id = task.context.get("_model_id", self.info.default_model)
        est_tokens = task.complexity * 5000  # Code tasks use more tokens
        rate = 0.000015 if "pro-1m" in model_id else 0.0000015
        return round(est_tokens * rate, 4)

    # ── Internal ──────────────────────────────────────────────

    def _build_code_prompt(self, task: TaskInput) -> str:
        """Build a structured prompt for the code agent CLI."""
        type_instructions = {
            "coding": "Write production-ready code",
            "debugging": "Debug and fix the issue",
            "testing": "Write comprehensive tests",
            "deployment": "Create deployment configuration",
        }
        instruction = type_instructions.get(task.task_type, "Complete this coding task")

        parts = [
            f"{instruction}:\n\n{task.description}",
        ]
        # Add context if provided
        if task.context:
            relevant = {k: v for k, v in task.context.items()
                        if not k.startswith("_") and k != "cwd"}
            if relevant:
                parts.append(f"\nContext: {relevant}")

        return "\n".join(parts)

    def _calc_cost(self, model_id: str, tokens: int) -> float:
        pricing = {
            "deepseek/pro-1m": 0.000015,
            "deepseek/flash": 0.0000015,
            "ollama/qwen2.5:14b": 0.0,
        }
        return round(tokens * pricing.get(model_id, 0.000002), 6)
