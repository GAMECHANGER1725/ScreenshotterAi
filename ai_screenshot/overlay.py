"""Floating overlay window for ScreenshotterAI — Wispr Flow-style UI.

Shows a transparent, always-on-top panel that displays capture status,
streaming AI analysis results, and quick-action buttons.
Works on macOS using tkinter (ships with Python).
"""

import sys
import threading
import tkinter as tk
from tkinter import font as tkfont
from pathlib import Path
from typing import Callable


class OverlayWindow:
    """A floating transparent overlay that shows analysis results in real-time."""

    WINDOW_WIDTH = 420
    WINDOW_HEIGHT = 280
    PADDING = 16
    BG_COLOR = "#1a1a2e"
    FG_COLOR = "#e0e0e0"
    ACCENT_COLOR = "#6c63ff"
    SUCCESS_COLOR = "#4ecca3"
    ERROR_COLOR = "#ff6b6b"
    DIM_COLOR = "#7f8c8d"

    def __init__(self):
        self._root: tk.Tk | None = None
        self._thread: threading.Thread | None = None
        self._text_widget: tk.Text | None = None
        self._status_label: tk.Label | None = None
        self._title_label: tk.Label | None = None
        self._action_frame: tk.Frame | None = None
        self._visible = False
        self._on_copy: Callable | None = None
        self._on_paste: Callable | None = None
        self._on_retry: Callable | None = None
        self._current_text = ""
        self._lock = threading.Lock()

    def show(self, title: str = "ScreenshotterAI", status: str = "Capturing...") -> None:
        """Show the overlay window."""
        if self._visible:
            self.update_status(status)
            self.update_title(title)
            return

        self._thread = threading.Thread(target=self._create_window, args=(title, status), daemon=True)
        self._thread.start()

    def _create_window(self, title: str, status: str) -> None:
        """Create and run the overlay window (runs in its own thread)."""
        self._root = tk.Tk()
        self._root.title("ScreenshotterAI")
        self._root.overrideredirect(True)  # No title bar
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", 0.92)

        if sys.platform == "darwin":
            # macOS: transparent background
            self._root.attributes("-transparent", True)
            self._root.config(bg="systemTransparent")

        # Position: bottom-right corner of screen
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        x = screen_w - self.WINDOW_WIDTH - 24
        y = screen_h - self.WINDOW_HEIGHT - 80
        self._root.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}+{x}+{y}")

        # Main frame with rounded appearance
        main = tk.Frame(self._root, bg=self.BG_COLOR, highlightthickness=1,
                        highlightbackground=self.ACCENT_COLOR)
        main.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Header
        header = tk.Frame(main, bg=self.BG_COLOR)
        header.pack(fill=tk.X, padx=self.PADDING, pady=(self.PADDING, 4))

        self._title_label = tk.Label(
            header, text=title, bg=self.BG_COLOR, fg=self.ACCENT_COLOR,
            font=("SF Pro Display", 14, "bold"), anchor="w",
        )
        self._title_label.pack(side=tk.LEFT)

        close_btn = tk.Label(
            header, text="  x  ", bg=self.BG_COLOR, fg=self.DIM_COLOR,
            font=("SF Pro Display", 12), cursor="hand2",
        )
        close_btn.pack(side=tk.RIGHT)
        close_btn.bind("<Button-1>", lambda e: self.hide())

        # Status
        self._status_label = tk.Label(
            main, text=status, bg=self.BG_COLOR, fg=self.SUCCESS_COLOR,
            font=("SF Pro Display", 11), anchor="w",
        )
        self._status_label.pack(fill=tk.X, padx=self.PADDING, pady=(0, 8))

        # Results text area
        text_frame = tk.Frame(main, bg="#0f0f23")
        text_frame.pack(fill=tk.BOTH, expand=True, padx=self.PADDING, pady=(0, 8))

        self._text_widget = tk.Text(
            text_frame, bg="#0f0f23", fg=self.FG_COLOR,
            font=("SF Mono", 11), wrap=tk.WORD,
            borderwidth=0, highlightthickness=0,
            insertbackground=self.FG_COLOR,
            selectbackground=self.ACCENT_COLOR,
        )
        self._text_widget.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._text_widget.config(state=tk.DISABLED)

        # Action buttons
        self._action_frame = tk.Frame(main, bg=self.BG_COLOR)
        self._action_frame.pack(fill=tk.X, padx=self.PADDING, pady=(0, self.PADDING))

        self._add_action_button("Copy", self._handle_copy, self.ACCENT_COLOR)
        self._add_action_button("Paste", self._handle_paste, self.SUCCESS_COLOR)
        self._add_action_button("Retry", self._handle_retry, self.DIM_COLOR)

        # Allow dragging
        self._drag_data = {"x": 0, "y": 0}
        header.bind("<ButtonPress-1>", self._start_drag)
        header.bind("<B1-Motion>", self._on_drag)
        self._title_label.bind("<ButtonPress-1>", self._start_drag)
        self._title_label.bind("<B1-Motion>", self._on_drag)

        self._visible = True
        self._root.mainloop()
        self._visible = False

    def _add_action_button(self, text: str, command: Callable, color: str) -> None:
        btn = tk.Label(
            self._action_frame, text=f"  {text}  ", bg=color, fg="#ffffff",
            font=("SF Pro Display", 10, "bold"), cursor="hand2", padx=8, pady=2,
        )
        btn.pack(side=tk.LEFT, padx=(0, 6))
        btn.bind("<Button-1>", lambda e: command())

    def _start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drag(self, event):
        if self._root:
            x = self._root.winfo_x() + event.x - self._drag_data["x"]
            y = self._root.winfo_y() + event.y - self._drag_data["y"]
            self._root.geometry(f"+{x}+{y}")

    def hide(self) -> None:
        """Hide and destroy the overlay."""
        if self._root:
            try:
                self._root.quit()
                self._root.destroy()
            except Exception:
                pass
            self._root = None
        self._visible = False

    def update_status(self, status: str, color: str | None = None) -> None:
        """Update the status text."""
        if self._root and self._status_label:
            c = color or self.SUCCESS_COLOR
            try:
                self._root.after(0, lambda: self._status_label.config(text=status, fg=c))
            except Exception:
                pass

    def update_title(self, title: str) -> None:
        """Update the title text."""
        if self._root and self._title_label:
            try:
                self._root.after(0, lambda: self._title_label.config(text=title))
            except Exception:
                pass

    def append_text(self, text: str) -> None:
        """Append text to the results area (for streaming)."""
        with self._lock:
            self._current_text += text
        if self._root and self._text_widget:
            try:
                self._root.after(0, self._do_append, text)
            except Exception:
                pass

    def _do_append(self, text: str) -> None:
        if self._text_widget:
            self._text_widget.config(state=tk.NORMAL)
            self._text_widget.insert(tk.END, text)
            self._text_widget.see(tk.END)
            self._text_widget.config(state=tk.DISABLED)

    def set_text(self, text: str) -> None:
        """Replace all text in the results area."""
        with self._lock:
            self._current_text = text
        if self._root and self._text_widget:
            try:
                self._root.after(0, self._do_set_text, text)
            except Exception:
                pass

    def _do_set_text(self, text: str) -> None:
        if self._text_widget:
            self._text_widget.config(state=tk.NORMAL)
            self._text_widget.delete("1.0", tk.END)
            self._text_widget.insert("1.0", text)
            self._text_widget.config(state=tk.DISABLED)

    def get_text(self) -> str:
        """Get the current text from the results area."""
        with self._lock:
            return self._current_text

    def set_callbacks(
        self,
        on_copy: Callable | None = None,
        on_paste: Callable | None = None,
        on_retry: Callable | None = None,
    ) -> None:
        """Set callback functions for the action buttons."""
        self._on_copy = on_copy
        self._on_paste = on_paste
        self._on_retry = on_retry

    def _handle_copy(self) -> None:
        if self._on_copy:
            self._on_copy()
        else:
            from ai_screenshot.clipboard import copy_text
            copy_text(self.get_text())
            self.update_status("Copied to clipboard!", self.SUCCESS_COLOR)

    def _handle_paste(self) -> None:
        if self._on_paste:
            self._on_paste()
        else:
            from ai_screenshot.clipboard import paste_text
            paste_text(self.get_text())
            self.update_status("Pasted!", self.SUCCESS_COLOR)

    def _handle_retry(self) -> None:
        if self._on_retry:
            self._on_retry()

    @property
    def visible(self) -> bool:
        return self._visible


def show_quick_result(text: str, title: str = "ScreenshotterAI", auto_hide: float = 5.0) -> None:
    """Show a quick result overlay that auto-hides after a delay."""
    overlay = OverlayWindow()
    overlay.show(title=title, status="Done")
    overlay.set_text(text)
    if auto_hide > 0 and overlay._root:
        overlay._root.after(int(auto_hide * 1000), overlay.hide)
