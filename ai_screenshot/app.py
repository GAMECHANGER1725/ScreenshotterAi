"""Main menu bar application for ScreenshotterAI (macOS).

Wispr Flow-style menu bar app with overlay UI, streaming analysis,
smart content detection, and continuous capture mode.
"""

import sys
import threading
from datetime import datetime
from pathlib import Path

import rumps

from ai_screenshot.config import load_config, save_config, ensure_dirs
from ai_screenshot.capture import capture_region, capture_fullscreen, capture_window, capture_from_file
from ai_screenshot.ocr import extract_text
from ai_screenshot.analyzer import (
    analyze_screenshot, analyze_screenshot_stream, ANALYSIS_PROMPTS,
)
from ai_screenshot.clipboard import copy_text, copy_image, paste_text
from ai_screenshot.history import History, ScreenshotRecord
from ai_screenshot.hotkeys import HotkeyListener
from ai_screenshot.smart import detect_content_type, get_smart_prompt


class AIScreenshotApp(rumps.App):
    """macOS menu bar app for AI-powered screenshots."""

    def __init__(self):
        super().__init__(
            "ScreenshotterAI",
            title="📸",
            quit_button=None,
        )
        self.config = load_config()
        ensure_dirs(self.config)

        history_file = Path(self.config["screenshot_dir"]) / ".history.json"
        self.history = History(history_file, max_records=self.config["max_history"])

        self._overlay = None
        self._watcher = None

        # Build menu
        self.menu = [
            rumps.MenuItem("Capture Region (⌘⇧S)", callback=self._on_capture_region),
            rumps.MenuItem("Capture Full Screen (⌘⇧A)", callback=self._on_capture_fullscreen),
            rumps.MenuItem("Capture Window (⌘⇧W)", callback=self._on_capture_window),
            rumps.MenuItem("Timed Capture...", callback=self._on_timed_capture),
            None,  # separator
            rumps.MenuItem("Analyze from File...", callback=self._on_analyze_file),
            None,
            self._build_analysis_menu(),
            self._build_smart_menu(),
            None,
            self._build_watch_menu(),
            None,
            rumps.MenuItem("View History", callback=self._on_view_history),
            rumps.MenuItem("Open Screenshot Folder", callback=self._on_open_folder),
            None,
            rumps.MenuItem("Settings...", callback=self._on_settings),
            rumps.MenuItem("Quit", callback=self._on_quit),
        ]

        # Start hotkey listener
        self._hotkey_listener = HotkeyListener()
        hotkeys = self.config.get("hotkeys", {})
        if "region" in hotkeys:
            self._hotkey_listener.register(hotkeys["region"], self._on_capture_region)
        if "fullscreen" in hotkeys:
            self._hotkey_listener.register(hotkeys["fullscreen"], self._on_capture_fullscreen)
        if "window" in hotkeys:
            self._hotkey_listener.register(hotkeys["window"], self._on_capture_window)
        self._hotkey_listener.start()

        self._last_screenshot: Path | None = None
        self._current_prompt = "smart"  # Default to smart mode

    def _build_analysis_menu(self) -> rumps.MenuItem:
        menu = rumps.MenuItem("Analysis Mode")
        # Smart mode first
        smart_item = rumps.MenuItem(
            "smart: Auto-detect content type",
            callback=lambda sender: self._set_analysis_mode("smart"),
        )
        menu.add(smart_item)
        menu.add(None)  # separator
        for key, description in ANALYSIS_PROMPTS.items():
            item = rumps.MenuItem(
                f"{key}: {description[:50]}...",
                callback=lambda sender, k=key: self._set_analysis_mode(k),
            )
            menu.add(item)
        return menu

    def _build_smart_menu(self) -> rumps.MenuItem:
        menu = rumps.MenuItem("Options")
        streaming = rumps.MenuItem(
            "Streaming Results",
            callback=self._toggle_streaming,
        )
        streaming.state = 1 if self.config.get("streaming") else 0
        menu.add(streaming)

        overlay = rumps.MenuItem(
            "Show Overlay",
            callback=self._toggle_overlay,
        )
        overlay.state = 1 if self.config.get("show_overlay") else 0
        menu.add(overlay)

        auto_paste = rumps.MenuItem(
            "Auto-Paste Results",
            callback=self._toggle_auto_paste,
        )
        auto_paste.state = 1 if self.config.get("auto_paste") else 0
        menu.add(auto_paste)

        smart = rumps.MenuItem(
            "Smart Mode (auto-detect)",
            callback=self._toggle_smart,
        )
        smart.state = 1 if self.config.get("smart_mode") else 0
        menu.add(smart)

        return menu

    def _build_watch_menu(self) -> rumps.MenuItem:
        menu = rumps.MenuItem("Continuous Capture")
        menu.add(rumps.MenuItem("Start Watching", callback=self._on_start_watch))
        menu.add(rumps.MenuItem("Stop Watching", callback=self._on_stop_watch))
        return menu

    def _toggle_streaming(self, sender) -> None:
        self.config["streaming"] = not self.config.get("streaming", True)
        sender.state = 1 if self.config["streaming"] else 0
        save_config(self.config)

    def _toggle_overlay(self, sender) -> None:
        self.config["show_overlay"] = not self.config.get("show_overlay", True)
        sender.state = 1 if self.config["show_overlay"] else 0
        save_config(self.config)

    def _toggle_auto_paste(self, sender) -> None:
        self.config["auto_paste"] = not self.config.get("auto_paste", False)
        sender.state = 1 if self.config["auto_paste"] else 0
        save_config(self.config)

    def _toggle_smart(self, sender) -> None:
        self.config["smart_mode"] = not self.config.get("smart_mode", True)
        sender.state = 1 if self.config["smart_mode"] else 0
        save_config(self.config)

    def _set_analysis_mode(self, mode: str) -> None:
        self._current_prompt = mode
        rumps.notification(
            "ScreenshotterAI",
            "Analysis Mode Changed",
            f"Now using: {mode}",
        )

    def _get_prompt_for_image(self, image_path: Path, ocr_text: str = "") -> tuple[str, str]:
        """Get the analysis prompt — uses smart detection if enabled."""
        if self._current_prompt == "smart" and self.config.get("smart_mode", True):
            return get_smart_prompt(image_path, ocr_text)
        else:
            mode = self._current_prompt if self._current_prompt != "smart" else "describe"
            prompt = ANALYSIS_PROMPTS.get(mode, ANALYSIS_PROMPTS["describe"])
            return mode, prompt

    def _process_screenshot(self, screenshot_path: Path, capture_type: str) -> None:
        """Process a captured screenshot — OCR + AI analysis with overlay."""
        self._last_screenshot = screenshot_path
        rumps.notification("ScreenshotterAI", "Captured!", f"Saved to {screenshot_path.name}")

        record = ScreenshotRecord(
            filepath=str(screenshot_path),
            timestamp=datetime.now().isoformat(),
            capture_type=capture_type,
        )

        # Show overlay if enabled
        overlay = None
        if self.config.get("show_overlay"):
            try:
                from ai_screenshot.overlay import OverlayWindow
                overlay = OverlayWindow()
                overlay.show(title=f"ScreenshotterAI — {capture_type}", status="Analyzing...")
            except Exception:
                overlay = None

        def process():
            try:
                # OCR first
                ocr_text = extract_text(screenshot_path, self.config.get("ocr_language", "eng"))
                record.ocr_text = ocr_text

                if self.config.get("auto_analyze") and self.config.get("api_key"):
                    mode, prompt = self._get_prompt_for_image(screenshot_path, ocr_text)

                    if overlay:
                        overlay.update_status(f"Analyzing ({mode})...")

                    # Use streaming if enabled
                    if self.config.get("streaming") and overlay:
                        analysis = analyze_screenshot_stream(
                            screenshot_path,
                            prompt=prompt,
                            model=self.config.get("ai_model", "claude-sonnet-4-20250514"),
                            api_key=self.config.get("api_key"),
                            on_chunk=lambda chunk: overlay.append_text(chunk),
                        )
                    else:
                        analysis = analyze_screenshot(
                            screenshot_path,
                            prompt=prompt,
                            model=self.config.get("ai_model", "claude-sonnet-4-20250514"),
                            api_key=self.config.get("api_key"),
                        )
                        if overlay:
                            overlay.set_text(analysis)

                    record.ai_analysis = analysis

                    if overlay:
                        overlay.update_status(f"Done ({mode})")

                    # Auto-paste or auto-copy
                    if self.config.get("auto_paste"):
                        paste_text(analysis)
                        rumps.notification("ScreenshotterAI", "Analysis Complete", "Result pasted!")
                    elif self.config.get("auto_copy"):
                        copy_text(analysis)
                        rumps.notification("ScreenshotterAI", "Analysis Complete", "Result copied to clipboard!")
                    else:
                        rumps.notification("ScreenshotterAI", "Analysis Complete", analysis[:100])

                elif self.config.get("auto_copy") and ocr_text:
                    copy_text(ocr_text)
                    if overlay:
                        overlay.set_text(ocr_text)
                        overlay.update_status("OCR Complete")
                    rumps.notification("ScreenshotterAI", "OCR Complete", "Text copied to clipboard!")

            except Exception as e:
                if overlay:
                    overlay.update_status(f"Error: {str(e)[:60]}", "#ff6b6b")
                rumps.notification("ScreenshotterAI", "Error", str(e)[:100])
            finally:
                self.history.add(record)

        threading.Thread(target=process, daemon=True).start()

    def _on_capture_region(self, sender=None) -> None:
        path = capture_region(self.config["screenshot_dir"])
        if path:
            self._process_screenshot(path, "region")

    def _on_capture_fullscreen(self, sender=None) -> None:
        path = capture_fullscreen(self.config["screenshot_dir"])
        if path:
            self._process_screenshot(path, "fullscreen")

    def _on_capture_window(self, sender=None) -> None:
        path = capture_window(self.config["screenshot_dir"])
        if path:
            self._process_screenshot(path, "window")

    def _on_timed_capture(self, sender=None) -> None:
        """Capture with a countdown timer."""
        response = rumps.Window(
            title="Timed Capture",
            message="Delay in seconds:",
            default_text="3",
            ok="Start",
            cancel="Cancel",
        ).run()
        if response.clicked:
            try:
                delay = float(response.text)
            except ValueError:
                delay = 3.0

            from ai_screenshot.watcher import TimedCapture
            tc = TimedCapture(self.config["screenshot_dir"])
            tc.capture_with_delay(
                delay=delay,
                mode="fullscreen",
                on_tick=lambda r: rumps.notification("ScreenshotterAI", "Timer", f"{r:.0f}s..."),
                on_complete=lambda p: self._process_screenshot(p, "timed"),
            )

    def _on_start_watch(self, sender=None) -> None:
        """Start continuous screen watching."""
        if self._watcher and self._watcher.running:
            rumps.notification("ScreenshotterAI", "Watch Mode", "Already watching!")
            return

        from ai_screenshot.watcher import ScreenWatcher
        self._watcher = ScreenWatcher(
            screenshot_dir=self.config["screenshot_dir"],
            interval=self.config.get("watch_interval", 2.0),
            change_threshold=self.config.get("watch_threshold", 0.05),
            on_change=lambda path: self._process_screenshot(path, "watch"),
        )
        self._watcher.start()
        self.title = "📸👁"
        rumps.notification("ScreenshotterAI", "Watch Mode", "Started watching for screen changes!")

    def _on_stop_watch(self, sender=None) -> None:
        """Stop continuous screen watching."""
        if self._watcher:
            self._watcher.stop()
            self._watcher = None
        self.title = "📸"
        rumps.notification("ScreenshotterAI", "Watch Mode", "Stopped watching.")

    def _on_analyze_file(self, sender=None) -> None:
        """Open a file dialog to select an image for analysis."""
        import subprocess
        result = subprocess.run(
            [
                "osascript", "-e",
                'POSIX path of (choose file of type {"png", "jpg", "jpeg", "bmp", "tiff"} with prompt "Select an image to analyze")',
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            file_path = result.stdout.strip()
            path = capture_from_file(file_path)
            if path:
                self._process_screenshot(path, "file")

    def _on_view_history(self, sender=None) -> None:
        records = self.history.get_recent(10)
        if not records:
            rumps.notification("ScreenshotterAI", "History", "No screenshots yet.")
            return

        lines = []
        for r in records:
            ts = r.timestamp[:19]
            preview = (r.ai_analysis or r.ocr_text)[:60]
            lines.append(f"[{ts}] {r.capture_type}: {preview}")

        rumps.alert(
            title="Recent Screenshots",
            message="\n".join(lines),
        )

    def _on_open_folder(self, sender=None) -> None:
        import subprocess
        subprocess.run(["open", self.config["screenshot_dir"]])

    def _on_settings(self, sender=None) -> None:
        response = rumps.Window(
            title="ScreenshotterAI Settings",
            message="Enter your Anthropic API key:",
            default_text=self.config.get("api_key", ""),
            ok="Save",
            cancel="Cancel",
        ).run()
        if response.clicked:
            self.config["api_key"] = response.text
            save_config(self.config)
            rumps.notification("ScreenshotterAI", "Settings", "API key saved!")

    def _on_quit(self, sender=None) -> None:
        if self._watcher:
            self._watcher.stop()
        if self._overlay:
            self._overlay.hide()
        self._hotkey_listener.stop()
        rumps.quit_application()


def main():
    """Entry point for the menu bar app."""
    if sys.platform != "darwin":
        print("ScreenshotterAI requires macOS.")
        print("For testing on other platforms, use the CLI: python -m ai_screenshot.cli")
        sys.exit(1)

    app = AIScreenshotApp()
    app.run()


if __name__ == "__main__":
    main()
