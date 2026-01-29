"""
Configuration module for YouTube Video Intelligence Pipeline.
Centralized settings for API keys, car models, and analysis parameters.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class CarModel:
    """Configuration for a car model to analyze."""
    company: str
    model: str
    search_queries: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.search_queries:
            # Default search queries for electric vehicles
            self.search_queries = [
                f"{self.model} {self.company}",
                f"{self.model} 전기차 시승기",
                f"{self.company} {self.model} 전기차 리뷰",
                f"{self.model} 충전 속도 장단점",
                f"{self.model} 가격 옵션 사양",
            ]
    
    @property
    def identifier(self) -> str:
        """Unique identifier for file naming."""
        return f"{self.company}_{self.model}".replace(" ", "_").lower()


@dataclass
class PipelineConfig:
    """Main configuration for the analysis pipeline."""
    
    # API Configuration
    google_api_key: str = field(default_factory=lambda: os.getenv('GOOGLE_API_KEY', ''))
    
    # Search Parameters
    max_search_results: int = 50
    published_after: str = "2024-04-01T00:00:00Z"
    max_comments_per_video: int = 100
    
    # Output Directories
    output_dir: str = "output"
    audio_dir: str = "audio"
    downloads_dir: str = "downloads"
    
    # Analysis Settings
    gemini_model: str = "gemini-2.0-flash"
    
    # Car Models to Analyze
    car_models: List[CarModel] = field(default_factory=list)
    
    def __post_init__(self):
        # Create output directories
        for dir_path in [self.output_dir, self.audio_dir, self.downloads_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # Validate API key
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")
    
    def add_car_model(self, company: str, model: str, search_queries: Optional[List[str]] = None):
        """Add a car model to analyze."""
        car = CarModel(company=company, model=model, search_queries=search_queries or [])
        self.car_models.append(car)
        return car


# Predefined car model configurations
SCENIC_CONFIG = CarModel(
    company="르노",
    model="Scenic E-Tech",
    search_queries=[
        "르노 세닉 E-Tech",
        "세닉 전기차 시승기",
        "르노 세닉 전기차 리뷰",
        "세닉 충전 속도 장단점",
        "세닉 가격 옵션 사양",
    ]
)

KOLEOS_CONFIG = CarModel(
    company="르노 코리아",
    model="그랑 콜레오스",
    search_queries=[
        "그랑 콜레오스 르노 코리아",
        "그랑 콜레오스 시승기",
        "르노 코리아 그랑 콜레오스 신차 리뷰",
        "그랑 콜레오스 하이브리드 장단점",
        "그랑 콜레오스 가격 옵션",
    ]
)

TORRES_CONFIG = CarModel(
    company="KGM",
    model="토레스 하이브리드",
    search_queries=[
        "토레스 하이브리드 KGM",
        "토레스 하이브리드 시승기",
        "KGM 토레스 하이브리드 리뷰",
        "토레스 하이브리드 장단점",
        "토레스 가격 옵션",
    ]
)

SORENTO_CONFIG = CarModel(
    company="기아",
    model="쏘렌토",
)

SANTAFE_CONFIG = CarModel(
    company="현대",
    model="싼타페",
)


def get_default_config() -> PipelineConfig:
    """Get default pipeline configuration."""
    config = PipelineConfig()
    config.car_models = [SCENIC_CONFIG]  # Default to Scenic
    return config
