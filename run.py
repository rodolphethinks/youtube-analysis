"""
YouTube Video Intelligence Pipeline - Quick Start Script

This script provides a simple programmatic interface for common use cases.
For CLI usage, use main.py instead.
"""

import os
from pathlib import Path


def analyze_car(
    company: str,
    model: str,
    search_queries: list = None,
    skip_transcription: bool = True,
    max_videos: int = 20,
    output_dir: str = "output"
):
    """
    Analyze YouTube videos for a car model.
    
    Args:
        company: Car company name (e.g., "Renault", "Toyota")
        model: Car model name (e.g., "Scenic E-Tech", "RAV4")
        search_queries: List of YouTube search queries (auto-generated if None)
        skip_transcription: Skip audio transcription for faster analysis
        max_videos: Maximum videos to transcribe
        output_dir: Directory for output files
        
    Returns:
        Dictionary of output file paths
        
    Example:
        >>> outputs = analyze_car("르노", "Scenic E-Tech", skip_transcription=True)
        >>> print(outputs)
    """
    from src.config import PipelineConfig, CarModel
    from src.pipeline import YouTubeAnalysisPipeline
    
    # Get API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    
    # Create car model
    car_model = CarModel(
        company=company,
        model=model,
        search_queries=search_queries or []
    )
    
    # Create config
    config = PipelineConfig(
        google_api_key=api_key,
        output_dir=output_dir,
    )
    
    # Run pipeline
    pipeline = YouTubeAnalysisPipeline(config)
    outputs = pipeline.run_full_pipeline(
        car_model=car_model,
        max_videos_to_transcribe=max_videos,
        skip_transcription=skip_transcription,
    )
    
    return outputs


def analyze_scenic():
    """Quick analysis of Renault Scenic E-Tech."""
    from src.config import SCENIC_CONFIG
    return _run_predefined(SCENIC_CONFIG)


def analyze_koleos():
    """Quick analysis of Renault Grand Koleos."""
    from src.config import KOLEOS_CONFIG
    return _run_predefined(KOLEOS_CONFIG)


def analyze_torres():
    """Quick analysis of KGM Torres Hybrid."""
    from src.config import TORRES_CONFIG
    return _run_predefined(TORRES_CONFIG)


def _run_predefined(car_model, skip_transcription=True):
    """Run pipeline with predefined car model."""
    from src.config import PipelineConfig
    from src.pipeline import YouTubeAnalysisPipeline
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    
    config = PipelineConfig(google_api_key=api_key)
    pipeline = YouTubeAnalysisPipeline(config)
    
    return pipeline.run_full_pipeline(
        car_model=car_model,
        skip_transcription=skip_transcription,
    )


# Quick comparison functions
def compare_models(model_names: list, skip_transcription: bool = True):
    """
    Compare multiple car models.
    
    Args:
        model_names: List of predefined model names 
                    ("scenic", "koleos", "torres", "sorento", "santafe")
        skip_transcription: Skip audio transcription
        
    Returns:
        Dictionary mapping model names to their analysis results
    """
    from src.config import PipelineConfig
    from src.pipeline import YouTubeAnalysisPipeline
    from src.reports import MultiModelReportGenerator
    from src.analysis import analysis_to_dataframe, GeminiClient
    
    MODEL_MAP = {
        "scenic": "SCENIC_CONFIG",
        "koleos": "KOLEOS_CONFIG", 
        "torres": "TORRES_CONFIG",
        "sorento": "SORENTO_CONFIG",
        "santafe": "SANTAFE_CONFIG",
    }
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    
    config = PipelineConfig(google_api_key=api_key)
    pipeline = YouTubeAnalysisPipeline(config)
    
    results = {}
    
    for name in model_names:
        if name not in MODEL_MAP:
            print(f"Warning: Unknown model '{name}', skipping")
            continue
        
        # Import the config
        from src import config as config_module
        car_model = getattr(config_module, MODEL_MAP[name])
        
        print(f"\n{'='*60}")
        print(f"Analyzing: {car_model.company} {car_model.model}")
        print(f"{'='*60}")
        
        pipeline.run_full_pipeline(
            car_model=car_model,
            skip_transcription=skip_transcription,
        )
        
        results[name] = pipeline.results.get(car_model.identifier, {})
    
    # Generate comparison report
    if len(results) > 1:
        gemini_client = GeminiClient(api_key)
        multi_report = MultiModelReportGenerator(gemini_client, config.output_dir)
        
        model_analyses = {}
        for name, data in results.items():
            if 'video_analyses' in data:
                model_analyses[name] = analysis_to_dataframe(data['video_analyses'])
        
        if model_analyses:
            comparison_df = multi_report.generate_sentiment_comparison(model_analyses)
            multi_report.generate_comparison_excel(model_analyses, "comparison.xlsx")
            multi_report.visualize_sentiment(comparison_df)
            print("\n✓ Comparison report generated")
    
    return results


if __name__ == "__main__":
    # Example usage
    print("YouTube Video Intelligence Pipeline - Quick Start")
    print("=" * 50)
    print("\nAvailable functions:")
    print("  analyze_scenic()     - Analyze Renault Scenic E-Tech")
    print("  analyze_koleos()     - Analyze Renault Grand Koleos")
    print("  analyze_torres()     - Analyze KGM Torres Hybrid")
    print("  analyze_car(...)     - Analyze custom car model")
    print("  compare_models(...)  - Compare multiple models")
    print("\nExample:")
    print('  outputs = analyze_car("Toyota", "RAV4")')
    print('  compare_models(["scenic", "koleos", "torres"])')
