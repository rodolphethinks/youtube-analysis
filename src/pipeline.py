"""
Main pipeline orchestration module.
Coordinates all components for end-to-end video analysis.
"""

from typing import Dict, List, Optional, Tuple
from pathlib import Path
import pandas as pd

from .config import PipelineConfig, CarModel
from .youtube_api import YouTubeClient, VideoDiscovery
from .transcription import TranscriptionService
from .analysis import (
    GeminiClient, VideoAnalyzer, CommentAnalyzer,
    VideoAnalysis, CommentAnalysis, analysis_to_dataframe
)
from .reports import ReportGenerator, MultiModelReportGenerator


class YouTubeAnalysisPipeline:
    """
    End-to-end pipeline for YouTube video analysis.
    
    Pipeline stages:
    1. Video Discovery - Search and fetch video metadata
    2. Comment Collection - Gather top comments
    3. Transcription - Download audio and transcribe
    4. Analysis - AI-powered sentiment and content analysis
    5. Report Generation - Create output files
    """
    
    def __init__(self, config: PipelineConfig):
        """Initialize pipeline with configuration."""
        self.config = config
        
        # Initialize clients
        self.youtube_client = YouTubeClient(config.google_api_key)
        self.gemini_client = GeminiClient(config.google_api_key, config.gemini_model)
        
        # Initialize services
        self.video_discovery = VideoDiscovery(self.youtube_client, config)
        self.video_analyzer = VideoAnalyzer(self.gemini_client)
        self.comment_analyzer = CommentAnalyzer(self.gemini_client)
        self.report_generator = ReportGenerator(self.gemini_client, config.output_dir)
        
        # Results storage
        self.results: Dict[str, Dict] = {}
    
    def run_discovery(self, car_model: CarModel) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Stage 1 & 2: Discover videos and collect comments.
        
        Returns:
            Tuple of (videos_df, comments_df)
        """
        print(f"\n{'='*60}")
        print(f"STAGE 1-2: Video Discovery & Comment Collection")
        print(f"Target: {car_model.company} {car_model.model}")
        print(f"{'='*60}\n")
        
        # Discover videos
        videos_df = self.video_discovery.discover_videos(car_model)
        
        if videos_df.empty:
            print("No videos found!")
            return pd.DataFrame(), pd.DataFrame()
        
        # Collect comments
        comments_df = self.video_discovery.fetch_all_comments(videos_df)
        
        # Save intermediate results
        model_id = car_model.identifier
        self.results[model_id] = {
            'videos_df': videos_df,
            'comments_df': comments_df,
            'car_model': car_model
        }
        
        return videos_df, comments_df
    
    def run_transcription(
        self, 
        car_model: CarModel,
        video_urls: Optional[List[str]] = None,
        max_videos: int = 20,
        whisper_model: str = "large-v3"
    ) -> Dict[str, str]:
        """
        Stage 3: Transcribe video audio.
        
        Args:
            car_model: Car model being analyzed
            video_urls: Specific URLs to transcribe (uses discovered videos if None)
            max_videos: Maximum number of videos to transcribe
            whisper_model: Whisper model size
            
        Returns:
            Dictionary mapping URLs to transcriptions
        """
        print(f"\n{'='*60}")
        print(f"STAGE 3: Video Transcription")
        print(f"{'='*60}\n")
        
        model_id = car_model.identifier
        
        if video_urls is None:
            if model_id not in self.results or 'videos_df' not in self.results[model_id]:
                print("No videos discovered yet. Run discovery first.")
                return {}
            video_urls = self.results[model_id]['videos_df']['Video URL'].tolist()[:max_videos]
        
        transcription_service = TranscriptionService(
            self.config,
            whisper_model=whisper_model,
            cleanup_audio=True
        )
        
        transcriptions = transcription_service.transcribe_videos(video_urls)
        
        # Store results
        if model_id not in self.results:
            self.results[model_id] = {}
        self.results[model_id]['transcriptions'] = transcriptions
        
        return transcriptions
    
    def run_analysis(
        self, 
        car_model: CarModel,
        transcriptions: Optional[Dict[str, str]] = None
    ) -> Tuple[List[VideoAnalysis], Dict[str, CommentAnalysis]]:
        """
        Stage 4: Analyze transcripts and comments.
        
        Returns:
            Tuple of (video_analyses, comment_analyses)
        """
        print(f"\n{'='*60}")
        print(f"STAGE 4: AI-Powered Analysis")
        print(f"{'='*60}\n")
        
        model_id = car_model.identifier
        
        # Get transcriptions
        if transcriptions is None:
            if model_id not in self.results or 'transcriptions' not in self.results[model_id]:
                print("No transcriptions available. Run transcription first.")
                return [], {}
            transcriptions = self.results[model_id]['transcriptions']
        
        # Analyze transcripts
        video_analyses = self.video_analyzer.analyze_multiple(transcriptions, car_model)
        
        # Analyze comments
        comments_df = self.results.get(model_id, {}).get('comments_df', pd.DataFrame())
        comment_analyses = {}
        
        if not comments_df.empty:
            # Group comments by video
            comments_by_video = comments_df.groupby("Video ID").apply(
                lambda x: "\n".join(x["Comment"].tolist())
            ).to_dict()
            
            # Convert Video ID to URL
            videos_df = self.results[model_id].get('videos_df', pd.DataFrame())
            if not videos_df.empty:
                id_to_url = dict(zip(videos_df['Video ID'], videos_df['Video URL']))
                comments_by_url = {
                    id_to_url.get(vid, vid): comments 
                    for vid, comments in comments_by_video.items()
                    if vid in id_to_url
                }
                comment_analyses = self.comment_analyzer.analyze_all_comments(
                    comments_by_url, car_model
                )
        
        # Store results
        self.results[model_id]['video_analyses'] = video_analyses
        self.results[model_id]['comment_analyses'] = comment_analyses
        
        return video_analyses, comment_analyses
    
    def run_reporting(
        self,
        car_model: CarModel,
        generate_word: bool = True,
        generate_excel: bool = True
    ) -> Dict[str, Path]:
        """
        Stage 5: Generate reports.
        
        Returns:
            Dictionary of output file paths
        """
        print(f"\n{'='*60}")
        print(f"STAGE 5: Report Generation")
        print(f"{'='*60}\n")
        
        model_id = car_model.identifier
        outputs = {}
        
        if model_id not in self.results:
            print("No analysis results available. Run previous stages first.")
            return outputs
        
        results = self.results[model_id]
        
        # Convert analyses to DataFrame
        video_analyses = results.get('video_analyses', [])
        analysis_df = analysis_to_dataframe(video_analyses) if video_analyses else pd.DataFrame()
        
        # Generate summary report
        if not analysis_df.empty:
            print("Generating summary report...")
            summary = self.report_generator.generate_summary_report(analysis_df, car_model)
            
            if generate_word:
                word_path = self.report_generator.save_to_word(
                    summary, 
                    f"{model_id}_report.docx",
                    car_model
                )
                outputs['word_report'] = word_path
            
            # Always save text version
            text_path = self.report_generator.save_to_text(
                summary,
                f"{model_id}_report.txt"
            )
            outputs['text_report'] = text_path
        
        # Generate Excel
        if generate_excel:
            videos_df = results.get('videos_df', pd.DataFrame())
            comments_df = results.get('comments_df', pd.DataFrame())
            
            excel_path = self.report_generator.save_to_excel(
                videos_df=videos_df,
                analysis_df=analysis_df,
                comments_df=comments_df,
                filename=f"{model_id}_analysis.xlsx",
                car_model=car_model
            )
            outputs['excel_report'] = excel_path
        
        # Save comments CSV
        comments_df = results.get('comments_df', pd.DataFrame())
        if not comments_df.empty:
            csv_path = self.report_generator.save_comments_csv(
                comments_df,
                f"{model_id}_comments.csv"
            )
            outputs['comments_csv'] = csv_path
        
        return outputs
    
    def run_full_pipeline(
        self,
        car_model: CarModel,
        max_videos_to_transcribe: int = 20,
        skip_transcription: bool = False
    ) -> Dict[str, Path]:
        """
        Run the complete analysis pipeline.
        
        Args:
            car_model: Car model to analyze
            max_videos_to_transcribe: Limit on transcription count
            skip_transcription: Skip transcription (use for comments-only analysis)
            
        Returns:
            Dictionary of output file paths
        """
        print(f"\n{'#'*60}")
        print(f"# STARTING FULL PIPELINE")
        print(f"# Car Model: {car_model.company} {car_model.model}")
        print(f"{'#'*60}\n")
        
        # Stage 1-2: Discovery
        videos_df, comments_df = self.run_discovery(car_model)
        
        if videos_df.empty:
            print("Pipeline aborted: No videos found")
            return {}
        
        # Stage 3: Transcription (optional)
        if not skip_transcription:
            transcriptions = self.run_transcription(
                car_model, 
                max_videos=max_videos_to_transcribe
            )
        
        # Stage 4: Analysis
        self.run_analysis(car_model)
        
        # Stage 5: Reporting
        outputs = self.run_reporting(car_model)
        
        print(f"\n{'#'*60}")
        print(f"# PIPELINE COMPLETE")
        print(f"# Generated {len(outputs)} output files")
        print(f"{'#'*60}\n")
        
        return outputs


def create_pipeline(api_key: Optional[str] = None) -> YouTubeAnalysisPipeline:
    """Factory function to create a pipeline with default configuration."""
    import os
    
    if api_key is None:
        api_key = os.getenv('GOOGLE_API_KEY')
    
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not provided and not found in environment")
    
    config = PipelineConfig(google_api_key=api_key)
    return YouTubeAnalysisPipeline(config)
