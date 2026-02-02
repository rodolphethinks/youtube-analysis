"""
Tests for the configuration module.
"""

import os
import pytest
from unittest.mock import patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import CarModel, PipelineConfig, SCENIC_CONFIG, KOLEOS_CONFIG


class TestCarModel:
    """Tests for CarModel dataclass."""
    
    def test_car_model_creation(self):
        """Test basic CarModel creation."""
        car = CarModel(company="Toyota", model="RAV4")
        assert car.company == "Toyota"
        assert car.model == "RAV4"
    
    def test_car_model_with_custom_queries(self):
        """Test CarModel with custom search queries."""
        queries = ["Toyota RAV4 review", "RAV4 2024 test"]
        car = CarModel(company="Toyota", model="RAV4", search_queries=queries)
        assert car.search_queries == queries
    
    def test_car_model_auto_generates_queries(self):
        """Test that CarModel auto-generates queries when none provided."""
        car = CarModel(company="Hyundai", model="Tucson")
        assert len(car.search_queries) > 0
        # Should contain model name in queries
        assert any("Tucson" in q for q in car.search_queries)
    
    def test_car_model_identifier(self):
        """Test identifier property for file naming."""
        car = CarModel(company="르노", model="Scenic E-Tech")
        identifier = car.identifier
        assert " " not in identifier  # No spaces
        assert identifier.islower() or "_" in identifier  # Lowercase with underscores
    
    def test_predefined_scenic_config(self):
        """Test predefined Scenic configuration."""
        assert SCENIC_CONFIG.company == "르노"
        assert "Scenic" in SCENIC_CONFIG.model
        assert len(SCENIC_CONFIG.search_queries) > 0
    
    def test_predefined_koleos_config(self):
        """Test predefined Koleos configuration."""
        assert "르노" in KOLEOS_CONFIG.company
        assert len(KOLEOS_CONFIG.search_queries) > 0


class TestPipelineConfig:
    """Tests for PipelineConfig dataclass."""
    
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test_api_key_12345"})
    def test_config_with_env_api_key(self, tmp_path):
        """Test config loads API key from environment."""
        config = PipelineConfig(
            output_dir=str(tmp_path / "output"),
            audio_dir=str(tmp_path / "audio"),
            downloads_dir=str(tmp_path / "downloads")
        )
        assert config.google_api_key == "test_api_key_12345"
    
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key"})
    def test_config_creates_directories(self, tmp_path):
        """Test that config creates output directories."""
        output_dir = tmp_path / "output"
        audio_dir = tmp_path / "audio"
        downloads_dir = tmp_path / "downloads"
        
        config = PipelineConfig(
            output_dir=str(output_dir),
            audio_dir=str(audio_dir),
            downloads_dir=str(downloads_dir)
        )
        
        assert output_dir.exists()
        assert audio_dir.exists()
        assert downloads_dir.exists()
    
    @patch.dict(os.environ, {}, clear=True)
    def test_config_raises_without_api_key(self, tmp_path):
        """Test that config raises error when API key is missing."""
        # Remove GOOGLE_API_KEY from environment
        os.environ.pop("GOOGLE_API_KEY", None)
        
        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            PipelineConfig(
                google_api_key="",
                output_dir=str(tmp_path / "output"),
                audio_dir=str(tmp_path / "audio"),
                downloads_dir=str(tmp_path / "downloads")
            )
    
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key"})
    def test_config_default_values(self, tmp_path):
        """Test default configuration values."""
        config = PipelineConfig(
            output_dir=str(tmp_path / "output"),
            audio_dir=str(tmp_path / "audio"),
            downloads_dir=str(tmp_path / "downloads")
        )
        
        assert config.max_search_results == 50
        assert config.max_comments_per_video == 100
        assert config.gemini_model == "gemini-2.0-flash"
    
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key"})
    def test_add_car_model(self, tmp_path):
        """Test adding car models to config."""
        config = PipelineConfig(
            output_dir=str(tmp_path / "output"),
            audio_dir=str(tmp_path / "audio"),
            downloads_dir=str(tmp_path / "downloads")
        )
        
        car = config.add_car_model("BMW", "X5")
        
        assert len(config.car_models) == 1
        assert car.company == "BMW"
        assert car.model == "X5"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
