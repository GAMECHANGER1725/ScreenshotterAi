"""Tests for AI analyzer module."""

from pathlib import Path
from unittest.mock import patch, MagicMock

from ai_screenshot.analyzer import _encode_image, ANALYSIS_PROMPTS


def test_encode_image_png(tmp_path):
    """Should base64-encode a PNG file with correct media type."""
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    data, media_type = _encode_image(img)
    assert media_type == "image/png"
    assert len(data) > 0


def test_encode_image_jpg(tmp_path):
    """Should detect JPEG media type."""
    img = tmp_path / "test.jpg"
    img.write_bytes(b"\xff\xd8\xff" + b"\x00" * 100)
    data, media_type = _encode_image(img)
    assert media_type == "image/jpeg"


def test_analysis_prompts_exist():
    """Should have standard analysis prompts."""
    assert "describe" in ANALYSIS_PROMPTS
    assert "extract_text" in ANALYSIS_PROMPTS
    assert "code" in ANALYSIS_PROMPTS
    assert "summarize" in ANALYSIS_PROMPTS
