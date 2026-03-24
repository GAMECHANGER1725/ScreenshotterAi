"""AI vision analysis using Google's Gemini API.

Supports both standard and streaming analysis modes.
"""

import base64
from pathlib import Path
from typing import Generator

from PIL import Image


def _get_genai():
    """Lazy import of google.generativeai to avoid import errors in test environments."""
    import google.generativeai as genai
    return genai


def _configure_client(api_key: str | None = None) -> None:
    """Configure the Gemini client with the API key."""
    import os
    genai = _get_genai()
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    genai.configure(api_key=key)


def _load_image(image_path: Path) -> Image.Image:
    """Load an image for Gemini's vision API."""
    return Image.open(image_path)


def _encode_image(image_path: Path) -> tuple[str, str]:
    """Read and base64-encode an image file. Returns (base64_data, media_type).

    Kept for compatibility with tests and annotation modules.
    """
    suffix = image_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_types.get(suffix, "image/png")
    data = base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")
    return data, media_type


def analyze_screenshot(
    image_path: Path,
    prompt: str = "Describe what you see in this screenshot. Extract any visible text.",
    model: str = "gemini-2.0-flash",
    api_key: str | None = None,
) -> str:
    """Send a screenshot to Gemini's vision API for analysis.

    Args:
        image_path: Path to the screenshot image.
        prompt: What to ask about the image.
        model: Gemini model to use.
        api_key: Gemini API key (uses env var if None).

    Returns:
        The AI's analysis text.
    """
    _configure_client(api_key)
    genai = _get_genai()
    img = _load_image(image_path)

    gemini_model = genai.GenerativeModel(model)
    response = gemini_model.generate_content([prompt, img])
    return response.text


def analyze_screenshot_stream(
    image_path: Path,
    prompt: str = "Describe what you see in this screenshot. Extract any visible text.",
    model: str = "gemini-2.0-flash",
    api_key: str | None = None,
    on_chunk: callable = None,
) -> str:
    """Stream analysis results from Gemini — yields text chunks in real-time.

    Args:
        image_path: Path to the screenshot image.
        prompt: What to ask about the image.
        model: Gemini model to use.
        api_key: Gemini API key.
        on_chunk: Optional callback(str) called for each text chunk.

    Returns:
        The complete analysis text.
    """
    _configure_client(api_key)
    genai = _get_genai()
    img = _load_image(image_path)

    gemini_model = genai.GenerativeModel(model)
    response = gemini_model.generate_content([prompt, img], stream=True)

    full_text = []
    for chunk in response:
        if chunk.text:
            full_text.append(chunk.text)
            if on_chunk:
                on_chunk(chunk.text)

    return "".join(full_text)


def analyze_screenshot_iter(
    image_path: Path,
    prompt: str = "Describe what you see in this screenshot. Extract any visible text.",
    model: str = "gemini-2.0-flash",
    api_key: str | None = None,
) -> Generator[str, None, None]:
    """Generator that yields text chunks from streaming analysis.

    Usage:
        for chunk in analyze_screenshot_iter(path):
            print(chunk, end="", flush=True)
    """
    _configure_client(api_key)
    genai = _get_genai()
    img = _load_image(image_path)

    gemini_model = genai.GenerativeModel(model)
    response = gemini_model.generate_content([prompt, img], stream=True)

    for chunk in response:
        if chunk.text:
            yield chunk.text


def ask_about_screenshot(
    image_path: Path,
    question: str,
    model: str = "gemini-2.0-flash",
    api_key: str | None = None,
) -> str:
    """Ask a specific question about a screenshot."""
    return analyze_screenshot(
        image_path=image_path,
        prompt=question,
        model=model,
        api_key=api_key,
    )


def multi_analyze(
    image_path: Path,
    modes: list[str] | None = None,
    model: str = "gemini-2.0-flash",
    api_key: str | None = None,
) -> dict[str, str]:
    """Run multiple analysis modes on a single screenshot.

    Args:
        image_path: Path to the screenshot.
        modes: List of mode keys. If None, runs describe + extract_text.
        model: Gemini model to use.
        api_key: API key.

    Returns:
        Dict mapping mode keys to analysis results.
    """
    if modes is None:
        modes = ["describe", "extract_text"]

    results = {}
    for mode in modes:
        prompt = ANALYSIS_PROMPTS.get(mode, mode)
        try:
            results[mode] = analyze_screenshot(
                image_path, prompt=prompt, model=model, api_key=api_key,
            )
        except Exception as e:
            results[mode] = f"Error: {e}"

    return results


ANALYSIS_PROMPTS = {
    "describe": "Describe what you see in this screenshot in detail.",
    "extract_text": "Extract ALL visible text from this screenshot. Return only the text, preserving layout where possible.",
    "summarize": "Summarize the main content shown in this screenshot in 2-3 sentences.",
    "code": "Extract any code visible in this screenshot. Return it as properly formatted code with the correct language.",
    "ui_elements": "List all UI elements visible in this screenshot (buttons, fields, menus, etc.) with their labels and approximate positions.",
    "translate": "Extract any text from this screenshot and translate it to English.",
    "explain": "Explain what is happening in this screenshot. What application is being used and what task is being performed?",
    "debug": "Analyze this screenshot for any errors, warnings, or issues. Suggest fixes if applicable.",
    "accessibility": "Evaluate the UI shown in this screenshot for accessibility issues (contrast, text size, labels, etc.).",
    "data": "Extract any structured data (tables, lists, forms) from this screenshot into a clean text format.",
}
