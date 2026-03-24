"""Tests for clipboard utilities."""

from unittest.mock import patch, MagicMock, call
import importlib


def test_copy_text():
    """copy_text should call pyperclip.copy."""
    mock_pyperclip = MagicMock()
    with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
        import ai_screenshot.clipboard as clipboard
        importlib.reload(clipboard)
        result = clipboard.copy_text("hello world")
        mock_pyperclip.copy.assert_called_once_with("hello world")
        assert result is True


def test_get_text():
    """get_text should call pyperclip.paste."""
    mock_pyperclip = MagicMock()
    mock_pyperclip.paste.return_value = "clipboard content"
    with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
        import ai_screenshot.clipboard as clipboard
        importlib.reload(clipboard)
        result = clipboard.get_text()
        assert result == "clipboard content"
