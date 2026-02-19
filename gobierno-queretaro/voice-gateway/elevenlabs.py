"""
Gobierno Queretaro - ElevenLabs TTS Integration
Text-to-speech using ElevenLabs API
"""

import asyncio
import logging
from typing import AsyncGenerator

import httpx

from config import get_settings

logger = logging.getLogger(__name__)


class ElevenLabsTTS:
    """
    ElevenLabs Text-to-Speech client.

    Features:
    - Streaming audio generation
    - Voice selection
    - Audio quality settings
    """

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(
        self,
        api_key: str | None = None,
        voice_id: str | None = None,
        model_id: str | None = None,
    ):
        """
        Initialize ElevenLabs TTS client.

        Args:
            api_key: ElevenLabs API key (uses settings if not provided)
            voice_id: Voice ID to use (uses settings if not provided)
            model_id: Model ID to use (uses settings if not provided)
        """
        settings = get_settings()
        self.api_key = api_key or settings.elevenlabs_api_key
        self.voice_id = voice_id or settings.elevenlabs_voice_id
        self.model_id = model_id or settings.elevenlabs_model_id

        if not self.api_key:
            logger.warning("ElevenLabs API key not configured")

    @property
    def headers(self) -> dict:
        """Get API headers."""
        return {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }

    async def synthesize(
        self,
        text: str,
        voice_id: str | None = None,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True,
    ) -> bytes:
        """
        Synthesize speech from text.

        Args:
            text: Text to synthesize
            voice_id: Override voice ID
            stability: Voice stability (0-1)
            similarity_boost: Similarity to original voice (0-1)
            style: Style exaggeration (0-1)
            use_speaker_boost: Boost similarity to speaker

        Returns:
            Audio bytes (MP3 format)
        """
        voice = voice_id or self.voice_id
        url = f"{self.BASE_URL}/text-to-speech/{voice}"

        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": style,
                "use_speaker_boost": use_speaker_boost,
            },
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.content

    async def synthesize_stream(
        self,
        text: str,
        voice_id: str | None = None,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        chunk_size: int = 4096,
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream synthesized speech.

        Yields audio chunks as they are generated for lower latency.

        Args:
            text: Text to synthesize
            voice_id: Override voice ID
            stability: Voice stability (0-1)
            similarity_boost: Similarity to original voice (0-1)
            chunk_size: Size of audio chunks to yield

        Yields:
            Audio bytes chunks (MP3 format)
        """
        voice = voice_id or self.voice_id
        url = f"{self.BASE_URL}/text-to-speech/{voice}/stream"

        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
            },
        }

        headers = self.headers.copy()
        headers["Accept"] = "audio/mpeg"

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                url,
                headers=headers,
                json=payload,
                timeout=60.0,
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size):
                    yield chunk

    async def list_voices(self) -> list[dict]:
        """
        List available voices.

        Returns:
            List of voice dictionaries with id, name, and metadata
        """
        url = f"{self.BASE_URL}/voices"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"xi-api-key": self.api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("voices", [])

    async def get_voice(self, voice_id: str) -> dict:
        """
        Get voice details.

        Args:
            voice_id: Voice ID to look up

        Returns:
            Voice metadata dictionary
        """
        url = f"{self.BASE_URL}/voices/{voice_id}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"xi-api-key": self.api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    async def check_subscription(self) -> dict:
        """
        Check subscription status and remaining characters.

        Returns:
            Subscription info including character limits
        """
        url = f"{self.BASE_URL}/user/subscription"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"xi-api-key": self.api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()


# Singleton instance
_tts_client: ElevenLabsTTS | None = None


def get_tts_client() -> ElevenLabsTTS:
    """Get or create the singleton TTS client."""
    global _tts_client
    if _tts_client is None:
        _tts_client = ElevenLabsTTS()
    return _tts_client
