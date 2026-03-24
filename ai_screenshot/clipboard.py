"""Clipboard utilities for copying text, images, and pasting into active apps.

Includes a Wispr Flow-style "quick paste" that types text into
the currently focused application using macOS accessibility APIs.
"""

import subprocess
import sys
import time
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


def paste_text(text: str) -> bool:
    """Paste text into the currently active application.

    Uses the macOS clipboard + Cmd+V keystroke simulation.
    This mimics Wispr Flow's behavior of typing results directly
    into whatever app is focused.
    """
    if sys.platform != "darwin":
        # Fallback: just copy to clipboard
        return copy_text(text)

    # First, save current clipboard
    try:
        import pyperclip
        old_clipboard = pyperclip.paste()
    except Exception:
        old_clipboard = None

    # Copy our text to clipboard
    copy_text(text)

    # Small delay to ensure clipboard is ready
    time.sleep(0.1)

    # Simulate Cmd+V using osascript
    script = '''
    tell application "System Events"
        keystroke "v" using command down
    end tell
    '''
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
    )

    # Restore old clipboard after a brief delay
    if old_clipboard is not None:
        time.sleep(0.3)
        try:
            import pyperclip
            pyperclip.copy(old_clipboard)
        except Exception:
            pass

    return result.returncode == 0


def type_text(text: str, delay: float = 0.02) -> bool:
    """Type text character by character into the active application.

    Slower but more reliable than paste for some applications.
    Uses macOS System Events keystroke.

    Args:
        text: Text to type.
        delay: Delay between keystrokes in seconds.
    """
    if sys.platform != "darwin":
        return False

    # Escape special characters for AppleScript
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')

    script = f'''
    tell application "System Events"
        keystroke "{escaped}"
    end tell
    '''
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
    )
    return result.returncode == 0
