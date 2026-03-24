"""Screen watcher — continuous capture mode that monitors for screen changes.

Like Wispr Flow's always-listening mode, this watches the screen and
triggers capture + analysis when significant visual changes are detected.
"""

import sys
import time
import threading
from pathlib import Path
from datetime import datetime

from PIL import Image


class ScreenWatcher:
    """Monitors the screen for visual changes and triggers callbacks.

    Uses periodic screen grabs and pixel-comparison to detect when
    the screen content has changed significantly.
    """

    def __init__(
        self,
        screenshot_dir: str,
        interval: float = 2.0,
        change_threshold: float = 0.05,
        on_change: callable = None,
    ):
        """
        Args:
            screenshot_dir: Where to save captured screenshots.
            interval: Seconds between screen checks.
            change_threshold: Fraction of pixels that must change to trigger (0.0–1.0).
            on_change: Callback(Path) called when a change is detected.
        """
        self.screenshot_dir = Path(screenshot_dir)
        self.interval = interval
        self.change_threshold = change_threshold
        self.on_change = on_change
        self._running = False
        self._thread: threading.Thread | None = None
        self._last_image: Image.Image | None = None
        self._cooldown = 5.0  # Min seconds between triggers
        self._last_trigger = 0.0

    def _grab_screen(self) -> Image.Image | None:
        """Grab the current screen contents."""
        if sys.platform != "darwin":
            # Use Pillow's ImageGrab (works on macOS with extra deps)
            try:
                from PIL import ImageGrab
                return ImageGrab.grab()
            except Exception:
                return None

        # macOS: use screencapture to a temp file
        import subprocess
        import tempfile

        tmp = Path(tempfile.mktemp(suffix=".png"))
        try:
            result = subprocess.run(
                ["screencapture", "-x", "-C", str(tmp)],
                capture_output=True, timeout=5,
            )
            if result.returncode == 0 and tmp.exists():
                img = Image.open(tmp).copy()
                return img
        except Exception:
            pass
        finally:
            tmp.unlink(missing_ok=True)
        return None

    def _compare_images(self, img1: Image.Image, img2: Image.Image) -> float:
        """Compare two images and return the fraction of changed pixels.

        Uses a downscaled comparison for speed.
        """
        # Downscale for fast comparison
        size = (160, 90)
        a = img1.resize(size).convert("L")
        b = img2.resize(size).convert("L")

        pixels_a = list(a.tobytes())
        pixels_b = list(b.tobytes())

        total = len(pixels_a)
        if total == 0:
            return 0.0

        # Count pixels with significant brightness change
        changed = sum(1 for pa, pb in zip(pixels_a, pixels_b) if abs(pa - pb) > 30)
        return changed / total

    def _save_screenshot(self, img: Image.Image) -> Path:
        """Save a captured image to the screenshot directory."""
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.screenshot_dir / f"watch_{ts}.png"
        img.save(path, "PNG")
        return path

    def _watch_loop(self) -> None:
        """Main watch loop — runs in a background thread."""
        while self._running:
            try:
                img = self._grab_screen()
                if img is None:
                    time.sleep(self.interval)
                    continue

                if self._last_image is not None:
                    change = self._compare_images(self._last_image, img)
                    now = time.time()

                    if change > self.change_threshold and (now - self._last_trigger) > self._cooldown:
                        self._last_trigger = now
                        path = self._save_screenshot(img)

                        if self.on_change:
                            # Run callback in a separate thread to not block the watcher
                            threading.Thread(
                                target=self.on_change, args=(path,), daemon=True,
                            ).start()

                self._last_image = img

            except Exception:
                pass

            time.sleep(self.interval)

    def start(self) -> None:
        """Start watching for screen changes."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop watching."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.interval + 1)
            self._thread = None

    @property
    def running(self) -> bool:
        return self._running


class TimedCapture:
    """Capture a screenshot after a countdown delay."""

    def __init__(self, screenshot_dir: str):
        self.screenshot_dir = Path(screenshot_dir)

    def capture_with_delay(
        self,
        delay: float = 3.0,
        mode: str = "fullscreen",
        on_tick: callable = None,
        on_complete: callable = None,
    ) -> None:
        """Start a delayed capture in a background thread.

        Args:
            delay: Seconds to wait before capturing.
            mode: Capture mode (fullscreen, region, window).
            on_tick: Callback(remaining_seconds) called each second.
            on_complete: Callback(Path) called with the screenshot path.
        """
        def run():
            remaining = delay
            while remaining > 0:
                if on_tick:
                    on_tick(remaining)
                time.sleep(1)
                remaining -= 1

            from ai_screenshot.capture import (
                capture_fullscreen, capture_region, capture_window,
            )

            capture_fn = {
                "fullscreen": capture_fullscreen,
                "region": capture_region,
                "window": capture_window,
            }.get(mode, capture_fullscreen)

            path = capture_fn(str(self.screenshot_dir))
            if path and on_complete:
                on_complete(path)

        threading.Thread(target=run, daemon=True).start()
