"""Image annotation — draw highlights, arrows, and text on screenshots.

Provides a simple annotation API for marking up screenshots before
or after AI analysis. Useful for highlighting regions of interest.
"""

from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFont


Color = tuple[int, int, int, int]  # RGBA

# Default colors
RED = (255, 75, 75, 200)
GREEN = (75, 200, 120, 200)
BLUE = (100, 130, 255, 200)
YELLOW = (255, 220, 50, 200)
WHITE = (255, 255, 255, 230)


class Annotator:
    """Draw annotations on a screenshot image."""

    def __init__(self, image_path: Path | str):
        self.image_path = Path(image_path)
        self.image = Image.open(self.image_path).convert("RGBA")
        self._overlay = Image.new("RGBA", self.image.size, (0, 0, 0, 0))
        self._draw = ImageDraw.Draw(self._overlay)

    def highlight_region(
        self,
        x: int, y: int, width: int, height: int,
        color: Color = YELLOW,
        border_width: int = 3,
    ) -> "Annotator":
        """Draw a highlighted rectangle around a region."""
        # Semi-transparent fill
        fill = (color[0], color[1], color[2], 40)
        self._draw.rectangle(
            [(x, y), (x + width, y + height)],
            fill=fill,
            outline=color,
            width=border_width,
        )
        return self

    def draw_arrow(
        self,
        x1: int, y1: int, x2: int, y2: int,
        color: Color = RED,
        width: int = 3,
    ) -> "Annotator":
        """Draw a line with an arrowhead."""
        self._draw.line([(x1, y1), (x2, y2)], fill=color, width=width)

        # Arrowhead
        import math
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_len = 15
        for offset in [math.pi / 6, -math.pi / 6]:
            ax = x2 - arrow_len * math.cos(angle + offset)
            ay = y2 - arrow_len * math.sin(angle + offset)
            self._draw.line([(x2, y2), (int(ax), int(ay))], fill=color, width=width)

        return self

    def add_text(
        self,
        x: int, y: int,
        text: str,
        color: Color = WHITE,
        size: int = 16,
        bg_color: Color | None = (0, 0, 0, 160),
    ) -> "Annotator":
        """Add text label at a position."""
        try:
            fnt = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", size)
        except (OSError, IOError):
            fnt = ImageFont.load_default()

        # Draw background box behind text
        if bg_color:
            bbox = self._draw.textbbox((x, y), text, font=fnt)
            pad = 4
            self._draw.rectangle(
                [bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad],
                fill=bg_color,
            )

        self._draw.text((x, y), text, fill=color, font=fnt)
        return self

    def add_number_badge(
        self,
        x: int, y: int,
        number: int,
        color: Color = RED,
    ) -> "Annotator":
        """Add a numbered circle badge (for marking up UI elements)."""
        radius = 14
        self._draw.ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            fill=color,
        )
        text = str(number)
        try:
            fnt = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", 14)
        except (OSError, IOError):
            fnt = ImageFont.load_default()

        bbox = self._draw.textbbox((0, 0), text, font=fnt)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        self._draw.text(
            (x - tw // 2, y - th // 2 - 1), text, fill=WHITE, font=fnt,
        )
        return self

    def blur_region(
        self,
        x: int, y: int, width: int, height: int,
    ) -> "Annotator":
        """Blur/pixelate a region (for redacting sensitive info)."""
        from PIL import ImageFilter

        region = self.image.crop((x, y, x + width, y + height))
        # Pixelate by downscaling and upscaling
        small = region.resize((max(1, width // 10), max(1, height // 10)), Image.NEAREST)
        pixelated = small.resize((width, height), Image.NEAREST)
        self.image.paste(pixelated, (x, y))
        return self

    def save(self, output_path: Path | str | None = None) -> Path:
        """Composite overlay onto image and save.

        Args:
            output_path: Where to save. If None, overwrites the original.

        Returns:
            Path to the saved annotated image.
        """
        out = Path(output_path) if output_path else self.image_path
        result = Image.alpha_composite(self.image, self._overlay)
        result = result.convert("RGB")
        result.save(out)
        return out

    def save_as(self, suffix: str = "_annotated") -> Path:
        """Save with a suffix added to the filename."""
        stem = self.image_path.stem
        ext = self.image_path.suffix
        out = self.image_path.parent / f"{stem}{suffix}{ext}"
        return self.save(out)


def annotate_ocr_regions(
    image_path: Path,
    ocr_boxes: list[dict],
    output_path: Path | None = None,
) -> Path:
    """Annotate an image with OCR bounding boxes.

    Args:
        image_path: Source image.
        ocr_boxes: List of dicts from ocr.extract_text_with_boxes().
        output_path: Where to save (default: adds _annotated suffix).

    Returns:
        Path to annotated image.
    """
    ann = Annotator(image_path)

    for i, box in enumerate(ocr_boxes):
        if box["conf"] > 50:  # Only show confident detections
            ann.highlight_region(
                box["left"], box["top"], box["width"], box["height"],
                color=GREEN if box["conf"] > 80 else YELLOW,
                border_width=2,
            )

    if output_path:
        return ann.save(output_path)
    return ann.save_as()
