"""Tests for screenshot history management."""

from pathlib import Path

from ai_screenshot.history import History, ScreenshotRecord


def _make_record(text="hello", capture_type="region") -> ScreenshotRecord:
    return ScreenshotRecord(
        filepath="/tmp/test.png",
        timestamp="2025-01-01T12:00:00",
        capture_type=capture_type,
        ocr_text=text,
    )


def test_history_add_and_retrieve(tmp_path):
    h = History(tmp_path / "history.json")
    r = _make_record()
    h.add(r)
    assert len(h) == 1
    assert h.get_all()[0].ocr_text == "hello"


def test_history_max_records(tmp_path):
    h = History(tmp_path / "history.json", max_records=3)
    for i in range(5):
        h.add(_make_record(text=f"record_{i}"))
    assert len(h) == 3
    # Most recent should be first
    assert h.get_all()[0].ocr_text == "record_4"


def test_history_search(tmp_path):
    h = History(tmp_path / "history.json")
    h.add(_make_record(text="receipt from store"))
    h.add(_make_record(text="code snippet"))
    h.add(_make_record(text="email from store"))

    results = h.search("store")
    assert len(results) == 2


def test_history_clear(tmp_path):
    h = History(tmp_path / "history.json")
    h.add(_make_record())
    h.add(_make_record())
    h.clear()
    assert len(h) == 0


def test_history_persistence(tmp_path):
    path = tmp_path / "history.json"
    h1 = History(path)
    h1.add(_make_record(text="persistent"))
    del h1

    h2 = History(path)
    assert len(h2) == 1
    assert h2.get_all()[0].ocr_text == "persistent"


def test_record_serialization():
    r = _make_record(text="test")
    d = r.to_dict()
    r2 = ScreenshotRecord.from_dict(d)
    assert r2.ocr_text == "test"
    assert r2.capture_type == "region"
