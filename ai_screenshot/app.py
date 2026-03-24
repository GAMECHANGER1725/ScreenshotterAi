"""Main menu bar application for AI Screenshot Tool (macOS)."""

import sys
import threading
from datetime import datetime
from pathlib import Path

import rumps

from ai_screenshot.config import load_config, save_config, ensure_dirs
from ai_screenshot.capture import capture_region, capture_fullscreen, capture_window, capture_from_file
from ai_screenshot.ocr import extract_text
from ai_screenshot.analyzer import analyze_screenshot, ANALYSIS_PROMPTS
from ai_screenshot.clipboard import copy_text, copy_image
from ai_screenshot.history import History, ScreenshotRecord
from ai_screenshot.hotkeys import HotkeyListener


class AIScreenshotApp(rumps.App):
    """macOS menu bar app for AI-powered screenshots."""

    def __init__(self):
        super().__init__(
            "AI Screenshot",
            title="📸",
            quit_button=None,
        )
        self.config = load_config()
        ensure_dirs(self.config)

        history_file = Path(self.config["screenshot_dir"]) / ".history.json"
        self.history = History(history_file, max_records=self.config["max_history"])

        # Build menu
        self.menu = [
            rumps.MenuItem("Capture Region (⌘⇧S)", callback=self._on_capture_region),
            rumps.MenuItem("Capture Full Screen (⌘⇧A)", callback=self._on_capture_fullscreen),
            rumps.MenuItem("Capture Window (⌘⇧W)", callback=self._on_capture_window),
            None,  # separator
            rumps.MenuItem("Analyze from File...", callback=self._on_analyze_file),
            None,
            self._build_analysis_menu(),
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
        self._current_prompt = "describe"

    def _build_analysis_menu(self) -> rumps.MenuItem:
        menu = rumps.MenuItem("Analysis Mode")
        for key, description in ANALYSIS_PROMPTS.items():
            item = rumps.MenuItem(
                f"{key}: {description[:50]}...",
                callback=lambda sender, k=key: self._set_analysis_mode(k),
            )
            menu.add(item)
        return menu

    def _set_analysis_mode(self, mode: str) -> None:
        self._current_prompt = mode
        rumps.notification(
            "AI Screenshot",
            "Analysis Mode Changed",
            f"Now using: {mode}",
        )

    def _process_screenshot(self, screenshot_path: Path, capture_type: str) -> None:
        """Process a captured screenshot — OCR + AI analysis."""
        self._last_screenshot = screenshot_path
        rumps.notification("AI Screenshot", "Captured!", f"Saved to {screenshot_path.name}")

        record = ScreenshotRecord(
            filepath=str(screenshot_path),
            timestamp=datetime.now().isoformat(),
            capture_type=capture_type,
        )

        # OCR in background
        def process():
            try:
                ocr_text = extract_text(screenshot_path, self.config.get("ocr_language", "eng"))
                record.ocr_text = ocr_text

                if self.config.get("auto_analyze") and self.config.get("api_key"):
                    prompt = ANALYSIS_PROMPTS.get(self._current_prompt, ANALYSIS_PROMPTS["describe"])
                    analysis = analyze_screenshot(
                        screenshot_path,
                        prompt=prompt,
                        model=self.config.get("ai_model", "claude-sonnet-4-20250514"),
                        api_key=self.config.get("api_key"),
                    )
                    record.ai_analysis = analysis

                    if self.config.get("auto_copy"):
                        copy_text(analysis)
                        rumps.notification("AI Screenshot", "Analysis Complete", "Result copied to clipboard!")
                    else:
                        rumps.notification("AI Screenshot", "Analysis Complete", analysis[:100])
                elif self.config.get("auto_copy") and ocr_text:
                    copy_text(ocr_text)
                    rumps.notification("AI Screenshot", "OCR Complete", "Text copied to clipboard!")

            except Exception as e:
                rumps.notification("AI Screenshot", "Error", str(e)[:100])
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
            rumps.notification("AI Screenshot", "History", "No screenshots yet.")
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
            title="AI Screenshot Settings",
            message="Enter your Anthropic API key:",
            default_text=self.config.get("api_key", ""),
            ok="Save",
            cancel="Cancel",
        ).run()
        if response.clicked:
            self.config["api_key"] = response.text
            save_config(self.config)
            rumps.notification("AI Screenshot", "Settings", "API key saved!")

    def _on_quit(self, sender=None) -> None:
        self._hotkey_listener.stop()
        rumps.quit_application()


def main():
    """Entry point for the menu bar app."""
    if sys.platform != "darwin":
        print("AI Screenshot Tool requires macOS.")
        print("For testing on other platforms, use the CLI: python -m ai_screenshot.cli")
        sys.exit(1)

    app = AIScreenshotApp()
    app.run()


if __name__ == "__main__":
    main()
