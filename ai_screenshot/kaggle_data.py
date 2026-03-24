"""Kaggle dataset downloader for testing ScreenshotterAI.

Downloads sample screenshot/OCR datasets for local testing and benchmarking.
Requires Kaggle API credentials (set KAGGLE_USERNAME and KAGGLE_KEY env vars,
or place kaggle.json in ~/.kaggle/).
"""

import os
import sys
import zipfile
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()

# Curated datasets useful for testing screenshot analysis and OCR
DATASETS = {
    "textocr": {
        "slug": "robikscool/textocr-text-extraction-from-images-dataset",
        "description": "TextOCR — 900K+ text annotations on real images. Great for OCR testing.",
        "category": "ocr",
    },
    "screenshots": {
        "slug": "nguyenhoaithan/ui-screenshots",
        "description": "UI Screenshots — mobile/web UI screenshots for visual analysis.",
        "category": "ui",
    },
    "receipts": {
        "slug": "jenswalter/receipts",
        "description": "Receipt images — test OCR on structured documents.",
        "category": "ocr",
    },
    "documents": {
        "slug": "ritvik1909/document-images",
        "description": "Document images — scanned docs, forms, and papers.",
        "category": "ocr",
    },
    "handwriting": {
        "slug": "landlord/handwriting-recognition",
        "description": "Handwriting samples — test OCR on handwritten text.",
        "category": "ocr",
    },
    "scene-text": {
        "slug": "preatcher/scene-text",
        "description": "Scene text — text found in natural images (signs, labels, etc.).",
        "category": "ocr",
    },
}


def list_datasets() -> None:
    """Display available datasets."""
    table = Table(title="Available Kaggle Datasets for Testing")
    table.add_column("Name", style="cyan")
    table.add_column("Category", style="green")
    table.add_column("Description", style="white")
    table.add_column("Slug", style="dim")

    for name, info in DATASETS.items():
        table.add_row(name, info["category"], info["description"], info["slug"])

    console.print(table)


def download_dataset(name: str, output_dir: str = "kaggle_data") -> Path | None:
    """Download a dataset from Kaggle.

    Args:
        name: Dataset name key from DATASETS dict, or a full Kaggle slug.
        output_dir: Directory to save the downloaded data.

    Returns:
        Path to the downloaded/extracted data directory.
    """
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError:
        console.print("[red]kaggle package not installed. Run: pip install kaggle[/red]")
        return None

    # Resolve slug
    if name in DATASETS:
        slug = DATASETS[name]["slug"]
        dataset_name = name
    else:
        slug = name
        dataset_name = name.split("/")[-1] if "/" in name else name

    out_path = Path(output_dir) / dataset_name
    out_path.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold]Downloading:[/bold] {slug}")
    console.print(f"[bold]To:[/bold] {out_path}")

    try:
        api = KaggleApi()
        api.authenticate()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Downloading dataset...", total=None)
            api.dataset_download_files(slug, path=str(out_path), unzip=True)
            progress.update(task, description="Download complete!")

        # Count files
        files = list(out_path.rglob("*"))
        image_files = [f for f in files if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".tiff")]

        console.print(f"[green]Downloaded {len(files)} files ({len(image_files)} images)[/green]")
        return out_path

    except Exception as e:
        console.print(f"[red]Download failed: {e}[/red]")
        console.print("[dim]Make sure KAGGLE_USERNAME and KAGGLE_KEY are set, or ~/.kaggle/kaggle.json exists.[/dim]")
        return None


def download_sample(output_dir: str = "kaggle_data") -> Path | None:
    """Download a small sample dataset for quick testing."""
    return download_dataset("receipts", output_dir)


def batch_test(data_dir: str, max_images: int = 5) -> None:
    """Run OCR and optionally AI analysis on a batch of images from a dataset.

    Useful for benchmarking and testing the tool against real data.
    """
    from ai_screenshot.config import load_config
    from ai_screenshot.ocr import extract_text

    config = load_config()
    data_path = Path(data_dir)

    if not data_path.exists():
        console.print(f"[red]Directory not found: {data_dir}[/red]")
        return

    image_files = []
    for ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
        image_files.extend(data_path.rglob(f"*{ext}"))

    if not image_files:
        console.print(f"[red]No images found in {data_dir}[/red]")
        return

    image_files = image_files[:max_images]
    console.print(f"[bold]Testing {len(image_files)} images from {data_dir}[/bold]\n")

    for img_path in image_files:
        console.print(f"\n[cyan]{'─' * 60}[/cyan]")
        console.print(f"[bold]Image:[/bold] {img_path.name}")

        try:
            text = extract_text(img_path, config.get("ocr_language", "eng"))
            preview = text[:200] + "..." if len(text) > 200 else text
            console.print(f"[green]OCR:[/green] {preview or '[dim]No text detected[/dim]'}")
        except Exception as e:
            console.print(f"[red]OCR error: {e}[/red]")

        # AI analysis if API key available
        if config.get("api_key"):
            try:
                from ai_screenshot.analyzer import analyze_screenshot
                result = analyze_screenshot(
                    img_path,
                    prompt="Briefly describe this image in one sentence.",
                    model=config.get("ai_model", "claude-sonnet-4-20250514"),
                    api_key=config.get("api_key"),
                )
                console.print(f"[magenta]AI:[/magenta] {result}")
            except Exception as e:
                console.print(f"[yellow]AI analysis skipped: {e}[/yellow]")


def main():
    """CLI entry point for Kaggle dataset management."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="ai-screenshot-kaggle",
        description="Download and test with Kaggle datasets",
    )
    subparsers = parser.add_subparsers(dest="command")

    # list
    subparsers.add_parser("list", help="List available datasets")

    # download
    dl = subparsers.add_parser("download", help="Download a dataset")
    dl.add_argument("name", help="Dataset name or Kaggle slug")
    dl.add_argument("--output", "-o", default="kaggle_data", help="Output directory")

    # test
    test = subparsers.add_parser("test", help="Run batch test on downloaded images")
    test.add_argument("dir", help="Directory containing images")
    test.add_argument("--max", "-n", type=int, default=5, help="Max images to test")

    args = parser.parse_args()

    if args.command == "list":
        list_datasets()
    elif args.command == "download":
        download_dataset(args.name, args.output)
    elif args.command == "test":
        batch_test(args.dir, args.max)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
