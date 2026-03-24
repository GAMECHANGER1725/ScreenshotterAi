"""Clipboard utilities for copying text and images."""

import subprocess
import sys
from pathlib import Path


def copy_text(text: str) -> bool:
    """Copy text to the system clipboard.

    Uses pyperclip for cross-platform support.
    Returns True on success.
    """
    import pyperclip
    pyperclip.copy(text)
    return True


def copy_image(image_path: Path) -> bool:
    """Copy an image to the macOS clipboard using osascript.

    Returns True on success.
    """
    if sys.platform != "darwin":
        return False

    script = f'''
    set the clipboard to (read (POSIX file "{image_path}") as «class PNGf»)
    '''
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
    )
    return result.returncode == 0


def get_text() -> str:
    """Get text from the system clipboard."""
    import pyperclip
    return pyperclip.paste()
