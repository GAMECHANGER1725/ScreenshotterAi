"""CLI interface for ScreenshotterAI — works on any platform for testing.

Provides all features including streaming analysis, smart mode,
annotation, timed capture, and continuous watch mode.
"""

import argparse
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text

from ai_screenshot.config import load_config, ensure_dirs
from ai_screenshot.capture import capture_region, capture_fullscreen, capture_window, capture_from_file
from ai_screenshot.ocr import extract_text
from ai_screenshot.analyzer import (
    analyze_screenshot, analyze_screenshot_stream, analyze_screenshot_iter,
    ask_about_screenshot, multi_analyze, ANALYSIS_PROMPTS,
)
from ai_screenshot.clipboard import copy_text, paste_text
from ai_screenshot.history import History, ScreenshotRecord

console = Console()


def cmd_capture(args, config):
    """Handle capture subcommand."""
    ensure_dirs(config)

    # Timed capture
    if args.delay:
        console.print(f"[bold]Capturing in {args.delay} seconds...[/bold]")
        for i in range(int(args.delay), 0, -1):
            console.print(f"  [cyan]{i}...[/cyan]")
            time.sleep(1)

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

    ocr_text = ""

    # OCR
    if args.ocr or args.all:
        console.print("\n[bold]OCR Text:[/bold]")
        try:
            ocr_text = extract_text(path, config.get("ocr_language", "eng"))
            console.print(Panel(ocr_text or "[dim]No text detected[/dim]", title="OCR Result"))
            if args.copy:
                copy_text(ocr_text)
                console.print("[green]Copied to clipboard![/green]")
        except Exception as e:
            console.print(f"[red]OCR failed: {e}[/red]")

    # Smart mode — auto-detect content and pick best prompt
    if args.smart or (args.all and config.get("smart_mode")):
        from ai_screenshot.smart import get_smart_prompt
        if not ocr_text:
            try:
                ocr_text = extract_text(path, config.get("ocr_language", "eng"))
            except Exception:
                pass
        mode, prompt = get_smart_prompt(path, ocr_text)
        console.print(f"\n[bold]Smart Mode:[/bold] Detected → [cyan]{mode}[/cyan]")
        args.prompt = mode
        args.analyze = True

    # AI Analysis
    if args.analyze or args.all:
        prompt_key = args.prompt or "describe"
        prompt = ANALYSIS_PROMPTS.get(prompt_key, prompt_key)
        console.print(f"\n[bold]AI Analysis ({prompt_key}):[/bold]")
        try:
            if args.stream:
                # Streaming mode — show results in real time
                result_parts = []
                with Live(Text(""), console=console, refresh_per_second=10) as live:
                    def on_chunk(chunk):
                        result_parts.append(chunk)
                        live.update(Text("".join(result_parts)))

                    analyze_screenshot_stream(
                        path,
                        prompt=prompt,
                        model=config.get("ai_model", "gemini-2.0-flash"),
                        api_key=config.get("api_key"),
                        on_chunk=on_chunk,
                    )
                result = "".join(result_parts)
                console.print()  # newline after streaming
            else:
                result = analyze_screenshot(
                    path,
                    prompt=prompt,
                    model=config.get("ai_model", "gemini-2.0-flash"),
                    api_key=config.get("api_key"),
                )
                console.print(Panel(result, title="AI Analysis"))

            if args.paste:
                paste_text(result)
                console.print("[green]Pasted into active app![/green]")
            elif args.copy and not (args.ocr or args.all):
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
                model=config.get("ai_model", "gemini-2.0-flash"),
                api_key=config.get("api_key"),
            )
            console.print(Panel(result, title="Answer"))
            if args.paste:
                paste_text(result)
                console.print("[green]Pasted into active app![/green]")
            elif args.copy:
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

    console.print(f"[bold]Analyzing:[/bold] {path}")

    ocr_text = ""

    # OCR
    console.print("\n[bold]OCR Text:[/bold]")
    try:
        ocr_text = extract_text(path, config.get("ocr_language", "eng"))
        console.print(Panel(ocr_text or "[dim]No text detected[/dim]", title="OCR"))
    except Exception as e:
        console.print(f"[yellow]OCR unavailable: {e}[/yellow]")

    # Smart prompt selection
    prompt_key = args.prompt
    if prompt_key == "smart":
        from ai_screenshot.smart import get_smart_prompt
        prompt_key, prompt = get_smart_prompt(path, ocr_text)
        console.print(f"[bold]Smart Mode:[/bold] Detected → [cyan]{prompt_key}[/cyan]")
    else:
        prompt = ANALYSIS_PROMPTS.get(prompt_key, prompt_key)

    console.print(f"\n[bold]AI Analysis ({prompt_key}):[/bold]")

    # AI
    try:
        if args.stream:
            result_parts = []
            with Live(Text(""), console=console, refresh_per_second=10) as live:
                def on_chunk(chunk):
                    result_parts.append(chunk)
                    live.update(Text("".join(result_parts)))

                analyze_screenshot_stream(
                    path,
                    prompt=prompt,
                    model=config.get("ai_model", "gemini-2.0-flash"),
                    api_key=config.get("api_key"),
                    on_chunk=on_chunk,
                )
            result = "".join(result_parts)
            console.print()
        else:
            result = analyze_screenshot(
                path,
                prompt=prompt,
                model=config.get("ai_model", "gemini-2.0-flash"),
                api_key=config.get("api_key"),
            )
            console.print(Panel(result, title="AI Analysis"))

        if args.paste:
            paste_text(result)
            console.print("[green]Pasted into active app![/green]")
        elif args.copy:
            copy_text(result)
            console.print("[green]Copied to clipboard![/green]")
    except Exception as e:
        console.print(f"[red]AI analysis failed: {e}[/red]")


