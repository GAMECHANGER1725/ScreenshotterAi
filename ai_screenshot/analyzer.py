"""AI vision analysis using Anthropic's Claude API."""

import base64
from pathlib import Path

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

    image_data, media_type = _encode_image(image_path)

    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[
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
        ],
    )
    return message.content[0].text


def ask_about_screenshot(
    image_path: Path,
    question: str,
    model: str = "claude-sonnet-4-20250514",
    api_key: str | None = None,
) -> str:
    """Ask a specific question about a screenshot.

    Args:
        image_path: Path to the screenshot.
        question: The question to ask.
        model: Claude model to use.
        api_key: Anthropic API key.

    Returns:
        The AI's response.
    """
    return analyze_screenshot(
        image_path=image_path,
        prompt=question,
        model=model,
        api_key=api_key,
    )


ANALYSIS_PROMPTS = {
    "describe": "Describe what you see in this screenshot in detail.",
    "extract_text": "Extract ALL visible text from this screenshot. Return only the text, preserving layout where possible.",
    "summarize": "Summarize the main content shown in this screenshot in 2-3 sentences.",
    "code": "Extract any code visible in this screenshot. Return it as properly formatted code.",
    "ui_elements": "List all UI elements visible in this screenshot (buttons, fields, menus, etc.) with their labels.",
    "translate": "Extract any text from this screenshot and translate it to English.",
    "explain": "Explain what is happening in this screenshot. What application is being used and what task is being performed?",
}
