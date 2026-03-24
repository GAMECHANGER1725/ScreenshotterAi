"""Smart content detection — auto-detect what's in a screenshot and pick the best analysis mode.

Analyzes image properties, OCR output, and pixel patterns to determine
whether the screenshot contains code, a document, a UI, a receipt, etc.
"""

import re
from pathlib import Path

from PIL import Image, ImageStat


# Heuristic patterns for content detection
CODE_PATTERNS = [
    r"(def |class |function |const |let |var |import |from |return )",
    r"[{}\[\]();]",
    r"(=>|->|::|\|\||\&\&)",
    r"(if\s*\(|for\s*\(|while\s*\()",
    r"(console\.log|print\(|println|System\.out)",
]

RECEIPT_PATTERNS = [
    r"\$\d+\.\d{2}",
    r"(total|subtotal|tax|tip|amount|balance)",
    r"(visa|mastercard|amex|cash|change|paid)",
    r"(qty|quantity|item|price|receipt)",
]

DOCUMENT_PATTERNS = [
    r"(dear\s|sincerely|regards|subject:|re:|from:|to:)",
    r"(section\s+\d|chapter\s+\d|page\s+\d|article\s+\d)",
    r"(abstract|introduction|conclusion|references|bibliography)",
]

URL_PATTERNS = [
    r"https?://\S+",
    r"www\.\S+",
]

EMAIL_PATTERNS = [
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
]


class ContentType:
    CODE = "code"
    DOCUMENT = "document"
    RECEIPT = "receipt"
    UI = "ui_elements"
    SCREENSHOT = "describe"
    TEXT_HEAVY = "extract_text"
    NATURAL = "describe"
    UNKNOWN = "describe"


def detect_content_type(image_path: Path, ocr_text: str = "") -> str:
    """Detect what type of content is in the image.

    Uses a combination of image analysis and OCR text patterns to determine
    the most likely content type. Returns an analysis mode key.

    Args:
        image_path: Path to the screenshot.
        ocr_text: Pre-extracted OCR text (if available, saves re-running OCR).

    Returns:
        Analysis mode key (matches ANALYSIS_PROMPTS keys).
    """
    scores: dict[str, float] = {
        ContentType.CODE: 0,
        ContentType.DOCUMENT: 0,
        ContentType.RECEIPT: 0,
        ContentType.UI: 0,
        ContentType.TEXT_HEAVY: 0,
        ContentType.NATURAL: 0,
    }

    # Analyze image properties
    try:
        img = Image.open(image_path)
        width, height = img.size
        aspect_ratio = width / max(height, 1)

        # Image statistics
        stat = ImageStat.Stat(img.convert("RGB"))
        mean_brightness = sum(stat.mean) / 3
        stddev = sum(stat.stddev) / 3

        # Dark images with high contrast → likely code editor / terminal
        if mean_brightness < 80 and stddev > 40:
            scores[ContentType.CODE] += 2.0

        # Very bright, low contrast → likely document
        if mean_brightness > 200 and stddev < 50:
            scores[ContentType.DOCUMENT] += 1.5

        # Narrow aspect → receipt
        if aspect_ratio < 0.6:
            scores[ContentType.RECEIPT] += 1.5

        # Wide aspect → UI / website
        if aspect_ratio > 1.5:
            scores[ContentType.UI] += 1.0

    except Exception:
        pass

    # Analyze OCR text patterns
    if ocr_text:
        text_lower = ocr_text.lower()
        text_len = len(ocr_text)

        # Check code patterns
        code_score = sum(
            len(re.findall(p, ocr_text, re.IGNORECASE))
            for p in CODE_PATTERNS
        )
        if code_score > 5:
            scores[ContentType.CODE] += 3.0
        elif code_score > 2:
            scores[ContentType.CODE] += 1.5

        # Check receipt patterns
        receipt_score = sum(
            len(re.findall(p, text_lower))
            for p in RECEIPT_PATTERNS
        )
        if receipt_score > 3:
            scores[ContentType.RECEIPT] += 3.0
        elif receipt_score > 1:
            scores[ContentType.RECEIPT] += 1.5

        # Check document patterns
        doc_score = sum(
            len(re.findall(p, text_lower))
            for p in DOCUMENT_PATTERNS
        )
        if doc_score > 2:
            scores[ContentType.DOCUMENT] += 3.0
        elif doc_score > 0:
            scores[ContentType.DOCUMENT] += 1.0

        # High text density → text-heavy content
        if text_len > 500:
            scores[ContentType.TEXT_HEAVY] += 2.0
        elif text_len > 200:
            scores[ContentType.TEXT_HEAVY] += 1.0

        # Low text → natural image or UI
        if text_len < 50:
            scores[ContentType.NATURAL] += 1.5
            scores[ContentType.UI] += 0.5

    # Pick the highest scoring type
    best = max(scores, key=lambda k: scores[k])

    # If no strong signal, default to describe
    if scores[best] < 1.0:
        return ContentType.UNKNOWN

    return best


def get_smart_prompt(image_path: Path, ocr_text: str = "") -> tuple[str, str]:
    """Get the best analysis prompt for the detected content type.

    Returns:
        Tuple of (mode_key, prompt_text).
    """
    from ai_screenshot.analyzer import ANALYSIS_PROMPTS

    mode = detect_content_type(image_path, ocr_text)
    prompt = ANALYSIS_PROMPTS.get(mode, ANALYSIS_PROMPTS["describe"])
    return mode, prompt
