"""Tests for screen watcher and timed capture modules."""

import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from PIL import Image

from ai_screenshot.watcher import ScreenWatcher, TimedCapture


def _create_test_image(size=(160, 90), color=(128, 128, 128)):
    return Image.new("RGB", size, color=color)


def test_screen_watcher_compare_identical():
    """Identical images should have 0% change."""
    watcher = ScreenWatcher("/tmp/test_screenshots")
    img = _create_test_image()
    change = watcher._compare_images(img, img)
    assert change == 0.0


def test_screen_watcher_compare_different():
    """Very different images should have high change percentage."""
    watcher = ScreenWatcher("/tmp/test_screenshots")
    img1 = _create_test_image(color=(0, 0, 0))
    img2 = _create_test_image(color=(255, 255, 255))
    change = watcher._compare_images(img1, img2)
    assert change > 0.5


def test_screen_watcher_compare_slight_change():
    """Slight brightness change should be below threshold."""
    watcher = ScreenWatcher("/tmp/test_screenshots")
    img1 = _create_test_image(color=(128, 128, 128))
    img2 = _create_test_image(color=(130, 130, 130))
    change = watcher._compare_images(img1, img2)
    assert change < 0.05


def test_screen_watcher_save_screenshot(tmp_path):
    """Should save a screenshot to the correct directory."""
    watcher = ScreenWatcher(str(tmp_path))
    img = _create_test_image()
    path = watcher._save_screenshot(img)
    assert path.exists()
    assert path.suffix == ".png"
    assert "watch_" in path.name


def test_screen_watcher_start_stop():
    """Should start and stop without errors."""
    watcher = ScreenWatcher("/tmp/test_screenshots", interval=0.1)
    # Mock the screen grab to avoid needing actual display
    watcher._grab_screen = MagicMock(return_value=None)
    watcher.start()
    assert watcher.running
    time.sleep(0.2)
    watcher.stop()
    assert not watcher.running
