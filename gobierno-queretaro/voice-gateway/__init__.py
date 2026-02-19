"""
Gobierno Queretaro - Voice Gateway
Voice interface for government service agents
"""

from .config import VoiceSettings, get_settings
from .elevenlabs import ElevenLabsTTS, get_tts_client
from .deepgram import DeepgramSTT, StreamingTranscriber, get_stt_client

__all__ = [
    "VoiceSettings",
    "get_settings",
    "ElevenLabsTTS",
    "get_tts_client",
    "DeepgramSTT",
    "StreamingTranscriber",
    "get_stt_client",
]
