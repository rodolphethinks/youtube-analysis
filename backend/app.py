"""
FastAPI Backend for YouTube Video Intelligence Pipeline
"""

import os
import sys
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import sqlite3

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import PipelineConfig, CarModel, SCENIC_CONFIG, KOLEOS_CONFIG, TORRES_CONFIG, SORENTO_CONFIG, SANTAFE_CONFIG
from src.pipeline import YouTubeAnalysisPipeline
from src.analysis import analysis_to_dataframe


# Database setup
DB_PATH = Path(__file__).parent / "history.db"

def init_db():
    """Initialize SQLite database for job history."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            car_company TEXT,
            car_model TEXT,
            search_query TEXT,
            status TEXT,
            created_at TEXT,
            completed_at TEXT,
            videos_found INTEGER,
            comments_collected INTEGER,
            videos_analyzed INTEGER,
            error TEXT,
            report_filename TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            video_id TEXT,
            video_title TEXT,
            channel_name TEXT,
            sentiment TEXT,
            strengths TEXT,
            weaknesses TEXT,
            summary TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)
    conn.commit()
    conn.close()


# Background job storage
active_jobs = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    init_db()
    yield


app = FastAPI(
    title="YouTube Video Intelligence API",
    description="AI-powered analysis of YouTube car review videos",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class CarModelRequest(BaseModel):
    company: str = Field(..., example="르노")
    model: str = Field(..., example="Scenic E-Tech")
    search_queries: Optional[List[str]] = Field(None, example=["르노 세닉 리뷰", "세닉 전기차"])
    skip_transcription: bool = Field(True, description="Skip audio transcription for faster analysis")
    max_videos: int = Field(20, ge=1, le=200)
    date_from: Optional[str] = Field(None, example="2024-01-01")
    date_to: Optional[str] = Field(None, example="2024-12-31")
    region_code: Optional[str] = Field(None, example="US")
    use_existing_subtitles: bool = Field(False, description="Use existing YouTube subtitles if available")


class PredefinedModelRequest(BaseModel):
    model_key: str = Field(..., example="scenic")
    skip_transcription: bool = True
    max_videos: int = 20
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    region_code: Optional[str] = None
    use_existing_subtitles: bool = False


class JobStatus(BaseModel):
    id: str
    car_company: str
    car_model: str
    search_query: str = ""
    status: str
    created_at: str
    completed_at: Optional[str]
    videos_found: int
    comments_collected: int
    videos_analyzed: int
    error: Optional[str]
    report_filename: Optional[str]


class AnalysisResult(BaseModel):
    id: int
    job_id: str
    video_id: str
    video_title: str
    channel_name: str
    sentiment: str
    strengths: str
    weaknesses: str
    summary: str


# Predefined models mapping
PREDEFINED_MODELS = {
    "scenic": SCENIC_CONFIG,
    "koleos": KOLEOS_CONFIG,
    "torres": TORRES_CONFIG,
    "sorento": SORENTO_CONFIG,
    "santafe": SANTAFE_CONFIG,
}


def run_analysis_job(
    job_id: str, 
    car_model: CarModel, 
    skip_transcription: bool, 
    max_videos: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    region_code: Optional[str] = None,
    use_existing_subtitles: bool = False
):
    """Background task to run the analysis pipeline."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Update status to running
        cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", ("running", job_id))
        conn.commit()
        
        # Get API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        
        # Create pipeline
        config = PipelineConfig(
            google_api_key=api_key,
            output_dir=str(Path(__file__).parent.parent / "output"),
            # Update config with request parameters
            max_search_results=max_videos, # Use max_videos for search results limit roughly
        )
        # Apply filters to config
        if date_from:
            config.published_after = f"{date_from}T00:00:00Z"
        if date_to:
            config.published_before = f"{date_to}T23:59:59Z"
        if region_code:
            config.region_code = region_code
        config.use_existing_subtitles = use_existing_subtitles

        pipeline = YouTubeAnalysisPipeline(config)
        
        # Run discovery
        videos_df, comments_df = pipeline.run_discovery(car_model)
        
        cursor.execute(
            "UPDATE jobs SET videos_found = ?, comments_collected = ? WHERE id = ?",
            (len(videos_df), len(comments_df), job_id)
        )
        conn.commit()
        
        if videos_df.empty:
            cursor.execute(
                "UPDATE jobs SET status = ?, error = ?, completed_at = ? WHERE id = ?",
                ("failed", "No videos found", datetime.now().isoformat(), job_id)
            )
            conn.commit()
            return
        
        # Run transcription if enabled
        if not skip_transcription:
            pipeline.run_transcription(car_model, max_videos=max_videos)
        
        # Run analysis
        video_analyses, comment_analyses = pipeline.run_analysis(car_model)
        
        cursor.execute(
            "UPDATE jobs SET videos_analyzed = ? WHERE id = ?",
            (len(video_analyses), job_id)
        )
        conn.commit()
        
        # Store results
        for analysis in video_analyses:
            # Find video details from URL
            video_id = analysis.video_url.split("v=")[-1] if "v=" in analysis.video_url else analysis.video_url
            video_row = videos_df[videos_df['Video URL'] == analysis.video_url]
            title = video_row['Title'].iloc[0] if not video_row.empty else "Unknown"
            channel = video_row['Channel Title'].iloc[0] if not video_row.empty else "Unknown"
            
            # Convert lists to strings for display
            strengths_str = ", ".join(analysis.key_strengths) if analysis.key_strengths else ""
            weaknesses_str = ", ".join(analysis.key_weaknesses) if analysis.key_weaknesses else ""
            
            cursor.execute("""
                INSERT INTO results (job_id, video_id, video_title, channel_name, sentiment,
                    strengths, weaknesses, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                video_id,
                title,
                channel,
                analysis.overall_sentiment,
                strengths_str,
                weaknesses_str,
                analysis.final_verdict
            ))
        conn.commit()
        
        # Generate reports
        outputs = pipeline.run_reporting(car_model)
        report_filename = None
        for key, path in outputs.items():
            if str(path).endswith('.docx'):
                report_filename = Path(path).name
                break
        
        # Update job as completed
        cursor.execute("""
            UPDATE jobs SET status = ?, completed_at = ?, report_filename = ? WHERE id = ?
        """, ("completed", datetime.now().isoformat(), report_filename, job_id))
        conn.commit()
        
    except Exception as e:
        cursor.execute("""
            UPDATE jobs SET status = ?, error = ?, completed_at = ? WHERE id = ?
        """, ("failed", str(e), datetime.now().isoformat(), job_id))
        conn.commit()
    finally:
        conn.close()


# API Routes
@app.get("/")
async def root():
    """API health check."""
    return {"status": "ok", "message": "YouTube Video Intelligence API"}


@app.get("/api/models")
async def get_predefined_models():
    """Get list of predefined car models."""
    return {
        key: {"company": model.company, "model": model.model}
        for key, model in PREDEFINED_MODELS.items()
    }


@app.post("/api/analyze/predefined", response_model=JobStatus)
async def analyze_predefined(request: PredefinedModelRequest, background_tasks: BackgroundTasks):
    """Start analysis for a predefined car model."""
    if request.model_key not in PREDEFINED_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown model: {request.model_key}")
    
    car_model = PREDEFINED_MODELS[request.model_key]
    return await _create_job(
        car_model, 
        request.skip_transcription, 
        request.max_videos, 
        background_tasks,
        date_from=request.date_from,
        date_to=request.date_to,
        region_code=request.region_code,
        use_existing_subtitles=request.use_existing_subtitles
    )


@app.post("/api/analyze/custom", response_model=JobStatus)
async def analyze_custom(request: CarModelRequest, background_tasks: BackgroundTasks):
    """Start analysis for a custom car model."""
    car_model = CarModel(
        company=request.company,
        model=request.model,
        search_queries=request.search_queries or []
    )
    return await _create_job(
        car_model, 
        request.skip_transcription, 
        request.max_videos, 
        background_tasks,
        date_from=request.date_from,
        date_to=request.date_to,
        region_code=request.region_code,
        use_existing_subtitles=request.use_existing_subtitles
    )


async def _create_job(
    car_model: CarModel, 
    skip_transcription: bool, 
    max_videos: int, 
    background_tasks: BackgroundTasks,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    region_code: Optional[str] = None,
    use_existing_subtitles: bool = False
):
    """Create a new analysis job."""
    job_id = str(uuid.uuid4())[:8]
    search_query = car_model.search_queries[0] if car_model.search_queries else f"{car_model.company} {car_model.model} 리뷰"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO jobs (id, car_company, car_model, search_query, status, created_at, videos_found, 
            comments_collected, videos_analyzed, report_filename)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (job_id, car_model.company, car_model.model, search_query, "pending", 
          datetime.now().isoformat(), 0, 0, 0, None))
    conn.commit()
    conn.close()
    
    # Start background job
    background_tasks.add_task(
        run_analysis_job, 
        job_id, 
        car_model, 
        skip_transcription, 
        max_videos,
        date_from,
        date_to,
        region_code,
        use_existing_subtitles
    )
    
    return JobStatus(
        id=job_id,
        car_company=car_model.company,
        car_model=car_model.model,
        search_query=search_query,
        status="pending",
        created_at=datetime.now().isoformat(),
        completed_at=None,
        videos_found=0,
        comments_collected=0,
        videos_analyzed=0,
        error=None,
        report_filename=None
    )


@app.get("/api/jobs", response_model=List[JobStatus])
async def get_jobs():
    """Get all job history."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [
        JobStatus(
            id=row["id"],
            car_company=row["car_company"],
            car_model=row["car_model"],
            search_query=row["search_query"] or "",
            status=row["status"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
            videos_found=row["videos_found"] or 0,
            comments_collected=row["comments_collected"] or 0,
            videos_analyzed=row["videos_analyzed"] or 0,
            error=row["error"],
            report_filename=row["report_filename"]
        )
        for row in rows
    ]


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str):
    """Get specific job status."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatus(
        id=row["id"],
        car_company=row["car_company"],
        car_model=row["car_model"],
        search_query=row["search_query"] or "",
        status=row["status"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
        videos_found=row["videos_found"] or 0,
        comments_collected=row["comments_collected"] or 0,
        videos_analyzed=row["videos_analyzed"] or 0,
        error=row["error"],
        report_filename=row["report_filename"]
    )


@app.get("/api/jobs/{job_id}/results", response_model=List[AnalysisResult])
async def get_job_results(job_id: str):
    """Get analysis results for a job."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM results WHERE job_id = ?", (job_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [
        AnalysisResult(
            id=row["id"],
            job_id=row["job_id"],
            video_id=row["video_id"],
            video_title=row["video_title"],
            channel_name=row["channel_name"],
            sentiment=row["sentiment"],
            strengths=row["strengths"] or "",
            weaknesses=row["weaknesses"] or "",
            summary=row["summary"] or ""
        )
        for row in rows
    ]


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its results."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM results WHERE job_id = ?", (job_id,))
    cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Download a generated report file."""
    output_dir = Path(__file__).parent.parent / "output"
    file_path = output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path, filename=filename)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
