"""OCR text extraction using pytesseract."""

from pathlib import Path

from PIL import Image


def extract_text(image_path: Path | str, language: str = "eng") -> str:
    """Extract text from an image using Tesseract OCR.

    Args:
        image_path: Path to the image file.
        language: Tesseract language code (default: eng).

    Returns:
        Extracted text string.
    """
    import pytesseract

    img = Image.open(image_path)
    text = pytesseract.image_to_string(img, lang=language)
    return text.strip()


def extract_text_with_boxes(image_path: Path | str, language: str = "eng") -> list[dict]:
    """Extract text with bounding box positions.

    Returns a list of dicts with keys: text, left, top, width, height, conf.
    """
    import pytesseract

    img = Image.open(image_path)
    data = pytesseract.image_to_data(img, lang=language, output_type=pytesseract.Output.DICT)

    results = []
    for i in range(len(data["text"])):
        text = data["text"][i].strip()
        if text:
            results.append({
                "text": text,
                "left": data["left"][i],
                "top": data["top"][i],
                "width": data["width"][i],
                "height": data["height"][i],
                "conf": float(data["conf"][i]),
            })
    return results
