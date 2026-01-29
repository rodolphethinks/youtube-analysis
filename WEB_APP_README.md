# YouTube Video Intelligence - Web Application

A professional web application for analyzing YouTube car review videos using AI.

## Architecture

```
├── backend/            # FastAPI backend
│   └── app.py          # API server with SQLite database
├── frontend/           # React + TypeScript frontend
│   ├── src/
│   │   ├── pages/      # Page components
│   │   ├── api.ts      # API client
│   │   └── App.tsx     # Main app with routing
│   └── package.json
└── src/                # Core analysis pipeline
    ├── config.py       # Configuration classes
    ├── youtube_api.py  # YouTube API integration
    ├── transcription.py# Audio transcription
    ├── analysis.py     # AI analysis with Gemini
    ├── reports.py      # Report generation
    └── pipeline.py     # Main orchestration
```

## Prerequisites

1. **Python 3.9+** with dependencies:
   ```bash
   pip install fastapi uvicorn google-generativeai google-api-python-client yt-dlp transformers torch pandas python-docx
   ```

2. **Node.js 18+** for frontend

3. **API Keys** (set as environment variables):
   - `GOOGLE_API_KEY` - Google/Gemini API key for AI analysis and YouTube Data API

## Running the Application

### Option 1: Using the start script

```powershell
# Windows PowerShell
.\start-app.ps1
```

### Option 2: Manual start

**Terminal 1 - Backend:**
```bash
cd backend
$env:GOOGLE_API_KEY="your-api-key"
python -m uvicorn app:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173** in your browser.

## Features

### Dashboard
- Overview statistics (total analyses, videos analyzed, success rate)
- Recent analysis jobs with status indicators
- Quick access to start new analysis

### New Analysis
- **Predefined Models**: Renault Scenic, Grand Koleos, Torres Hybrid, Sorento, Santa Fe
- **Custom Models**: Enter any car company/model with custom search queries
- Configurable options:
  - Enable/disable audio transcription (faster without)
  - Set maximum videos to analyze

### History
- Full list of all analysis jobs
- Search and filter by car model or status
- Delete old analyses

### Job Details
- Real-time status updates while analysis is running
- Sentiment distribution charts (pie chart)
- Summary statistics (positive/negative/neutral counts)
- Detailed results table with:
  - Video title and link
  - Sentiment classification
  - Key strengths and weaknesses
- Download reports (Word document, CSV data)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/models` | Get predefined car models |
| POST | `/api/analyze/predefined` | Start analysis with predefined model |
| POST | `/api/analyze/custom` | Start analysis with custom model |
| GET | `/api/jobs` | Get all analysis jobs |
| GET | `/api/jobs/{id}` | Get specific job status |
| GET | `/api/jobs/{id}/results` | Get analysis results |
| DELETE | `/api/jobs/{id}` | Delete a job |
| GET | `/api/download/{filename}` | Download report file |

## Tech Stack

- **Backend**: FastAPI, SQLite, Pydantic
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS
- **Charts**: Recharts
- **Icons**: Lucide React
- **AI**: Google Gemini 2.0 Flash
- **Transcription**: OpenAI Whisper (local)
