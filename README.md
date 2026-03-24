# AI Screenshot Tool

An AI-powered screenshot tool for macOS — capture your screen, extract text with OCR, and analyze content with Claude's vision API. Inspired by [Wispr Flow](https://wispr.com).

## Features

- **Screen Capture** — Region selection, full screen, or active window via macOS native `screencapture`
- **AI Vision Analysis** — Send screenshots to Claude for intelligent understanding (describe, extract text, summarize, detect code, identify UI elements)
- **OCR Text Extraction** — Local text extraction using Tesseract
- **Global Hotkeys** — `⌘⇧S` region, `⌘⇧A` full screen, `⌘⇧W` window
- **Menu Bar App** — Lives in your macOS menu bar for quick access
- **Clipboard Integration** — Results auto-copied to clipboard
- **Screenshot History** — Searchable history of all captures and analyses
- **Kaggle Datasets** — Download real-world test data from Kaggle for benchmarking

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
git clone https://github.com/gamechanger1725/wheelofnames.git
cd wheelofnames
pip install -e ".[dev]"

# Set your API key
export ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### Run the Menu Bar App

```bash
ai-screenshot gui
# or
python -m ai_screenshot gui
```

A camera icon (📸) appears in your menu bar. Click it to capture, or use hotkeys.

### CLI Usage

```bash
# Capture a region and run OCR + AI analysis
ai-screenshot capture --mode region --all

# Capture full screen, extract text only
ai-screenshot capture --mode fullscreen --ocr --copy

# Analyze an existing image
ai-screenshot analyze path/to/image.png --prompt extract_text

# Ask a question about a screenshot
ai-screenshot capture --file screenshot.png --ask "What error is shown?"

# View history
ai-screenshot history
ai-screenshot history --search "error"
```

### Analysis Modes

| Mode | Description |
|------|-------------|
| `describe` | Detailed description of screenshot content |
| `extract_text` | Extract all visible text, preserving layout |
| `summarize` | 2-3 sentence summary |
| `code` | Extract and format any visible code |
| `ui_elements` | List all UI elements with labels |
| `translate` | Extract text and translate to English |
| `explain` | Explain what's happening in the screenshot |

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

# Batch test OCR on downloaded images
ai-screenshot-kaggle test kaggle_data/receipts --max 10
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

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run a specific test
pytest tests/test_history.py -v
```

## Architecture

```
ai_screenshot/
  app.py          # macOS menu bar application (rumps)
  cli.py          # Command-line interface (argparse + rich)
  capture.py      # Screenshot capture via macOS screencapture
  analyzer.py     # Claude vision API integration
  ocr.py          # Tesseract OCR wrapper
  hotkeys.py      # Global hotkey listener (pynput)
  history.py      # JSON-backed screenshot history
  clipboard.py    # System clipboard utilities
  config.py       # Configuration management
  kaggle_data.py  # Kaggle dataset downloader
```

## License

MIT