def cmd_annotate(args, config):
    """Annotate a screenshot with OCR bounding boxes."""
    path = Path(args.file)
    if not path.exists():
        console.print(f"[red]File not found: {args.file}[/red]")
        return

    from ai_screenshot.ocr import extract_text_with_boxes
    from ai_screenshot.annotate import annotate_ocr_regions

    console.print(f"[bold]Annotating:[/bold] {path}")

    try:
        boxes = extract_text_with_boxes(path, config.get("ocr_language", "eng"))
        console.print(f"Found {len(boxes)} text regions")
        out = annotate_ocr_regions(path, boxes)
        console.print(f"[green]Annotated image saved:[/green] {out}")
    except Exception as e:
        console.print(f"[red]Annotation failed: {e}[/red]")


def cmd_watch(args, config):
    """Start continuous screen watching."""
    from ai_screenshot.watcher import ScreenWatcher

    ensure_dirs(config)

    def on_change(path):
        console.print(f"\n[cyan]Change detected![/cyan] Saved: {path}")
        if args.analyze:
            try:
                ocr_text = extract_text(path, config.get("ocr_language", "eng"))
                if ocr_text:
                    console.print(f"[yellow]OCR:[/yellow] {ocr_text[:100]}")

                if config.get("api_key"):
                    from ai_screenshot.smart import get_smart_prompt
                    mode, prompt = get_smart_prompt(path, ocr_text)
                    result = analyze_screenshot(
                        path, prompt=prompt,
                        model=config.get("ai_model", "gemini-2.0-flash"),
                        api_key=config.get("api_key"),
                    )
                    console.print(f"[magenta]AI ({mode}):[/magenta] {result[:200]}")
            except Exception as e:
                console.print(f"[red]Analysis error: {e}[/red]")

    watcher = ScreenWatcher(
        screenshot_dir=config["screenshot_dir"],
        interval=args.interval,
        change_threshold=args.threshold,
        on_change=on_change,
    )

    console.print(f"[bold]Watching screen[/bold] (interval={args.interval}s, threshold={args.threshold})")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    watcher.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
        console.print("\n[green]Stopped watching.[/green]")


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
    cap.add_argument("--smart", "-s", action="store_true", help="Smart mode — auto-detect content type")
    cap.add_argument("--ask", "-q", help="Ask a specific question about the screenshot")
    cap.add_argument("--prompt", "-p", help="Analysis prompt key or custom prompt")
    cap.add_argument("--copy", "-c", action="store_true", help="Copy result to clipboard")
    cap.add_argument("--paste", action="store_true", help="Paste result into active app")
    cap.add_argument("--stream", action="store_true", default=True, help="Stream AI results in real time")
    cap.add_argument("--no-stream", dest="stream", action="store_false", help="Disable streaming")
    cap.add_argument("--delay", "-d", type=float, help="Delay in seconds before capturing")

    # analyze
    ana = subparsers.add_parser("analyze", help="Analyze an existing image")
    ana.add_argument("file", help="Path to image file")
    ana.add_argument("--prompt", "-p", default="smart", help="Analysis prompt key, custom text, or 'smart'")
    ana.add_argument("--copy", "-c", action="store_true", help="Copy result to clipboard")
    ana.add_argument("--paste", action="store_true", help="Paste result into active app")
    ana.add_argument("--stream", action="store_true", default=True, help="Stream AI results")
    ana.add_argument("--no-stream", dest="stream", action="store_false")

    # annotate
    ann = subparsers.add_parser("annotate", help="Annotate image with OCR bounding boxes")
    ann.add_argument("file", help="Path to image file")

    # history
    hist = subparsers.add_parser("history", help="View screenshot history")
    hist.add_argument("--limit", "-n", type=int, default=10, help="Number of records to show")
    hist.add_argument("--search", "-s", help="Search history by text content")
    hist.add_argument("--clear", action="store_true", help="Clear all history")

    # watch
    watch = subparsers.add_parser("watch", help="Continuous capture — watch for screen changes")
    watch.add_argument("--interval", "-i", type=float, default=2.0, help="Check interval in seconds")
    watch.add_argument("--threshold", "-t", type=float, default=0.05, help="Change threshold (0.0-1.0)")
    watch.add_argument("--analyze", "-a", action="store_true", help="Auto-analyze captured changes")

    # gui
    subparsers.add_parser("gui", help="Launch the menu bar app (macOS only)")

    args = parser.parse_args()
    config = load_config()

    if args.command == "capture":
        cmd_capture(args, config)
    elif args.command == "analyze":
        cmd_analyze(args, config)
    elif args.command == "annotate":
        cmd_annotate(args, config)
    elif args.command == "history":
        cmd_history(args, config)
    elif args.command == "watch":
        cmd_watch(args, config)
    elif args.command == "gui":
        from ai_screenshot.app import main as gui_main
        gui_main()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
