"""Configuration management for ScreenshotterAI."""

import os
import json
from pathlib import Path


DEFAULT_CONFIG = {
    "screenshot_dir": os.path.expanduser("~/ai_screenshots"),
    "ai_model": "claude-sonnet-4-20250514",
    "max_history": 100,
    "hotkeys": {
        "region": "<cmd>+<shift>+s",
        "fullscreen": "<cmd>+<shift>+a",
        "window": "<cmd>+<shift>+w",
    },
    "auto_copy": True,
    "auto_analyze": True,
    "auto_paste": False,
    "smart_mode": True,
    "streaming": True,
    "show_overlay": True,
    "ocr_language": "eng",
    "watch_interval": 2.0,
    "watch_threshold": 0.05,
}

CONFIG_DIR = Path.home() / ".ai_screenshot"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    """Load config from file, falling back to defaults."""
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            user_config = json.load(f)
        config.update(user_config)
    # Env overrides
    if api_key := os.environ.get("ANTHROPIC_API_KEY"):
        config["api_key"] = api_key
    if model := os.environ.get("AI_MODEL"):
        config["ai_model"] = model
    if sdir := os.environ.get("SCREENSHOT_DIR"):
        config["screenshot_dir"] = os.path.expanduser(sdir)
    return config


def save_config(config: dict) -> None:
    """Save config to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def ensure_dirs(config: dict) -> None:
    """Ensure required directories exist."""
    Path(config["screenshot_dir"]).mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
