"""
Gobierno Queretaro - Voice Gateway Server
FastAPI + WebSocket server for voice interactions
"""

import asyncio
import json
import logging
import sys
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

from config import get_settings
from elevenlabs import ElevenLabsTTS, get_tts_client
from deepgram import DeepgramSTT, StreamingTranscriber, get_stt_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

settings = get_settings()


# ============================================
# Request/Response Models
# ============================================

class TextToSpeechRequest(BaseModel):
    """Request for text-to-speech conversion."""

    text: str
    voice_id: str | None = None
    stability: float = 0.5
    similarity_boost: float = 0.75


class SpeechToTextRequest(BaseModel):
    """Request for speech-to-text conversion."""

    audio_base64: str
    language: str | None = None


class VoiceQueryRequest(BaseModel):
    """Request for voice-based query to orchestrator."""

    audio_base64: str
    conversation_id: str | None = None
    contact_id: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    tts_configured: bool
    stt_configured: bool


# ============================================
# Voice Session Manager
# ============================================

class VoiceSession:
    """
    Manages a voice conversation session.

    Handles:
    - Real-time STT streaming
    - TTS response generation
    - Orchestrator communication
    """

    def __init__(
        self,
        session_id: str,
        websocket: WebSocket,
        conversation_id: str | None = None,
        contact_id: str | None = None,
    ):
        self.session_id = session_id
        self.websocket = websocket
        self.conversation_id = conversation_id or str(uuid4())
        self.contact_id = contact_id

        self.tts = get_tts_client()
        self.stt = get_stt_client()
        self.transcriber: StreamingTranscriber | None = None

        self._running = False
        self._current_transcript = ""

    async def start(self) -> None:
        """Start the voice session."""
        self._running = True
        logger.info(f"Voice session {self.session_id} started")

        # Send session info to client
        await self.websocket.send_json({
            "type": "session_started",
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
        })

    async def stop(self) -> None:
        """Stop the voice session."""
        self._running = False
        if self.transcriber:
            await self.transcriber.stop()
        logger.info(f"Voice session {self.session_id} stopped")

    async def handle_audio_chunk(self, audio_data: bytes) -> None:
        """
        Handle incoming audio chunk for transcription.

        Args:
            audio_data: Raw audio bytes
        """
        if self.transcriber:
            await self.transcriber.feed_audio(audio_data)

    async def process_transcript(self, transcript: str) -> None:
        """
        Process a complete transcript by sending to orchestrator.

        Args:
            transcript: Transcribed user speech
        """
        if not transcript.strip():
            return

        logger.info(f"Processing transcript: {transcript[:50]}...")

        # Send to orchestrator
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.orchestrator_url}/route",
                    json={
                        "message": transcript,
                        "conversation_id": self.conversation_id,
                        "contact_id": self.contact_id,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

            # Get response text
            response_text = data.get("response", "")

            if response_text:
                # Send text response to client
                await self.websocket.send_json({
                    "type": "response_text",
                    "text": response_text,
                    "category": data.get("category"),
                    "agent_id": data.get("agent_id"),
                })

                # Generate and stream TTS audio
                await self.speak_response(response_text)

        except Exception as e:
            logger.error(f"Error processing transcript: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": "Error processing your request",
            })

    async def speak_response(self, text: str) -> None:
        """
        Generate and send TTS audio for response.

        Args:
            text: Text to synthesize
        """
        try:
            # Notify client that audio is coming
            await self.websocket.send_json({
                "type": "audio_start",
            })

            # Stream audio chunks
            async for chunk in self.tts.synthesize_stream(text):
                await self.websocket.send_bytes(chunk)

            # Notify client that audio is complete
            await self.websocket.send_json({
                "type": "audio_end",
            })

        except Exception as e:
            logger.error(f"TTS error: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": "Error generating audio response",
            })


# Active sessions
_sessions: dict[str, VoiceSession] = {}


# ============================================
# Lifespan Management
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    logger.info(f"Starting Voice Gateway v{settings.service_version}")
    logger.info(f"Orchestrator URL: {settings.orchestrator_url}")

    # Verify API keys are configured
    if settings.elevenlabs_api_key:
        logger.info("ElevenLabs TTS configured")
    else:
        logger.warning("ElevenLabs API key not configured")

    if settings.deepgram_api_key:
        logger.info("Deepgram STT configured")
    else:
        logger.warning("Deepgram API key not configured")

    yield

    # Shutdown
    logger.info("Shutting down Voice Gateway")
    # Close all active sessions
    for session_id, session in _sessions.items():
        await session.stop()
    _sessions.clear()


# ============================================
# FastAPI Application
# ============================================

