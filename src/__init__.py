"""
YouTube Video Intelligence Pipeline

A comprehensive toolkit for analyzing YouTube videos about automotive products.
Includes video discovery, transcription, sentiment analysis, and report generation.
"""

from .config import (
    PipelineConfig,
    CarModel,
    SCENIC_CONFIG,
    KOLEOS_CONFIG,
    TORRES_CONFIG,
    SORENTO_CONFIG,
    SANTAFE_CONFIG,
    get_default_config,
)

from .youtube_api import (
    YouTubeClient,
    VideoDiscovery,
    VideoInfo,
    Comment,
)

from .transcription import (
    TranscriptionService,
    AudioDownloader,
    WhisperTranscriber,
)

from .analysis import (
    GeminiClient,
    VideoAnalyzer,
    CommentAnalyzer,
    VideoAnalysis,
    CommentAnalysis,
    analysis_to_dataframe,
)

from .reports import (
    ReportGenerator,
    MultiModelReportGenerator,
)

from .pipeline import (
    YouTubeAnalysisPipeline,
    create_pipeline,
)

__version__ = "1.0.0"
__all__ = [
    # Config
    "PipelineConfig",
    "CarModel",
    "SCENIC_CONFIG",
    "KOLEOS_CONFIG",
    "TORRES_CONFIG",
    "SORENTO_CONFIG",
    "SANTAFE_CONFIG",
    "get_default_config",
    # YouTube API
    "YouTubeClient",
    "VideoDiscovery",
    "VideoInfo",
    "Comment",
    # Transcription
    "TranscriptionService",
    "AudioDownloader",
    "WhisperTranscriber",
    # Analysis
    "GeminiClient",
    "VideoAnalyzer",
    "CommentAnalyzer",
    "VideoAnalysis",
    "CommentAnalysis",
    "analysis_to_dataframe",
    # Reports
    "ReportGenerator",
    "MultiModelReportGenerator",
    # Pipeline
    "YouTubeAnalysisPipeline",
    "create_pipeline",
]
