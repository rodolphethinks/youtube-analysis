"""
Audio transcription module for YouTube videos.
Handles audio download and transcription using Whisper.
"""

import os
from typing import Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass

import yt_dlp
from tqdm import tqdm

if TYPE_CHECKING:
    from .config import PipelineConfig


@dataclass
class TranscriptionResult:
    """Result of a video transcription."""
    video_url: str
    video_id: str
    transcript: str
    success: bool
    error_message: Optional[str] = None


class AudioDownloader:
    """Download audio from YouTube videos."""
    
    def __init__(self, output_dir: str = "downloads"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def download(self, url: str, output_format: str = "wav") -> Optional[str]:
        """
        Download audio from a YouTube video.
        
        Args:
            url: YouTube video URL
            output_format: Audio format (wav, mp3, etc.)
            
        Returns:
            Path to downloaded audio file, or None on failure.
        """
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{self.output_dir}/%(id)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': output_format,
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.cache.remove()
                info_dict = ydl.extract_info(url, download=True)
                audio_file = f"{self.output_dir}/{info_dict['id']}.{output_format}"
                return audio_file
        except Exception as e:
            print(f"Error downloading audio from {url}: {e}")
            return None
    
    def cleanup(self, file_path: str) -> None:
        """Remove downloaded audio file."""
        if os.path.exists(file_path):
            os.remove(file_path)


class WhisperTranscriber:
    """Transcribe audio using OpenAI Whisper model."""
    
    def __init__(self, model_size: str = "large-v3", device: str = "auto"):
        """
        Initialize Whisper transcriber.
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v3)
            device: Device to use (auto, cuda, cpu)
        """
        self.model_size = model_size
        self.device = device
        self._pipeline = None
    
    @property
    def pipeline(self):
        """Lazy loading of Whisper pipeline."""
        if self._pipeline is None:
            self._pipeline = self._load_pipeline()
        return self._pipeline
    
    def _load_pipeline(self):
        """Load the Whisper model and create pipeline."""
        import torch
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
        
        if self.device == "auto":
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
        else:
            device = self.device
        
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        
        model_id = f"openai/whisper-{self.model_size}"
        
        print(f"Loading Whisper model: {model_id} on {device}")
        
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True
        )
        model.to(device)
        
        processor = AutoProcessor.from_pretrained(model_id)
        
        pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            torch_dtype=torch_dtype,
            device=device,
            return_timestamps=True
        )
        
        return pipe
    
    def transcribe(self, audio_path: str, language: str = "korean") -> Optional[str]:
        """
        Transcribe audio file.
        
        Args:
            audio_path: Path to audio file
            language: Language for transcription
            
        Returns:
            Transcription text or None on failure.
        """
        try:
            result = self.pipeline(
                audio_path,
                generate_kwargs={"language": language}
            )
            return result.get("text", "")
        except Exception as e:
            print(f"Error transcribing {audio_path}: {e}")
            return None


class TranscriptionService:
    """Service for transcribing multiple videos."""
    
    def __init__(
        self, 
        config: "PipelineConfig",
        whisper_model: str = "large-v3",
        cleanup_audio: bool = True
    ):
        self.config = config
        self.downloader = AudioDownloader(config.downloads_dir)
        self.transcriber = WhisperTranscriber(model_size=whisper_model)
        self.cleanup_audio = cleanup_audio
    
    def transcribe_videos(
        self, 
        video_urls: List[str],
        max_retries: int = 2
    ) -> Dict[str, str]:
        """
        Transcribe multiple videos.
        
        Args:
            video_urls: List of YouTube video URLs
            max_retries: Number of retry attempts on failure
            
        Returns:
            Dictionary mapping video URLs to transcriptions.
        """
        transcriptions = {}
        
        with tqdm(total=len(video_urls), desc="Transcribing videos", unit="video") as pbar:
            for url in video_urls:
                result = self._transcribe_single(url, max_retries)
                if result.success:
                    transcriptions[url] = result.transcript
                else:
                    print(f"Failed to transcribe {url}: {result.error_message}")
                pbar.update(1)
        
        print(f"Successfully transcribed {len(transcriptions)}/{len(video_urls)} videos")
        return transcriptions
    
    def _transcribe_single(
        self, 
        url: str, 
        max_retries: int
    ) -> TranscriptionResult:
        """Transcribe a single video with retry logic."""
        video_id = url.split("v=")[-1]
        
        # Try fetching existing captions first if enabled
        if self.config.use_existing_subtitles:
            print(f"Attempting to fetch existing captions for {video_id}...")
            captions = self.fetch_captions(video_id)
            if captions:
                print(f"Found existing captions for {video_id}")
                return TranscriptionResult(
                    video_url=url,
                    video_id=video_id,
                    transcript=captions,
                    success=True
                )
            print(f"No captions found, falling back to Whisper...")

        for attempt in range(max_retries + 1):
            try:
                # Download audio
                audio_path = self.downloader.download(url)
                if not audio_path:
                    return TranscriptionResult(
                        video_url=url,
                        video_id=video_id,
                        transcript="",
                        success=False,
                        error_message="Failed to download audio"
                    )
                
                # Transcribe
                transcript = self.transcriber.transcribe(audio_path)
                
                # Cleanup
                if self.cleanup_audio:
                    self.downloader.cleanup(audio_path)
                
                if transcript:
                    return TranscriptionResult(
                        video_url=url,
                        video_id=video_id,
                        transcript=transcript,
                        success=True
                    )
                else:
                    if attempt < max_retries:
                        print(f"Retry {attempt + 1}/{max_retries} for {url}")
                        continue
                    
            except Exception as e:
                if attempt < max_retries:
                    print(f"Retry {attempt + 1}/{max_retries} for {url}: {e}")
                    continue
                return TranscriptionResult(
                    video_url=url,
                    video_id=video_id,
                    transcript="",
                    success=False,
                    error_message=str(e)
                )
        
        return TranscriptionResult(
            video_url=url,
            video_id=video_id,
            transcript="",
            success=False,
            error_message="Max retries exceeded"
        )

    def fetch_captions(self, video_id: str, languages=['ko', 'en']) -> Optional[str]:
        """Fetch existing captions from YouTube.
        
        Uses YouTube's auto-generated or manual captions when available,
        which is faster and cheaper than Whisper transcription.
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            
            # New API requires instantiation
            api = YouTubeTranscriptApi()
            transcript_data = api.fetch(video_id, languages=languages)
            
            # Combine text parts (now FetchedTranscriptSnippet objects)
            full_text = " ".join([segment.text for segment in transcript_data])
            return full_text
        except Exception as e:
            # print(f"Could not fetch captions for {video_id}: {e}")
            return None
