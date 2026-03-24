"""AI vision analysis using Anthropic's Claude API.

Supports both standard and streaming analysis modes.
"""

import base64
from pathlib import Path
from typing import Generator

import anthropic


def _encode_image(image_path: Path) -> tuple[str, str]:
    """Read and base64-encode an image file. Returns (base64_data, media_type)."""
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


def _build_messages(image_path: Path, prompt: str) -> list[dict]:
    """Build the messages payload for the Claude API."""
    image_data, media_type = _encode_image(image_path)
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": prompt,
                },
            ],
        }
    ]


def analyze_screenshot(
    image_path: Path,
    prompt: str = "Describe what you see in this screenshot. Extract any visible text.",
    model: str = "claude-sonnet-4-20250514",
    api_key: str | None = None,
) -> str:
    """Send a screenshot to Claude's vision API for analysis.

    Args:
        image_path: Path to the screenshot image.
        prompt: What to ask about the image.
        model: Claude model to use.
        api_key: Anthropic API key (uses env var if None).

    Returns:
        The AI's analysis text.
    """
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=_build_messages(image_path, prompt),
    )
    return message.content[0].text


def analyze_screenshot_stream(
    image_path: Path,
    prompt: str = "Describe what you see in this screenshot. Extract any visible text.",
    model: str = "claude-sonnet-4-20250514",
    api_key: str | None = None,
    on_chunk: callable = None,
) -> str:
    """Stream analysis results from Claude — yields text chunks in real-time.

    This provides the Wispr Flow-like experience of seeing results appear
    as they're generated.

    Args:
        image_path: Path to the screenshot image.
        prompt: What to ask about the image.
        model: Claude model to use.
        api_key: Anthropic API key.
        on_chunk: Optional callback(str) called for each text chunk.

    Returns:
        The complete analysis text.
    """
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    full_text = []

    with client.messages.stream(
        model=model,
        max_tokens=4096,
        messages=_build_messages(image_path, prompt),
    ) as stream:
        for text in stream.text_stream:
            full_text.append(text)
            if on_chunk:
                on_chunk(text)

    return "".join(full_text)


def analyze_screenshot_iter(
    image_path: Path,
    prompt: str = "Describe what you see in this screenshot. Extract any visible text.",
    model: str = "claude-sonnet-4-20250514",
    api_key: str | None = None,
) -> Generator[str, None, None]:
    """Generator that yields text chunks from streaming analysis.

    Usage:
        for chunk in analyze_screenshot_iter(path):
            print(chunk, end="", flush=True)
    """
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    with client.messages.stream(
        model=model,
        max_tokens=4096,
        messages=_build_messages(image_path, prompt),
    ) as stream:
        for text in stream.text_stream:
            yield text


def ask_about_screenshot(
    image_path: Path,
    question: str,
    model: str = "claude-sonnet-4-20250514",
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
    model: str = "claude-sonnet-4-20250514",
    api_key: str | None = None,
) -> dict[str, str]:
    """Run multiple analysis modes on a single screenshot.

    Args:
        image_path: Path to the screenshot.
        modes: List of mode keys. If None, runs describe + extract_text.
        model: Claude model to use.
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