app = FastAPI(
    title="Gobierno Queretaro - Voice Gateway",
    description="Voice interface for government service agents",
    version=settings.service_version,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# REST Endpoints
# ============================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check voice gateway health status."""
    return HealthResponse(
        status="healthy",
        service="voice-gateway",
        version=settings.service_version,
        tts_configured=bool(settings.elevenlabs_api_key),
        stt_configured=bool(settings.deepgram_api_key),
    )


@app.post("/tts")
async def text_to_speech(request: TextToSpeechRequest):
    """
    Convert text to speech.

    Returns audio as binary response.
    """
    tts = get_tts_client()

    try:
        audio = await tts.synthesize(
            text=request.text,
            voice_id=request.voice_id,
            stability=request.stability,
            similarity_boost=request.similarity_boost,
        )

        return Response(
            content=audio,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"},
        )

    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stt")
async def speech_to_text(request: SpeechToTextRequest):
    """
    Convert speech to text.

    Accepts base64-encoded audio.
    """
    import base64

    stt = get_stt_client()

    try:
        audio = base64.b64decode(request.audio_base64)
        result = await stt.transcribe(
            audio=audio,
            language=request.language,
        )
        transcript = stt.get_transcript_text(result)

        return {
            "transcript": transcript,
            "confidence": result.get("results", {}).get("channels", [{}])[0]
            .get("alternatives", [{}])[0]
            .get("confidence", 0),
        }

    except Exception as e:
        logger.error(f"STT error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
async def voice_query(request: VoiceQueryRequest):
    """
    Process a voice query through the orchestrator.

    1. Transcribes audio to text
    2. Sends to orchestrator
    3. Converts response to speech
    4. Returns both text and audio
    """
    import base64

    stt = get_stt_client()
    tts = get_tts_client()

    try:
        # Transcribe audio
        audio = base64.b64decode(request.audio_base64)
        stt_result = await stt.transcribe(audio=audio)
        transcript = stt.get_transcript_text(stt_result)

        if not transcript:
            return {
                "transcript": "",
                "response": "No pude entender lo que dijiste. Por favor intenta de nuevo.",
                "audio_base64": "",
            }

        # Send to orchestrator
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.orchestrator_url}/route",
                json={
                    "message": transcript,
                    "conversation_id": request.conversation_id,
                    "contact_id": request.contact_id,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        response_text = data.get("response", "")

        # Generate TTS audio
        response_audio = await tts.synthesize(text=response_text)
        audio_base64 = base64.b64encode(response_audio).decode()

        return {
            "transcript": transcript,
            "response": response_text,
            "category": data.get("category"),
            "agent_id": data.get("agent_id"),
            "audio_base64": audio_base64,
        }

    except Exception as e:
        logger.error(f"Voice query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/voices")
async def list_voices():
    """List available TTS voices."""
    tts = get_tts_client()

    try:
        voices = await tts.list_voices()
        return {"voices": voices}
    except Exception as e:
        logger.error(f"List voices error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# WebSocket Endpoint
# ============================================

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: str | None = None,
    contact_id: str | None = None,
):
    """
    WebSocket endpoint for real-time voice interaction.

    Protocol:
    - Client sends binary audio chunks
    - Server sends JSON messages and binary audio responses

    Message types:
    - session_started: Session initialization complete
    - transcript: Interim or final transcript
    - response_text: Text response from agent
    - audio_start: Audio response starting
    - audio_end: Audio response complete
    - error: Error message
    """
    await websocket.accept()

    session_id = str(uuid4())
    session = VoiceSession(
        session_id=session_id,
        websocket=websocket,
        conversation_id=conversation_id,
        contact_id=contact_id,
    )
    _sessions[session_id] = session

    try:
        await session.start()

        # Start transcription session
        def on_transcript(text: str, is_final: bool):
            asyncio.create_task(
                websocket.send_json({
                    "type": "transcript",
                    "text": text,
                    "is_final": is_final,
                })
            )
            if is_final:
                asyncio.create_task(session.process_transcript(text))

        # Create streaming transcriber task
        transcriber = StreamingTranscriber(session.stt)
        session.transcriber = transcriber
        transcribe_task = asyncio.create_task(
            transcriber.start(on_transcript=on_transcript)
        )

        # Handle incoming messages
        while True:
            message = await websocket.receive()

            if "bytes" in message:
                # Audio data
                await session.handle_audio_chunk(message["bytes"])

            elif "text" in message:
                # JSON command
                try:
                    data = json.loads(message["text"])
                    cmd = data.get("type")

                    if cmd == "stop":
                        break

                    elif cmd == "ping":
                        await websocket.send_json({"type": "pong"})

                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e),
        })

    finally:
        await session.stop()
        _sessions.pop(session_id, None)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Gobierno Queretaro Voice Gateway",
        "version": settings.service_version,
        "status": "running",
        "endpoints": {
            "health": "/health",
            "tts": "/tts",
            "stt": "/stt",
            "query": "/query",
            "voices": "/voices",
            "websocket": "/ws",
        },
    }


# ============================================
# Run Server (for development)
# ============================================

if __name__ == "__main__":
    import uvicorn
    from fastapi.responses import Response

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
