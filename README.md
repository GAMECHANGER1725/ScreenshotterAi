# ScreenshotterAI

An AI-powered screenshot tool for macOS — capture your screen, extract text with OCR, and analyze content with Claude's vision API. Inspired by [Wispr Flow](https://wispr.com).

## Features

- **Screen Capture** — Region selection, full screen, active window, timed capture
- **AI Vision Analysis** — Claude-powered analysis with 10 built-in modes (describe, extract text, summarize, code, debug, data, and more)
- **Streaming Results** — See AI analysis appear in real-time, Wispr Flow-style
- **Smart Mode** — Auto-detects content type (code, receipt, document, UI) and picks the best analysis
- **Floating Overlay** — Transparent always-on-top results panel with copy/paste buttons
- **Quick Paste** — Paste extracted text directly into the active application
- **OCR Text Extraction** — Local text extraction using Tesseract
- **Continuous Capture** — Watch mode that detects screen changes and auto-captures
- **Image Annotation** — Highlight regions, draw arrows, add labels, blur sensitive areas
- **Global Hotkeys** — `⌘⇧S` region, `⌘⇧A` full screen, `⌘⇧W` window
- **Menu Bar App** — Lives in your macOS menu bar for quick access
- **Clipboard Integration** — Results auto-copied to clipboard
- **Screenshot History** — Searchable history of all captures and analyses
- **Kaggle Datasets** — Download real-world test data for benchmarking with accuracy reports

## Quick Start

### Prerequisites

- macOS (for screen capture and menu bar app)
- Python 3.10+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) for local text extraction
- An [Anthropic API key](https://console.anthropic.com/) for AI analysis

### Install

```bash
# Install Tesseract (macOS)
brew install tesseract

# Clone and install
git clone https://github.com/gamechanger1725/ScreenshotterAI.git
cd ScreenshotterAI
pip install -e ".[dev]"

# Set your API key
export ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### Run the Menu Bar App

```bash
ai-screenshot gui
# or
ai-screenshot-gui
```

A camera icon (📸) appears in your menu bar. Click it to capture, or use hotkeys.

### CLI Usage

```bash
# Capture a region with smart auto-detection
ai-screenshot capture --mode region --smart

# Capture full screen with streaming AI analysis
ai-screenshot capture --mode fullscreen --analyze --stream

# Capture with a 5-second delay
ai-screenshot capture --mode fullscreen --delay 5 --all

# Analyze an existing image (smart mode auto-detects content type)
ai-screenshot analyze path/to/image.png

# Analyze with a specific mode
ai-screenshot analyze path/to/image.png --prompt code

# Ask a question about a screenshot
ai-screenshot capture --file screenshot.png --ask "What error is shown?"

# Paste results directly into the active app
ai-screenshot capture --mode region --analyze --paste

# Annotate an image with OCR bounding boxes
ai-screenshot annotate path/to/image.png

# Watch for screen changes (continuous capture)
ai-screenshot watch --interval 2 --threshold 0.05 --analyze

# View history
ai-screenshot history
ai-screenshot history --search "error"
```

### Analysis Modes

| Mode | Description |
|------|-------------|
| `smart` | Auto-detect content type and pick the best mode |
| `describe` | Detailed description of screenshot content |
| `extract_text` | Extract all visible text, preserving layout |
| `summarize` | 2-3 sentence summary |
| `code` | Extract and format any visible code |
| `ui_elements` | List all UI elements with labels |
| `translate` | Extract text and translate to English |
| `explain` | Explain what's happening in the screenshot |
| `debug` | Analyze errors/warnings and suggest fixes |
| `accessibility` | Evaluate UI for accessibility issues |
| `data` | Extract structured data (tables, lists, forms) |

## Kaggle Dataset Testing

Download real-world image datasets from Kaggle for testing and benchmarking:

```bash
# List available datasets
ai-screenshot-kaggle list

# Download a dataset
ai-screenshot-kaggle download textocr
ai-screenshot-kaggle download receipts

# Download any Kaggle dataset by slug
ai-screenshot-kaggle download owner/dataset-name

# Batch test with benchmarking report
ai-screenshot-kaggle test kaggle_data/receipts --max 10 --report
```

### Available Datasets

| Name | Category | Description |
|------|----------|-------------|
| `textocr` | OCR | 900K+ text annotations on real images |
| `screenshots` | UI | Mobile/web UI screenshots |
| `receipts` | OCR | Receipt images for structured document OCR |
| `documents` | OCR | Scanned docs, forms, and papers |
| `handwriting` | OCR | Handwriting recognition samples |
| `scene-text` | OCR | Text in natural images (signs, labels) |
| `icons` | UI | 50 categories of app icons |
| `charts` | Data | Chart images for data extraction |

### Kaggle Setup

```bash
# Option 1: Environment variables
export KAGGLE_USERNAME=your_username
export KAGGLE_KEY=your_api_key

# Option 2: kaggle.json file
mkdir -p ~/.kaggle
echo '{"username":"your_username","key":"your_api_key"}' > ~/.kaggle/kaggle.json
chmod 600 ~/.kaggle/kaggle.json
```

## Configuration

Config is stored at `~/.ai_screenshot/config.json`. You can also set values via environment variables:

| Env Var | Description |
|---------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key for AI analysis |
| `AI_MODEL` | Claude model (default: `claude-sonnet-4-20250514`) |
| `SCREENSHOT_DIR` | Where to save screenshots (default: `~/ai_screenshots`) |
| `KAGGLE_USERNAME` | Kaggle API username |
| `KAGGLE_KEY` | Kaggle API key |

### Config Options

| Option | Default | Description |
|--------|---------|-------------|
| `smart_mode` | `true` | Auto-detect content type |
| `streaming` | `true` | Stream AI results in real-time |
| `show_overlay` | `true` | Show floating results overlay |
| `auto_copy` | `true` | Auto-copy results to clipboard |
| `auto_paste` | `false` | Auto-paste results into active app |
| `auto_analyze` | `true` | Run AI analysis on capture |
| `watch_interval` | `2.0` | Screen watch check interval (seconds) |
| `watch_threshold` | `0.05` | Screen change detection threshold |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run a specific test
pytest tests/test_smart.py -v
```

## Architecture

```
ai_screenshot/
  app.py          # macOS menu bar application (rumps)
  cli.py          # Command-line interface (argparse + rich)
  capture.py      # Screenshot capture via macOS screencapture
  analyzer.py     # Claude vision API (standard + streaming)
  ocr.py          # Tesseract OCR wrapper
  smart.py        # Smart content detection (auto-picks analysis mode)
  overlay.py      # Floating overlay window (tkinter)
  watcher.py      # Continuous screen capture + timed capture
  annotate.py     # Image annotation (highlights, arrows, text, blur)
  hotkeys.py      # Global hotkey listener (pynput)
  history.py      # JSON-backed screenshot history
  clipboard.py    # Clipboard utilities + quick paste
  config.py       # Configuration management
  kaggle_data.py  # Kaggle dataset downloader + benchmarking
```

## License

MIT
