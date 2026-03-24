"""Tests for smart content detection module."""

from pathlib import Path
from unittest.mock import patch, MagicMock

from PIL import Image

from ai_screenshot.smart import detect_content_type, get_smart_prompt, ContentType


def _create_test_image(tmp_path, brightness=128, size=(800, 600)):
    """Create a test image with specified brightness."""
    img = Image.new("RGB", size, color=(brightness, brightness, brightness))
    path = tmp_path / "test.png"
    img.save(path)
    return path


def test_detect_code_from_text(tmp_path):
    """Should detect code content from OCR text."""
    path = _create_test_image(tmp_path, brightness=30)  # Dark (like a code editor)
    ocr_text = """
    def hello_world():
        print("Hello, World!")
        return True

    if __name__ == "__main__":
        hello_world()
    """
    result = detect_content_type(path, ocr_text)
    assert result == ContentType.CODE


def test_detect_receipt_from_text(tmp_path):
    """Should detect receipt content from OCR text."""
    path = _create_test_image(tmp_path, brightness=240)  # Bright
    ocr_text = """
    STORE RECEIPT
    Item 1       $5.99
    Item 2       $12.50
    Subtotal     $18.49
    Tax          $1.48
    Total        $19.97
    VISA ****1234
    """
    result = detect_content_type(path, ocr_text)
    assert result == ContentType.RECEIPT


def test_detect_document_from_text(tmp_path):
    """Should detect document content from OCR text."""
    path = _create_test_image(tmp_path, brightness=245)
    ocr_text = """
    Dear Sir or Madam,

    Re: Application for the position of Software Engineer

    I am writing to express my interest in the role.
    Section 1: Background
    Section 2: Experience

    Sincerely,
    John Doe
    """
    result = detect_content_type(path, ocr_text)
    assert result == ContentType.DOCUMENT


def test_detect_text_heavy(tmp_path):
    """Should detect text-heavy content."""
    path = _create_test_image(tmp_path)
    ocr_text = "word " * 200  # Lots of text
    result = detect_content_type(path, ocr_text)
    assert result == ContentType.TEXT_HEAVY


def test_detect_unknown_with_no_text(tmp_path):
    """Should return default when no text and no strong image signal."""
    path = _create_test_image(tmp_path, brightness=128)
    result = detect_content_type(path, "")
    # With medium brightness and no text, should default
    assert result in (ContentType.UNKNOWN, ContentType.NATURAL, ContentType.UI)


def test_get_smart_prompt_returns_tuple(tmp_path):
    """get_smart_prompt should return (mode, prompt) tuple."""
    path = _create_test_image(tmp_path)
    mode, prompt = get_smart_prompt(path, "def foo(): return 42")
    assert isinstance(mode, str)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_narrow_image_scores_receipt(tmp_path):
    """A narrow tall image should score higher for receipt detection."""
    path = _create_test_image(tmp_path, brightness=240, size=(300, 800))
    result = detect_content_type(path, "$5.99 total tax receipt")
    assert result == ContentType.RECEIPT
