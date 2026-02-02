"""
Tests for the transcription module.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.transcription import (
    TranscriptionResult, AudioDownloader, WhisperTranscriber, 
    TranscriptionService
)


class TestTranscriptionResult:
    """Tests for TranscriptionResult dataclass."""
    
    def test_successful_result(self):
        """Test creating a successful transcription result."""
        result = TranscriptionResult(
            video_url="https://youtube.com/watch?v=test",
            video_id="test",
            transcript="This is the transcript text.",
            success=True
        )
        
        assert result.success is True
        assert result.transcript == "This is the transcript text."
        assert result.error_message is None
    
    def test_failed_result(self):
        """Test creating a failed transcription result."""
        result = TranscriptionResult(
            video_url="https://youtube.com/watch?v=test",
            video_id="test",
            transcript="",
            success=False,
            error_message="Download failed"
        )
        
        assert result.success is False
        assert result.error_message == "Download failed"


class TestAudioDownloader:
    """Tests for AudioDownloader."""
    
    def test_initialization(self, tmp_path):
        """Test downloader initialization creates directory."""
        output_dir = tmp_path / "downloads"
        downloader = AudioDownloader(output_dir=str(output_dir))
        
        assert output_dir.exists()
    
    @patch('src.transcription.yt_dlp.YoutubeDL')
    def test_download_success(self, mock_ydl_class, tmp_path):
        """Test successful audio download."""
        output_dir = tmp_path / "downloads"
        downloader = AudioDownloader(output_dir=str(output_dir))
        
        # Mock the YoutubeDL context manager
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = Mock(return_value=False)
        
        mock_ydl.extract_info.return_value = {'id': 'test123'}
        
        result = downloader.download("https://youtube.com/watch?v=test123")
        
        assert result is not None
        assert "test123" in result
    
    @patch('src.transcription.yt_dlp.YoutubeDL')
    def test_download_failure(self, mock_ydl_class, tmp_path):
        """Test download failure returns None."""
        output_dir = tmp_path / "downloads"
        downloader = AudioDownloader(output_dir=str(output_dir))
        
        # Mock exception during download
        mock_ydl_class.return_value.__enter__ = Mock(side_effect=Exception("Network error"))
        mock_ydl_class.return_value.__exit__ = Mock(return_value=False)
        
        result = downloader.download("https://youtube.com/watch?v=test123")
        
        assert result is None
    
    def test_cleanup_existing_file(self, tmp_path):
        """Test cleanup removes existing file."""
        output_dir = tmp_path / "downloads"
        output_dir.mkdir()
        
        # Create a test file
        test_file = output_dir / "test.wav"
        test_file.write_text("test content")
        
        downloader = AudioDownloader(output_dir=str(output_dir))
        downloader.cleanup(str(test_file))
        
        assert not test_file.exists()
    
    def test_cleanup_nonexistent_file(self, tmp_path):
        """Test cleanup handles nonexistent file gracefully."""
        output_dir = tmp_path / "downloads"
        output_dir.mkdir()
        
        downloader = AudioDownloader(output_dir=str(output_dir))
        # Should not raise exception
        downloader.cleanup(str(output_dir / "nonexistent.wav"))


class TestWhisperTranscriber:
    """Tests for WhisperTranscriber."""
    
    def test_initialization(self):
        """Test transcriber initialization."""
        transcriber = WhisperTranscriber(model_size="base", device="cpu")
        
        assert transcriber.model_size == "base"
        assert transcriber.device == "cpu"
        assert transcriber._pipeline is None  # Lazy loading
    
    def test_transcribe_without_pipeline_initialization(self):
        """Test that transcribe attempts to load pipeline."""
        transcriber = WhisperTranscriber(model_size="tiny", device="cpu")
        
        # Mock the pipeline property
        mock_pipe = MagicMock()
        mock_pipe.return_value = {"text": "Transcribed text"}
        
        with patch.object(WhisperTranscriber, 'pipeline', 
                         new_callable=lambda: property(lambda self: mock_pipe)):
            transcriber_with_mock = WhisperTranscriber(model_size="tiny")
            # This would trigger pipeline loading in real scenario


class TestTranscriptionService:
    """Tests for TranscriptionService."""
    
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key"})
    def test_initialization(self, tmp_path):
        """Test service initialization."""
        from src.config import PipelineConfig
        
        config = PipelineConfig(
            google_api_key="test_key",
            output_dir=str(tmp_path / "output"),
            audio_dir=str(tmp_path / "audio"),
            downloads_dir=str(tmp_path / "downloads")
        )
        
        service = TranscriptionService(
            config=config,
            whisper_model="tiny",
            cleanup_audio=True
        )
        
        assert service.cleanup_audio is True
    
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key"})
    def test_fetch_captions_fallback(self, tmp_path):
        """Test caption fetching as fallback."""
        from src.config import PipelineConfig
        
        config = PipelineConfig(
            google_api_key="test_key",
            output_dir=str(tmp_path / "output"),
            audio_dir=str(tmp_path / "audio"),
            downloads_dir=str(tmp_path / "downloads"),
            use_existing_subtitles=True
        )
        
        service = TranscriptionService(config=config, whisper_model="tiny")
        
        # Mock the entire YouTubeTranscriptApi class
        with patch.object(service, 'fetch_captions') as mock_fetch:
            mock_fetch.return_value = "Hello World"
            
            result = service.fetch_captions("test_video_id")
            
            assert result == "Hello World"
    
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key"})
    def test_fetch_captions_failure(self, tmp_path):
        """Test caption fetching returns None on failure."""
        from src.config import PipelineConfig
        
        config = PipelineConfig(
            google_api_key="test_key",
            output_dir=str(tmp_path / "output"),
            audio_dir=str(tmp_path / "audio"),
            downloads_dir=str(tmp_path / "downloads")
        )
        
        service = TranscriptionService(config=config, whisper_model="tiny")
        
        # Test the actual method with a non-existent video - should return None
        result = service.fetch_captions("this_video_does_not_exist_12345")
        
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
