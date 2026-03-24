"""Tests for configuration management."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_screenshot.config import load_config, save_config, ensure_dirs, DEFAULT_CONFIG


def test_load_config_defaults():
    """Loading config without a file should return defaults."""
    with patch("ai_screenshot.config.CONFIG_FILE", Path("/tmp/nonexistent_config.json")):
        config = load_config()
    assert config["max_history"] == 100
    assert "hotkeys" in config


def test_load_config_env_override():
    """Environment variables should override config values."""
    with patch("ai_screenshot.config.CONFIG_FILE", Path("/tmp/nonexistent_config.json")):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-123", "AI_MODEL": "claude-haiku-4-5-20251001"}):
            config = load_config()
    assert config["api_key"] == "test-key-123"
    assert config["ai_model"] == "claude-haiku-4-5-20251001"


def test_save_and_load_config(tmp_path):
    """Saving and loading config should roundtrip correctly."""
    config_file = tmp_path / "config.json"
    test_config = {"ai_model": "test-model", "max_history": 50}

    with patch("ai_screenshot.config.CONFIG_FILE", config_file):
        with patch("ai_screenshot.config.CONFIG_DIR", tmp_path):
            save_config(test_config)
            assert config_file.exists()

            loaded = json.loads(config_file.read_text())
            assert loaded["ai_model"] == "test-model"


def test_ensure_dirs(tmp_path):
    """ensure_dirs should create required directories."""
    config = {"screenshot_dir": str(tmp_path / "screenshots")}
    with patch("ai_screenshot.config.CONFIG_DIR", tmp_path / "config"):
        ensure_dirs(config)
    assert (tmp_path / "screenshots").exists()
