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
    
    def __init__(self, model_size: str = "large-v3-turbo", device: str = "auto"):
        """
        Initialize Whisper transcriber.
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v3, large-v3-turbo)
            device: Device to use (auto, cuda, cpu)
        """
        self.model_size = model_size
        self.device = device
        self._model = None
        self._processor = None
        self._torch_dtype = None
    
    def _load_model(self):
        """Load the Whisper model and processor directly."""
        import torch
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
        
        if self.device == "auto":
            self._device = "cuda:0" if torch.cuda.is_available() else "cpu"
        else:
            self._device = self.device
        
        self._torch_dtype = torch.float16 if "cuda" in self._device else torch.float32
        
        model_id = f"openai/whisper-{self.model_size}"
        
        print(f"Loading Whisper model: {model_id} on {self._device}")
        print(f"Using torch dtype: {self._torch_dtype}")
        
        # Load model with SDPA for faster attention
        self._model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            torch_dtype=self._torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
            attn_implementation="sdpa"
        )
        self._model.to(self._device)
        
        self._processor = AutoProcessor.from_pretrained(model_id)
        
        print(f"Model loaded successfully on {self._device}")
    
    @property
    def model(self):
        """Lazy loading of model."""
        if self._model is None:
            self._load_model()
        return self._model
    
    @property
    def processor(self):
        """Lazy loading of processor."""
        if self._processor is None:
            self._load_model()
        return self._processor
    
    def transcribe(self, audio_path: str, language: str = "korean") -> Optional[str]:
        """
        Transcribe audio file using Whisper's native long-form transcription.
        
        Args:
            audio_path: Path to audio file
            language: Language for transcription (e.g., 'korean', 'english')
            
        Returns:
            Transcription text or None on failure.
        """
        import torch
        import librosa
        
        try:
            # Load audio with librosa (resamples to 16kHz as required by Whisper)
            audio, sr = librosa.load(audio_path, sr=16000)
            
            # Process audio to get input features
            inputs = self.processor(
                audio,
                sampling_rate=16000,
                return_tensors="pt",
                return_attention_mask=True
            )
            
            # Move to device with correct dtype
            input_features = inputs.input_features.to(self._device, dtype=self._torch_dtype)
            attention_mask = inputs.attention_mask.to(self._device) if inputs.attention_mask is not None else None
            
            # Map language name to Whisper language code
            language_map = {
                "korean": "ko",
                "english": "en",
                "japanese": "ja",
                "chinese": "zh",
                "french": "fr",
                "german": "de",
                "spanish": "es",
            }
            lang_code = language_map.get(language.lower(), language.lower()[:2])
            
            # Generate transcription using Whisper's native long-form mechanism
            # This handles chunking internally (see Whisper paper section 3.8)
            with torch.no_grad():
                generated_ids = self.model.generate(
                    input_features=input_features,
                    attention_mask=attention_mask,
                    language=lang_code,
                    task="transcribe",
                    return_timestamps=False,  # Faster without timestamps
                )
            
            # Decode the generated tokens
            transcription = self.processor.batch_decode(
                generated_ids, 
                skip_special_tokens=True
            )[0]
            
            return transcription.strip()
            
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
        max_retries: int = 2,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, str]:
        """
        Transcribe multiple videos.
        
        Args:
            video_urls: List of YouTube video URLs
            max_retries: Number of retry attempts on failure
            progress_callback: Optional callback(transcribed_count, total, message)
            
        Returns:
            Dictionary mapping video URLs to transcriptions.
        """
        transcriptions = {}
        total = len(video_urls)
        
        with tqdm(total=total, desc="Transcribing videos", unit="video") as pbar:
            for i, url in enumerate(video_urls):
                video_id = url.split("v=")[-1]
                
                if progress_callback:
                    progress_callback(i, total, f"Transcribing video {video_id}")
                
                print(f"\n[{i+1}/{total}] Processing {video_id}...")
                result = self._transcribe_single(url, max_retries)
                if result.success:
                    transcriptions[url] = result.transcript
                    print(f"✓ Successfully transcribed {video_id}")
                else:
                    print(f"✗ Failed to transcribe {url}: {result.error_message}")
                pbar.update(1)
        
        if progress_callback:
            progress_callback(total, total, "Transcription complete")
        
        print(f"Successfully transcribed {len(transcriptions)}/{total} videos")
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
