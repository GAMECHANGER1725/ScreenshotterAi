"""Tests for image annotation module."""

from pathlib import Path

from PIL import Image

from ai_screenshot.annotate import Annotator, annotate_ocr_regions


def _create_test_image(tmp_path, size=(400, 300)):
    img = Image.new("RGB", size, color=(255, 255, 255))
    path = tmp_path / "test.png"
    img.save(path)
    return path


def test_annotator_highlight_region(tmp_path):
    """Should draw a highlighted rectangle."""
    path = _create_test_image(tmp_path)
    ann = Annotator(path)
    ann.highlight_region(10, 10, 100, 50)
    out = ann.save_as()
    assert out.exists()
    assert "_annotated" in out.name


def test_annotator_add_text(tmp_path):
    """Should add text to the image."""
    path = _create_test_image(tmp_path)
    ann = Annotator(path)
    ann.add_text(10, 10, "Hello World")
    out = ann.save_as()
    assert out.exists()


def test_annotator_draw_arrow(tmp_path):
    """Should draw an arrow."""
    path = _create_test_image(tmp_path)
    ann = Annotator(path)
    ann.draw_arrow(10, 10, 200, 150)
    out = ann.save_as()
    assert out.exists()


def test_annotator_chaining(tmp_path):
    """Should support method chaining."""
    path = _create_test_image(tmp_path)
    out = (
        Annotator(path)
        .highlight_region(10, 10, 100, 50)
        .add_text(10, 70, "Test")
        .draw_arrow(10, 90, 100, 90)
        .add_number_badge(50, 50, 1)
        .save_as()
    )
    assert out.exists()


def test_annotator_blur_region(tmp_path):
    """Should pixelate a region."""
    path = _create_test_image(tmp_path)
    ann = Annotator(path)
    ann.blur_region(10, 10, 100, 50)
    out = ann.save_as()
    assert out.exists()


def test_annotate_ocr_regions(tmp_path):
    """Should annotate image with OCR bounding boxes."""
    path = _create_test_image(tmp_path)
    boxes = [
        {"text": "Hello", "left": 10, "top": 10, "width": 60, "height": 20, "conf": 95.0},
        {"text": "World", "left": 10, "top": 40, "width": 60, "height": 20, "conf": 85.0},
        {"text": "?", "left": 10, "top": 70, "width": 10, "height": 10, "conf": 30.0},  # Low confidence
    ]
    out = annotate_ocr_regions(path, boxes)
    assert out.exists()
