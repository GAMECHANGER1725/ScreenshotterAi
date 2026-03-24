"""CLI interface for ScreenshotterAI — works on any platform for testing."""

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_screenshot.config import load_config, ensure_dirs
from ai_screenshot.capture import capture_region, capture_fullscreen, capture_window, capture_from_file
from ai_screenshot.ocr import extract_text
from ai_screenshot.analyzer import analyze_screenshot, ask_about_screenshot, ANALYSIS_PROMPTS
from ai_screenshot.clipboard import copy_text
from ai_screenshot.history import History, ScreenshotRecord

console = Console()


def cmd_capture(args, config):
    """Handle capture subcommand."""
    ensure_dirs(config)

    if args.file:
        path = capture_from_file(args.file)
        capture_type = "file"
    elif args.mode == "region":
        path = capture_region(config["screenshot_dir"])
        capture_type = "region"
    elif args.mode == "fullscreen":
        path = capture_fullscreen(config["screenshot_dir"])
        capture_type = "fullscreen"
    elif args.mode == "window":
        path = capture_window(config["screenshot_dir"])
        capture_type = "window"
    else:
        path = capture_region(config["screenshot_dir"])
        capture_type = "region"

    if not path:
        console.print("[red]Capture cancelled or failed.[/red]")
        return

    console.print(f"[green]Screenshot saved:[/green] {path}")

    # OCR
    if args.ocr or args.all:
        console.print("\n[bold]OCR Text:[/bold]")
        try:
            text = extract_text(path, config.get("ocr_language", "eng"))
            console.print(Panel(text or "[dim]No text detected[/dim]", title="OCR Result"))
            if args.copy:
                copy_text(text)
                console.print("[green]Copied to clipboard![/green]")
        except Exception as e:
            console.print(f"[red]OCR failed: {e}[/red]")

    # AI Analysis
    if args.analyze or args.all:
        prompt_key = args.prompt or "describe"
        prompt = ANALYSIS_PROMPTS.get(prompt_key, prompt_key)
        console.print(f"\n[bold]AI Analysis ({prompt_key}):[/bold]")
        try:
            result = analyze_screenshot(
                path,
                prompt=prompt,
                model=config.get("ai_model", "claude-sonnet-4-20250514"),
                api_key=config.get("api_key"),
            )
            console.print(Panel(result, title="AI Analysis"))
            if args.copy and not (args.ocr or args.all):
                copy_text(result)
                console.print("[green]Copied to clipboard![/green]")
        except Exception as e:
            console.print(f"[red]AI analysis failed: {e}[/red]")

    # Ask
    if args.ask:
        console.print(f"\n[bold]Question:[/bold] {args.ask}")
        try:
            result = ask_about_screenshot(
                path,
                question=args.ask,
                model=config.get("ai_model", "claude-sonnet-4-20250514"),
                api_key=config.get("api_key"),
            )
            console.print(Panel(result, title="Answer"))
            if args.copy:
                copy_text(result)
                console.print("[green]Copied to clipboard![/green]")
        except Exception as e:
            console.print(f"[red]AI query failed: {e}[/red]")


def cmd_history(args, config):
    """Handle history subcommand."""
    ensure_dirs(config)
    history_file = Path(config["screenshot_dir"]) / ".history.json"
    history = History(history_file)

    if args.clear:
        history.clear()
        console.print("[green]History cleared.[/green]")
        return

    if args.search:
        records = history.search(args.search)
    else:
        records = history.get_recent(args.limit)

    if not records:
        console.print("[dim]No records found.[/dim]")
        return

    table = Table(title="Screenshot History")
    table.add_column("Time", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("OCR Preview", style="yellow", max_width=40)
    table.add_column("AI Preview", style="magenta", max_width=40)

    for r in records:
        table.add_row(
            r.timestamp[:19],
            r.capture_type,
            (r.ocr_text[:37] + "...") if len(r.ocr_text) > 40 else r.ocr_text,
            (r.ai_analysis[:37] + "...") if len(r.ai_analysis) > 40 else r.ai_analysis,
        )
    console.print(table)


def cmd_analyze(args, config):
    """Analyze an existing image file."""
    path = Path(args.file)
    if not path.exists():
        console.print(f"[red]File not found: {args.file}[/red]")
        return

    prompt_key = args.prompt or "describe"
    prompt = ANALYSIS_PROMPTS.get(prompt_key, prompt_key)

    console.print(f"[bold]Analyzing:[/bold] {path}")
    console.print(f"[bold]Prompt:[/bold] {prompt_key}")

    # OCR
    console.print("\n[bold]OCR Text:[/bold]")
    try:
        text = extract_text(path, config.get("ocr_language", "eng"))
        console.print(Panel(text or "[dim]No text detected[/dim]", title="OCR"))
    except Exception as e:
        console.print(f"[yellow]OCR unavailable: {e}[/yellow]")

    # AI
    console.print(f"\n[bold]AI Analysis:[/bold]")
    try:
        result = analyze_screenshot(
            path,
            prompt=prompt,
            model=config.get("ai_model", "claude-sonnet-4-20250514"),
            api_key=config.get("api_key"),
        )
        console.print(Panel(result, title="AI Analysis"))
        if args.copy:
            copy_text(result)
            console.print("[green]Copied to clipboard![/green]")
    except Exception as e:
        console.print(f"[red]AI analysis failed: {e}[/red]")


def main():
    parser = argparse.ArgumentParser(
        prog="ai-screenshot",
        description="ScreenshotterAI — capture, analyze, and extract text from your screen",
    )
    subparsers = parser.add_subparsers(dest="command")

    # capture
    cap = subparsers.add_parser("capture", help="Take a screenshot")
    cap.add_argument("--mode", choices=["region", "fullscreen", "window"], default="region")
    cap.add_argument("--file", "-f", help="Analyze an existing image file instead of capturing")
    cap.add_argument("--ocr", action="store_true", help="Run OCR text extraction")
    cap.add_argument("--analyze", "-a", action="store_true", help="Run AI analysis")
    cap.add_argument("--all", action="store_true", help="Run both OCR and AI analysis")
    cap.add_argument("--ask", "-q", help="Ask a specific question about the screenshot")
    cap.add_argument("--prompt", "-p", help="Analysis prompt key or custom prompt")
    cap.add_argument("--copy", "-c", action="store_true", help="Copy result to clipboard")

    # analyze
    ana = subparsers.add_parser("analyze", help="Analyze an existing image")
    ana.add_argument("file", help="Path to image file")
    ana.add_argument("--prompt", "-p", default="describe", help="Analysis prompt key or custom text")
    ana.add_argument("--copy", "-c", action="store_true", help="Copy result to clipboard")

    # history
    hist = subparsers.add_parser("history", help="View screenshot history")
    hist.add_argument("--limit", "-n", type=int, default=10, help="Number of records to show")
    hist.add_argument("--search", "-s", help="Search history by text content")
    hist.add_argument("--clear", action="store_true", help="Clear all history")

    # gui
    subparsers.add_parser("gui", help="Launch the menu bar app (macOS only)")

    args = parser.parse_args()
    config = load_config()

    if args.command == "capture":
        cmd_capture(args, config)
    elif args.command == "analyze":
        cmd_analyze(args, config)
    elif args.command == "history":
        cmd_history(args, config)
    elif args.command == "gui":
        from ai_screenshot.app import main as gui_main
        gui_main()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
