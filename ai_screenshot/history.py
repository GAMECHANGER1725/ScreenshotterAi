"""Screenshot history management — tracks captures and their analysis results."""

import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict, field


@dataclass
class ScreenshotRecord:
    """A record of a captured screenshot and its analysis."""
    filepath: str
    timestamp: str
    capture_type: str  # region, fullscreen, window, file
    ocr_text: str = ""
    ai_analysis: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ScreenshotRecord":
        return cls(**data)


class History:
    """Manages a JSON-backed history of screenshots."""

    def __init__(self, history_file: Path, max_records: int = 100):
        self.history_file = history_file
        self.max_records = max_records
        self._records: list[ScreenshotRecord] = []
        self._load()

    def _load(self) -> None:
        if self.history_file.exists():
            with open(self.history_file) as f:
                data = json.load(f)
            self._records = [ScreenshotRecord.from_dict(r) for r in data]

    def _save(self) -> None:
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.history_file, "w") as f:
            json.dump([r.to_dict() for r in self._records], f, indent=2)

    def add(self, record: ScreenshotRecord) -> None:
        """Add a screenshot record to history."""
        self._records.insert(0, record)
        # Trim to max
        if len(self._records) > self.max_records:
            self._records = self._records[: self.max_records]
        self._save()

    def get_all(self) -> list[ScreenshotRecord]:
        """Get all records, newest first."""
        return list(self._records)

    def get_recent(self, n: int = 10) -> list[ScreenshotRecord]:
        """Get the n most recent records."""
        return self._records[:n]

    def search(self, query: str) -> list[ScreenshotRecord]:
        """Search records by OCR text or AI analysis content."""
        query_lower = query.lower()
        return [
            r for r in self._records
            if query_lower in r.ocr_text.lower()
            or query_lower in r.ai_analysis.lower()
            or any(query_lower in t.lower() for t in r.tags)
        ]

    def clear(self) -> None:
        """Clear all history."""
        self._records = []
        self._save()

    def __len__(self) -> int:
        return len(self._records)
