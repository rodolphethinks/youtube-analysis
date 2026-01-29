#!/usr/bin/env python3
"""
YouTube Video Intelligence Pipeline - Main Entry Point

Usage:
    python main.py --model scenic
    python main.py --model scenic --skip-transcription
    python main.py --company "Toyota" --model-name "RAV4" --queries "Toyota RAV4 review,RAV4 test drive"
"""

import argparse
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import (
    PipelineConfig,
    CarModel,
    SCENIC_CONFIG,
    KOLEOS_CONFIG,
    TORRES_CONFIG,
    SORENTO_CONFIG,
    SANTAFE_CONFIG,
)
from src.pipeline import YouTubeAnalysisPipeline


# Predefined model mapping
PREDEFINED_MODELS = {
    "scenic": SCENIC_CONFIG,
    "koleos": KOLEOS_CONFIG,
    "torres": TORRES_CONFIG,
    "sorento": SORENTO_CONFIG,
    "santafe": SANTAFE_CONFIG,
}


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="YouTube Video Intelligence Pipeline for Automotive Market Research",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze Renault Scenic E-Tech (predefined)
  python main.py --model scenic
  
  # Skip transcription (faster, comments-only analysis)
  python main.py --model scenic --skip-transcription
  
  # Custom car model
  python main.py --company "Toyota" --model-name "RAV4" --queries "Toyota RAV4 review,RAV4 2024"
  
  # Limit transcription count
  python main.py --model koleos --max-transcribe 5
        """
    )
    
    # Model selection (mutually exclusive)
    model_group = parser.add_mutually_exclusive_group(required=True)
    model_group.add_argument(
        "--model", "-m",
        choices=list(PREDEFINED_MODELS.keys()),
        help="Use a predefined car model configuration"
    )
    model_group.add_argument(
        "--company",
        help="Car company name (for custom model)"
    )
    
    # Custom model options
    parser.add_argument(
        "--model-name",
        help="Car model name (required with --company)"
    )
    parser.add_argument(
        "--queries",
        help="Comma-separated search queries (optional with --company)"
    )
    
    # Pipeline options
    parser.add_argument(
        "--skip-transcription", "-s",
        action="store_true",
        help="Skip audio transcription (faster, comments-only analysis)"
    )
    parser.add_argument(
        "--max-transcribe",
        type=int,
        default=20,
        help="Maximum number of videos to transcribe (default: 20)"
    )
    parser.add_argument(
        "--max-search",
        type=int,
        default=50,
        help="Maximum search results per query (default: 50)"
    )
    parser.add_argument(
        "--published-after",
        default="2024-04-01T00:00:00Z",
        help="Only include videos published after this date (ISO format)"
    )
    
    # Output options
    parser.add_argument(
        "--output-dir", "-o",
        default="output",
        help="Output directory for reports (default: output)"
    )
    parser.add_argument(
        "--no-word",
        action="store_true",
        help="Skip Word document generation"
    )
    parser.add_argument(
        "--no-excel",
        action="store_true",
        help="Skip Excel file generation"
    )
    
    # Stage control
    parser.add_argument(
        "--stage",
        choices=["discovery", "transcription", "analysis", "reports", "all"],
        default="all",
        help="Run specific pipeline stage (default: all)"
    )
    
    # Whisper options
    parser.add_argument(
        "--whisper-model",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        default="large-v3",
        help="Whisper model size for transcription (default: large-v3)"
    )
    
    args = parser.parse_args()
    
    # Validation
    if args.company and not args.model_name:
        parser.error("--model-name is required when using --company")
    
    return args


def get_car_model(args) -> CarModel:
    """Get car model from arguments."""
    if args.model:
        return PREDEFINED_MODELS[args.model]
    else:
        queries = args.queries.split(",") if args.queries else None
        return CarModel(
            company=args.company,
            model=args.model_name,
            search_queries=queries or []
        )


def run_pipeline(args):
    """Run the analysis pipeline."""
    # Get API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable not set")
        print("Set it with: set GOOGLE_API_KEY=your_key_here")
        sys.exit(1)
    
    # Get car model
    car_model = get_car_model(args)
    print(f"\n🚗 Analyzing: {car_model.company} {car_model.model}")
    
    # Create configuration
    config = PipelineConfig(
        google_api_key=api_key,
        max_search_results=args.max_search,
        published_after=args.published_after,
        output_dir=args.output_dir,
    )
    
    # Initialize pipeline
    pipeline = YouTubeAnalysisPipeline(config)
    
    # Run stages based on selection
    if args.stage == "all":
        outputs = pipeline.run_full_pipeline(
            car_model=car_model,
            max_videos_to_transcribe=args.max_transcribe,
            skip_transcription=args.skip_transcription,
        )
    else:
        outputs = run_individual_stage(pipeline, car_model, args)
    
    # Print results
    if outputs:
        print("\n" + "=" * 60)
        print("📁 Generated Files:")
        for name, path in outputs.items():
            print(f"   {name}: {path}")
        print("=" * 60)
    
    return outputs


def run_individual_stage(pipeline, car_model, args):
    """Run a specific pipeline stage."""
    outputs = {}
    
    if args.stage == "discovery":
        videos_df, comments_df = pipeline.run_discovery(car_model)
        print(f"\nVideos found: {len(videos_df)}")
        print(f"Comments collected: {len(comments_df)}")
        
    elif args.stage == "transcription":
        # Need discovery first
        pipeline.run_discovery(car_model)
        transcriptions = pipeline.run_transcription(
            car_model,
            max_videos=args.max_transcribe,
            whisper_model=args.whisper_model
        )
        print(f"\nTranscribed: {len(transcriptions)} videos")
        
    elif args.stage == "analysis":
        # Need discovery first
        pipeline.run_discovery(car_model)
        if not args.skip_transcription:
            pipeline.run_transcription(car_model, max_videos=args.max_transcribe)
        video_analyses, comment_analyses = pipeline.run_analysis(car_model)
        print(f"\nVideo analyses: {len(video_analyses)}")
        print(f"Comment analyses: {len(comment_analyses)}")
        
    elif args.stage == "reports":
        # Run full pipeline up to reports
        pipeline.run_discovery(car_model)
        if not args.skip_transcription:
            pipeline.run_transcription(car_model, max_videos=args.max_transcribe)
        pipeline.run_analysis(car_model)
        outputs = pipeline.run_reporting(
            car_model,
            generate_word=not args.no_word,
            generate_excel=not args.no_excel
        )
    
    return outputs


def main():
    """Main entry point."""
    args = parse_args()
    
    try:
        run_pipeline(args)
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
