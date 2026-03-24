"""Tests for OCR module (requires tesseract to be installed)."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_extract_text_calls_tesseract(tmp_path):
    """Should call pytesseract with the image."""
    # Create a minimal valid image
    from PIL import Image
    img = Image.new("RGB", (100, 30), color="white")
    img_path = tmp_path / "test.png"
    img.save(img_path)

    mock_tesseract = MagicMock(return_value="Hello World")
    with patch("ai_screenshot.ocr.pytesseract") as mock_module:
        mock_module.image_to_string = mock_tesseract
        from ai_screenshot.ocr import extract_text
        # Re-import to pick up the mock — but since pytesseract is imported
        # inside the function, we need to patch differently

    # The actual function imports pytesseract inside, so let's test differently
    with patch.dict("sys.modules", {"pytesseract": MagicMock()}):
        import sys
        sys.modules["pytesseract"].image_to_string = MagicMock(return_value="  Hello World  ")
        # Since pytesseract is imported at function call time, this should work
        from ai_screenshot import ocr
        # Force reimport
        import importlib
        importlib.reload(ocr)
        result = ocr.extract_text(img_path)
        # The mock returns "  Hello World  " and we strip it
        assert result == "Hello World"
