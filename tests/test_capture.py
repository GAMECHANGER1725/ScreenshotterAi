"""Tests for screenshot capture module."""

from pathlib import Path

from ai_screenshot.capture import capture_from_file


def test_capture_from_file_valid(tmp_path):
    """capture_from_file should return path for valid image files."""
    img = tmp_path / "test.png"
    img.write_bytes(b"fake png data")
    result = capture_from_file(str(img))
    assert result == img


def test_capture_from_file_invalid_extension(tmp_path):
    """capture_from_file should return None for non-image files."""
    txt = tmp_path / "test.txt"
    txt.write_text("not an image")
    result = capture_from_file(str(txt))
    assert result is None


def test_capture_from_file_nonexistent():
    """capture_from_file should return None for missing files."""
    result = capture_from_file("/tmp/does_not_exist_12345.png")
    assert result is None
