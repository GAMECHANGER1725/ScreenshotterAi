"""Screenshot capture for macOS using the native screencapture command."""

import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _output_path(screenshot_dir: str, prefix: str = "screenshot") -> Path:
    """Generate a unique output path for a screenshot."""
    d = Path(screenshot_dir)
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{prefix}_{_timestamp()}.png"


def capture_region(screenshot_dir: str) -> Path | None:
    """Capture a selected screen region (interactive crosshair selection).

    Uses macOS `screencapture -i` which lets the user drag-select a region.
    Returns the path to the saved screenshot, or None if cancelled.
    """
    if sys.platform != "darwin":
        raise RuntimeError("Region capture requires macOS (screencapture)")

    out = _output_path(screenshot_dir, "region")
    result = subprocess.run(
        ["screencapture", "-i", "-x", str(out)],
        capture_output=True,
    )
    if result.returncode != 0 or not out.exists():
        return None
    return out


def capture_fullscreen(screenshot_dir: str) -> Path | None:
    """Capture the entire screen.

    Uses macOS `screencapture` (no -i flag) for a full-screen grab.
    Returns the path to the saved screenshot.
    """
    if sys.platform != "darwin":
        raise RuntimeError("Fullscreen capture requires macOS (screencapture)")

    out = _output_path(screenshot_dir, "fullscreen")
    result = subprocess.run(
        ["screencapture", "-x", str(out)],
        capture_output=True,
    )
    if result.returncode != 0 or not out.exists():
        return None
    return out


def capture_window(screenshot_dir: str) -> Path | None:
    """Capture the frontmost window.

    Uses macOS `screencapture -w` for window capture.
    Returns the path to the saved screenshot.
    """
    if sys.platform != "darwin":
        raise RuntimeError("Window capture requires macOS (screencapture)")

    out = _output_path(screenshot_dir, "window")
    result = subprocess.run(
        ["screencapture", "-w", "-x", str(out)],
        capture_output=True,
    )
    if result.returncode != 0 or not out.exists():
        return None
    return out


def capture_from_file(file_path: str) -> Path | None:
    """Load an existing image file (for testing with Kaggle datasets etc.)."""
    p = Path(file_path)
    if p.exists() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
        return p
    return None
