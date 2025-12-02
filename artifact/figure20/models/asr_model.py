"""
ASR Model Wrapper
Provides unified interface for ASR (Automatic Speech Recognition) models
"""

from typing import List, Optional, Dict, Any


class ASRModel:
    """
    Wrapper for ASR (Automatic Speech Recognition) models.
    Supports: Whisper (OpenAI), other speech-to-text models
    """

    def __init__(self, model_type: str = "whisper", model_size: str = "base",
                 device: str = "cpu", language: Optional[str] = None):
        """
        Initialize ASR model.

        Args:
            model_type: ASR library to use ("whisper", etc.)
            model_size: Model size ("tiny", "base", "small", "medium", "large")
            device: Device to use ("cpu", "cuda", etc.)
            language: Language code (e.g., "en", "zh", None for auto-detect)
        """
        self.model_type = model_type
        self.model_size = model_size
        self.device = device
        self.language = language
        self.model = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the ASR model"""
        if self.model_type == "whisper":
            try:
                import whisper
                self.model = whisper.load_model(
                    self.model_size,
                    device=self.device
                )
            except ImportError:
                raise ImportError("Please install openai-whisper: pip install openai-whisper")
        else:
            raise ValueError(f"Unsupported ASR model: {self.model_type}")

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file (WAV, MP3, M4A, etc.)
            language: Language code (uses model's default if None)

        Returns:
            Transcribed text
        """
        target_language = language or self.language

        if self.model_type == "whisper":
            result = self.model.transcribe(
                audio_path,
                language=target_language,
                verbose=False
            )
            return result["text"]

    def transcribe_with_timestamps(self, audio_path: str,
                                   language: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Transcribe audio with timestamp information.

        Args:
            audio_path: Path to audio file
            language: Language code

        Returns:
            List of dicts with text and timestamp info
        """
        target_language = language or self.language

        if self.model_type == "whisper":
            result = self.model.transcribe(
                audio_path,
                language=target_language,
                verbose=False
            )

            # Extract segments with timing
            segments = []
            for segment in result.get("segments", []):
                segments.append({
                    "text": segment["text"],
                    "start": segment["start"],
                    "end": segment["end"]
                })
            return segments

    def batch_transcribe(self, audio_paths: List[str],
                        language: Optional[str] = None) -> List[str]:
        """
        Transcribe multiple audio files.

        Args:
            audio_paths: List of audio file paths
            language: Language code

        Returns:
            List of transcribed text strings
        """
        results = []
        for audio_path in audio_paths:
            text = self.transcribe(audio_path, language)
            results.append(text)
        return results

    def get_model_info(self) -> Dict[str, str]:
        """Get information about the ASR model"""
        return {
            "type": self.model_type,
            "model_size": self.model_size,
            "device": self.device,
            "language": self.language or "auto-detect"
        }

    def set_language(self, language: str):
        """Set default language for transcription"""
        self.language = language
