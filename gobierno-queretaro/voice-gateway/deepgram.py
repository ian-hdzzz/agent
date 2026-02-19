"""
Gobierno Queretaro - Deepgram STT Integration
Speech-to-text using Deepgram API
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Callable

import httpx
import websockets

from config import get_settings

logger = logging.getLogger(__name__)


class DeepgramSTT:
    """
    Deepgram Speech-to-Text client.

    Features:
    - Real-time streaming transcription
    - Batch transcription
    - Language detection
    - Punctuation and formatting
    """

    BASE_URL = "https://api.deepgram.com/v1"
    WS_URL = "wss://api.deepgram.com/v1/listen"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        language: str | None = None,
    ):
        """
        Initialize Deepgram STT client.

        Args:
            api_key: Deepgram API key (uses settings if not provided)
            model: Model to use (uses settings if not provided)
            language: Language code (uses settings if not provided)
        """
        settings = get_settings()
        self.api_key = api_key or settings.deepgram_api_key
        self.model = model or settings.deepgram_model
        self.language = language or settings.deepgram_language

        if not self.api_key:
            logger.warning("Deepgram API key not configured")

    @property
    def headers(self) -> dict:
        """Get API headers."""
        return {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/wav",
        }

    async def transcribe(
        self,
        audio: bytes,
        language: str | None = None,
        punctuate: bool = True,
        smart_format: bool = True,
    ) -> dict:
        """
        Transcribe audio file.

        Args:
            audio: Audio bytes (WAV, MP3, etc.)
            language: Override language code
            punctuate: Add punctuation
            smart_format: Apply smart formatting

        Returns:
            Transcription result dictionary
        """
        lang = language or self.language
        params = {
            "model": self.model,
            "language": lang,
            "punctuate": str(punctuate).lower(),
            "smart_format": str(smart_format).lower(),
        }

        url = f"{self.BASE_URL}/listen"
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query_string}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                full_url,
                headers=self.headers,
                content=audio,
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json()

    def get_transcript_text(self, result: dict) -> str:
        """
        Extract transcript text from Deepgram response.

        Args:
            result: Deepgram API response

        Returns:
            Transcribed text string
        """
        try:
            channels = result.get("results", {}).get("channels", [])
            if channels:
                alternatives = channels[0].get("alternatives", [])
                if alternatives:
                    return alternatives[0].get("transcript", "")
        except (KeyError, IndexError):
            pass
        return ""

    async def transcribe_stream(
        self,
        audio_generator: AsyncGenerator[bytes, None],
        on_transcript: Callable[[str, bool], None] | None = None,
        language: str | None = None,
        interim_results: bool = True,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream audio for real-time transcription.

        Args:
            audio_generator: Async generator yielding audio chunks
            on_transcript: Callback for transcript updates (text, is_final)
            language: Override language code
            interim_results: Include interim (non-final) results

        Yields:
            Transcription result dictionaries
        """
        lang = language or self.language
        params = {
            "model": self.model,
            "language": lang,
            "punctuate": "true",
            "smart_format": "true",
            "interim_results": str(interim_results).lower(),
            "encoding": "linear16",
            "sample_rate": str(get_settings().audio_sample_rate),
            "channels": "1",
        }

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        ws_url = f"{self.WS_URL}?{query_string}"

        headers = {"Authorization": f"Token {self.api_key}"}

        try:
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                # Start tasks for sending and receiving
                async def send_audio():
                    async for chunk in audio_generator:
                        await ws.send(chunk)
                    # Send close message
                    await ws.send(json.dumps({"type": "CloseStream"}))

                async def receive_transcripts():
                    async for message in ws:
                        try:
                            data = json.loads(message)

                            # Extract transcript
                            channel = data.get("channel", {})
                            alternatives = channel.get("alternatives", [])
                            if alternatives:
                                transcript = alternatives[0].get("transcript", "")
                                is_final = data.get("is_final", False)

                                if transcript and on_transcript:
                                    on_transcript(transcript, is_final)

                                yield data

                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse WebSocket message")

                # Run send and receive concurrently
                send_task = asyncio.create_task(send_audio())

                async for result in receive_transcripts():
                    yield result

                await send_task

        except websockets.exceptions.WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            raise


class StreamingTranscriber:
    """
    Streaming transcription session manager.

    Manages the lifecycle of a real-time transcription session.
    """

    def __init__(self, stt: DeepgramSTT | None = None):
        """
        Initialize streaming transcriber.

        Args:
            stt: DeepgramSTT client (creates new if not provided)
        """
        self.stt = stt or DeepgramSTT()
        self._audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._running = False
        self._final_transcript = ""
        self._interim_transcript = ""

    async def start(
        self,
        on_transcript: Callable[[str, bool], None] | None = None,
    ) -> None:
        """
        Start transcription session.

        Args:
            on_transcript: Callback for transcript updates
        """
        self._running = True
        self._final_transcript = ""
        self._interim_transcript = ""

        async def audio_generator():
            while self._running:
                try:
                    chunk = await asyncio.wait_for(
                        self._audio_queue.get(),
                        timeout=1.0,
                    )
                    if chunk is None:  # Stop signal
                        break
                    yield chunk
                except asyncio.TimeoutError:
                    continue

        def handle_transcript(text: str, is_final: bool):
            if is_final:
                self._final_transcript += " " + text
                self._interim_transcript = ""
            else:
                self._interim_transcript = text

            if on_transcript:
                on_transcript(text, is_final)

        async for _ in self.stt.transcribe_stream(
            audio_generator(),
            on_transcript=handle_transcript,
        ):
            pass

    async def feed_audio(self, audio_chunk: bytes) -> None:
        """
        Feed audio chunk to transcriber.

        Args:
            audio_chunk: Raw audio bytes
        """
        if self._running:
            await self._audio_queue.put(audio_chunk)

    async def stop(self) -> str:
        """
        Stop transcription and return final transcript.

        Returns:
            Complete final transcript
        """
        self._running = False
        await self._audio_queue.put(None)  # Stop signal
        return self._final_transcript.strip()

    @property
    def current_transcript(self) -> str:
        """Get current transcript (final + interim)."""
        return (self._final_transcript + " " + self._interim_transcript).strip()

    @property
    def final_transcript(self) -> str:
        """Get final confirmed transcript."""
        return self._final_transcript.strip()


# Singleton instance
_stt_client: DeepgramSTT | None = None


def get_stt_client() -> DeepgramSTT:
    """Get or create the singleton STT client."""
    global _stt_client
    if _stt_client is None:
        _stt_client = DeepgramSTT()
    return _stt_client
