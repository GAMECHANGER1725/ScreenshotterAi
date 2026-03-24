"""Global hotkey listener using pynput."""

import threading
from typing import Callable

from pynput import keyboard


class HotkeyListener:
    """Listens for global hotkey combinations and triggers callbacks."""

    def __init__(self):
        self._hotkeys: dict[str, Callable] = {}
        self._listener: keyboard.GlobalHotKeys | None = None
        self._thread: threading.Thread | None = None

    def register(self, hotkey: str, callback: Callable) -> None:
        """Register a hotkey combination with a callback.

        Args:
            hotkey: Hotkey string like '<cmd>+<shift>+s'
            callback: Function to call when hotkey is pressed.
        """
        self._hotkeys[hotkey] = callback

    def start(self) -> None:
        """Start listening for hotkeys in a background thread."""
        if not self._hotkeys:
            return

        self._listener = keyboard.GlobalHotKeys(self._hotkeys)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        """Stop listening for hotkeys."""
        if self._listener:
            self._listener.stop()
            self._listener = None
