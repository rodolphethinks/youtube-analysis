# YouTube Video Intelligence Pipeline

A comprehensive Python toolkit for analyzing YouTube videos about automotive products. Extract insights from video content, comments, and transcriptions using AI-powered analysis.

## Features

- 🔍 **Video Discovery** - Search YouTube API for relevant videos
- 💬 **Comment Collection** - Fetch top comments for sentiment analysis  
- 🎙️ **Audio Transcription** - Download and transcribe using OpenAI Whisper
- 🤖 **AI Analysis** - Sentiment, strengths/weaknesses extraction using Google Gemini
- 👥 **Persona Generation** - Build user personas from comment patterns
- 📊 **Report Generation** - Create Word/Excel reports

## Project Structure

```
Youtube/
├── src/
│   ├── __init__.py          # Package exports
│   ├── config.py             # Configuration and car model definitions
│   ├── youtube_api.py        # YouTube Data API client
│   ├── transcription.py      # Audio download and Whisper transcription
│   ├── analysis.py           # Gemini AI analysis
│   ├── reports.py            # Report generation (Word, Excel)
│   └── pipeline.py           # Main orchestration
├── output/                   # Generated reports
├── audio/                    # Temporary audio files
├── downloads/                # Downloaded media
├── main.py                   # CLI entry point
├── run.py                    # Programmatic API
├── requirements.txt          # Python dependencies
└── README.md
```

## Installation

```bash
# Clone or download the project
cd Youtube

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

## Environment Setup

Set your Google API key:

```powershell
# Windows PowerShell
$env:GOOGLE_API_KEY = "your_api_key_here"

# Or add to .env file
echo GOOGLE_API_KEY=your_api_key_here > .env
```

## Quick Start

### Option 1: Command Line Interface

```bash
# Analyze Renault Scenic E-Tech (predefined model)
python main.py --model scenic

# Skip transcription (faster, comments-only analysis)
python main.py --model scenic --skip-transcription

# Analyze Grand Koleos with limited transcription
python main.py --model koleos --max-transcribe 5

# Custom car model
python main.py --company "Toyota" --model-name "RAV4" --queries "Toyota RAV4 review,RAV4 2024"

# Run specific pipeline stage
python main.py --model scenic --stage discovery
```

### Option 2: Python Script

```python
from src import YouTubeAnalysisPipeline, PipelineConfig, SCENIC_CONFIG
import os

# Configure
config = PipelineConfig(
    google_api_key=os.getenv('GOOGLE_API_KEY'),
    max_search_results=50,
    published_after="2024-04-01T00:00:00Z",
)

# Initialize and run
pipeline = YouTubeAnalysisPipeline(config)
outputs = pipeline.run_full_pipeline(
    SCENIC_CONFIG,
    max_videos_to_transcribe=10,
    skip_transcription=True
)

print(f"Generated: {outputs}")
```

### Option 3: Quick Functions

```python
from run import analyze_scenic, analyze_car, compare_models

# Predefined model
outputs = analyze_scenic()

# Custom model
outputs = analyze_car("Toyota", "RAV4")

# Compare multiple models
results = compare_models(["scenic", "koleos", "torres"])
```

## CLI Reference

```
usage: main.py [-h] (--model {scenic,koleos,torres,sorento,santafe} | --company COMPANY)
               [--model-name MODEL_NAME] [--queries QUERIES]
               [--skip-transcription] [--max-transcribe MAX_TRANSCRIBE]
               [--max-search MAX_SEARCH] [--published-after PUBLISHED_AFTER]
               [--output-dir OUTPUT_DIR] [--no-word] [--no-excel]
               [--stage {discovery,transcription,analysis,reports,all}]
               [--whisper-model {tiny,base,small,medium,large-v3}]

Options:
  --model, -m          Use predefined car model (scenic, koleos, torres, sorento, santafe)
  --company            Custom car company name
  --model-name         Custom car model name (required with --company)
  --queries            Comma-separated search queries
  --skip-transcription, -s  Skip audio transcription
  --max-transcribe     Max videos to transcribe (default: 20)
  --max-search         Max search results per query (default: 50)
  --output-dir, -o     Output directory (default: output)
  --stage              Run specific stage: discovery, transcription, analysis, reports, all
  --whisper-model      Whisper size: tiny, base, small, medium, large-v3
```

## Predefined Car Models

| Model | Company | Description |
|-------|---------|-------------|
| `scenic` | Renault | Scenic E-Tech electric |
| `koleos` | Renault Korea | Grand Koleos |
| `torres` | KGM | Torres Hybrid |
| `sorento` | Kia | Sorento |
| `santafe` | Hyundai | Santa Fe |

## Output Files

| File | Description |
|------|-------------|
| `{model}_report.docx` | Word document with executive summary |
| `{model}_report.txt` | Plain text version of the report |
| `{model}_analysis.xlsx` | Excel file with video details, analysis, comments |
| `{model}_comments.csv` | Raw comments data |
| `comparison.xlsx` | Multi-model comparison (when comparing) |
| `sentiment_comparison.png` | Visualization (when comparing) |

## API Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    YouTubeAnalysisPipeline                  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ YouTubeClient│  │ GeminiClient │  │ TranscriptionSvc │   │
│  └──────┬──────┘  └──────┬───────┘  └────────┬─────────┘   │
│         │                │                    │             │
│  ┌──────▼──────┐  ┌──────▼───────┐  ┌────────▼─────────┐   │
│  │VideoDiscovery│  │ VideoAnalyzer│  │WhisperTranscriber│   │
│  │             │  │CommentAnalyzer│  │ AudioDownloader  │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
│                          │                                  │
│                   ┌──────▼───────┐                         │
│                   │ReportGenerator│                         │
│                   └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## Requirements

- Python 3.9+
- FFmpeg (for audio processing)
- CUDA-capable GPU (recommended for Whisper transcription)

## API Keys Required

| Service | Usage |
|---------|-------|
| Google Cloud API | YouTube Data API v3, Generative AI (Gemini) |

Enable these APIs in [Google Cloud Console](https://console.cloud.google.com/).

## License

MIT
