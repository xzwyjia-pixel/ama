"""AMA configuration module."""
import json
from pathlib import Path
from typing import Any

CONFIG_DIR = Path(__file__).parent


def load_json(filename: str) -> dict[str, Any]:
    """Load a JSON config file from the config directory."""
    path = CONFIG_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_settings() -> dict[str, Any]:
    """Load global AMA settings."""
    return load_json("settings.json")


def get_models() -> dict[str, Any]:
    """Load model pool configuration."""
    return load_json("models.json")


def get_workers_config() -> dict[str, Any]:
    """Load worker registry configuration."""
    return load_json("workers.json")
