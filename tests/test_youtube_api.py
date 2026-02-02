"""
Tests for the YouTube API module.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.youtube_api import (
    VideoInfo, Comment, YouTubeClient, VideoDiscovery, 
    extract_video_id_from_url
)
from src.config import CarModel, PipelineConfig


class TestVideoInfo:
    """Tests for VideoInfo dataclass."""
    
    def test_video_info_creation(self):
        """Test basic VideoInfo creation."""
        info = VideoInfo(
            video_id="abc123",
            url="https://www.youtube.com/watch?v=abc123",
            title="Test Video",
            release_date="2024-01-01 12:00:00",
            channel_id="channel123",
            channel_title="Test Channel",
            views=1000,
            likes=100,
            comments=50,
            duration="PT10M30S"
        )
        
        assert info.video_id == "abc123"
        assert info.views == 1000
    
    def test_duration_conversion(self):
        """Test ISO 8601 duration conversion."""
        info = VideoInfo(
            video_id="test",
            url="http://test.com",
            title="Test",
            release_date="2024-01-01",
            channel_id="ch",
            channel_title="Channel",
            views=0,
            likes=0,
            comments=0,
            duration="PT1H30M45S"
        )
        
        assert info.duration_formatted == "01:30:45"
    
    def test_duration_conversion_minutes_only(self):
        """Test duration with minutes only."""
        info = VideoInfo(
            video_id="test",
            url="http://test.com",
            title="Test",
            release_date="2024-01-01",
            channel_id="ch",
            channel_title="Channel",
            views=0,
            likes=0,
            comments=0,
            duration="PT15M"
        )
        
        assert info.duration_formatted == "00:15:00"
    
    def test_duration_conversion_invalid(self):
        """Test invalid duration returns default."""
        info = VideoInfo(
            video_id="test",
            url="http://test.com",
            title="Test",
            release_date="2024-01-01",
            channel_id="ch",
            channel_title="Channel",
            views=0,
            likes=0,
            comments=0,
            duration="INVALID"
        )
        
        assert info.duration_formatted == "00:00:00"


class TestComment:
    """Tests for Comment dataclass."""
    
    def test_comment_creation(self):
        """Test Comment creation."""
        comment = Comment(
            video_id="vid123",
            author="John Doe",
            text="Great video!",
            likes=25,
            published_at="2024-01-15 10:30"
        )
        
        assert comment.video_id == "vid123"
        assert comment.author == "John Doe"
        assert comment.likes == 25


class TestYouTubeClient:
    """Tests for YouTubeClient."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        client = YouTubeClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client._youtube is None  # Lazy loading
    
    @patch('src.youtube_api.build')
    def test_lazy_youtube_initialization(self, mock_build):
        """Test lazy initialization of YouTube API client."""
        mock_build.return_value = MagicMock()
        
        client = YouTubeClient(api_key="test_key")
        # Access youtube property to trigger lazy load
        _ = client.youtube
        
        mock_build.assert_called_once_with("youtube", "v3", developerKey="test_key")
    
    @patch('src.youtube_api.build')
    def test_search_videos(self, mock_build):
        """Test video search."""
        mock_youtube = MagicMock()
        mock_build.return_value = mock_youtube
        
        # Mock the search response
        mock_youtube.search().list().execute.return_value = {
            'items': [
                {'id': {'videoId': 'vid1'}},
                {'id': {'videoId': 'vid2'}}
            ]
        }
        
        client = YouTubeClient(api_key="test_key")
        results = client.search_videos("test query", max_results=10)
        
        assert len(results) == 2
        assert "https://www.youtube.com/watch?v=vid1" in results
        assert "https://www.youtube.com/watch?v=vid2" in results
    
    @patch('src.youtube_api.build')
    def test_search_videos_empty_result(self, mock_build):
        """Test search with no results."""
        mock_youtube = MagicMock()
        mock_build.return_value = mock_youtube
        
        mock_youtube.search().list().execute.return_value = {'items': []}
        
        client = YouTubeClient(api_key="test_key")
        results = client.search_videos("nonexistent query")
        
        assert len(results) == 0


class TestVideoDiscovery:
    """Tests for VideoDiscovery service."""
    
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key"})
    def test_discover_videos_filters_by_title(self, tmp_path):
        """Test that discovery filters videos by title relevance."""
        mock_client = MagicMock()
        
        # Create config
        config = PipelineConfig(
            google_api_key="test_key",
            output_dir=str(tmp_path / "output"),
            audio_dir=str(tmp_path / "audio"),
            downloads_dir=str(tmp_path / "downloads")
        )
        
        discovery = VideoDiscovery(mock_client, config)
        
        # Mock search results
        mock_client.search_videos.return_value = {
            "https://www.youtube.com/watch?v=vid1": "vid1",
            "https://www.youtube.com/watch?v=vid2": "vid2"
        }
        
        # Mock video details - one relevant, one not
        def mock_get_details(video_id):
            if video_id == "vid1":
                return VideoInfo(
                    video_id="vid1",
                    url="https://www.youtube.com/watch?v=vid1",
                    title="Renault Scenic E-Tech Review",  # Relevant
                    release_date="2024-01-01",
                    channel_id="ch1",
                    channel_title="Auto Channel",
                    views=10000,
                    likes=500,
                    comments=100,
                    duration="PT15M"
                )
            else:
                return VideoInfo(
                    video_id="vid2",
                    url="https://www.youtube.com/watch?v=vid2",
                    title="Unrelated Video About Cooking",  # Not relevant
                    release_date="2024-01-01",
                    channel_id="ch2",
                    channel_title="Food Channel",
                    views=5000,
                    likes=200,
                    comments=50,
                    duration="PT10M"
                )
        
        mock_client.get_video_details.side_effect = mock_get_details
        
        car_model = CarModel(
            company="Renault",
            model="Scenic",
            search_queries=["Renault Scenic review"]
        )
        
        df = discovery.discover_videos(car_model)
        
        # Should only include the relevant video
        assert len(df) == 1
        assert "Scenic" in df.iloc[0]['Title']


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_extract_video_id_standard_url(self):
        """Test extracting video ID from standard URL."""
        url = "https://www.youtube.com/watch?v=abc123XYZ"
        video_id = extract_video_id_from_url(url)
        assert video_id == "abc123XYZ"
    
    def test_extract_video_id_with_params(self):
        """Test extracting video ID from URL with extra parameters."""
        url = "https://www.youtube.com/watch?v=abc123&t=120"
        video_id = extract_video_id_from_url(url)
        assert video_id == "abc123"
    
    def test_extract_video_id_invalid_url(self):
        """Test extracting from invalid URL returns None."""
        url = "https://example.com/video"
        video_id = extract_video_id_from_url(url)
        assert video_id is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
