"""Obsidian Vault knowledge base integration.

Optional module — requires Obsidian vault at D:/01_Documents.
Reads/writes notes for long-term agent memory.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_VAULT = Path("D:/01_Documents")


class ObsidianKnowledge:
    """Obsidian vault reader/writer for long-term agent memory.

    Usage:
        kb = ObsidianKnowledge(vault_path="D:/01_Documents")
        results = kb.search("AI agent architecture")
        kb.write_note("ama/task-001.md", content)
    """

    def __init__(self, vault_path: str = "D:/01_Documents") -> None:
        self.vault = Path(vault_path)
        self._enabled = self.vault.exists()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """Full-text search across the Obsidian vault."""
        if not self._enabled:
            logger.warning("Obsidian vault not found at %s", self.vault)
            return []

        results = []
        query_lower = query.lower()
        for md_file in self.vault.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8", errors="ignore")
                if query_lower in content.lower():
                    results.append({
                        "path": str(md_file.relative_to(self.vault)),
                        "title": md_file.stem,
                        "snippet": self._extract_snippet(content, query_lower, 200),
                    })
            except Exception:
                continue
            if len(results) >= max_results:
                break

        return results

    def read_note(self, relative_path: str) -> str | None:
        """Read a note from the vault."""
        if not self._enabled:
            return None
        full_path = self.vault / relative_path
        try:
            return full_path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.error("Failed to read note %s: %s", relative_path, exc)
            return None

    def write_note(self, relative_path: str, content: str) -> bool:
        """Write a note to the vault. Creates parent dirs if needed."""
        if not self._enabled:
            return False
        full_path = self.vault / relative_path
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            logger.info("Note written: %s", relative_path)
            return True
        except Exception as exc:
            logger.error("Failed to write note %s: %s", relative_path, exc)
            return False

    def _extract_snippet(self, content: str, query: str, max_len: int = 200) -> str:
        """Extract a snippet around the first query match."""
        idx = content.lower().find(query)
        if idx < 0:
            return content[:max_len] + "..."
        start = max(0, idx - max_len // 2)
        end = min(len(content), idx + len(query) + max_len // 2)
        snippet = content[start:end]
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(content) else ""
        return f"{prefix}{snippet}{suffix}"
