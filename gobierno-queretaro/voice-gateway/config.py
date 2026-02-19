"""
Gobierno Queretaro - Voice Gateway Configuration
Environment-based configuration for voice services
"""

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class VoiceSettings(BaseSettings):
    """Voice gateway configuration settings"""

    # Service identity
    service_name: str = "voice-gateway"
    service_version: str = "1.0.0"

    # ElevenLabs TTS
    elevenlabs_api_key: str = Field(
        default="",
        description="ElevenLabs API key for text-to-speech",
    )
    elevenlabs_voice_id: str = Field(
        default="cgSgspJ2msm6clMCkdW9",  # Default voice
        description="Default ElevenLabs voice ID",
    )
    elevenlabs_model_id: str = Field(
        default="eleven_turbo_v2",
        description="ElevenLabs model for TTS",
    )

    # Deepgram STT
    deepgram_api_key: str = Field(
        default="",
        description="Deepgram API key for speech-to-text",
    )
    deepgram_model: str = Field(
        default="nova-2",
        description="Deepgram model for STT",
    )
    deepgram_language: str = Field(
        default="es-419",  # Latin American Spanish
        description="Deepgram language code",
    )

    # Orchestrator connection
    orchestrator_url: str = Field(
        default="http://orchestrator:8000",
        description="URL of the orchestrator service",
    )

    # WebSocket settings
    ws_ping_interval: int = Field(
        default=30,
        description="WebSocket ping interval in seconds",
    )
    ws_ping_timeout: int = Field(
        default=10,
        description="WebSocket ping timeout in seconds",
    )

    # Audio settings
    audio_sample_rate: int = Field(
        default=16000,
        description="Audio sample rate in Hz",
    )
    audio_channels: int = Field(
        default=1,
        description="Number of audio channels (mono)",
    )
    audio_chunk_size: int = Field(
        default=4096,
        description="Audio chunk size in bytes",
    )

    # Conversation settings
    max_silence_seconds: float = Field(
        default=2.0,
        description="Max silence before ending turn",
    )
    voice_activity_threshold: float = Field(
        default=0.3,
        description="Voice activity detection threshold",
    )

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Redis (for session state)
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    class Config:
        env_file = ".env"
        case_sensitive = False
        env_prefix = ""


@lru_cache()
def get_settings() -> VoiceSettings:
    """Get cached settings instance"""
    return VoiceSettings()
