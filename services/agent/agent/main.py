"""FastAPI entry point for the Remi agent service with concurrent session management."""

import asyncio
from collections import defaultdict
import os
import time
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
import httpx
from pydantic import BaseModel, Field

from agent.cache import store_cache
from agent.daytona_tasks import get_task, start_delivery_report_task
from agent.graph import session_graph

app = FastAPI(title="Remi Agent Service", version="0.1.0")
_session_locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


class GreetingRequest(BaseModel):
    role: str = Field(min_length=1, max_length=80)
    user: str = Field(min_length=1, max_length=80)


class VoiceTurnRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=80)
    user: str = Field(min_length=1, max_length=80)


class TurnRequest(BaseModel):
    session_id: str = Field(description="Unique session/terminal ID")
    transcript: str = Field(description="User transcript or spoken input")
    account_id: int = Field(default=105, description="Mock staff user ID (105=Server, 106=Manager)")
    role: str = Field(default="server", description="Staff role: server or manager")


class TurnResponse(BaseModel):
    session_id: str
    reply: str
    order_draft: list[dict[str, Any]]
    order_confirmed: bool
    latency_ms: float
    store_context_summary: str


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "remi-agent"}


@app.get("/restaurant/menu")
async def restaurant_menu(account_id: int = 105) -> dict[str, Any]:
    """Read the menu through the selected demo account."""
    from agent.mcp_server import account_scope, get_menu

    try:
        with account_scope(account_id):
            return await get_menu()
    except PermissionError:
        raise HTTPException(status_code=403, detail="The selected demo account cannot access the menu.") from None
    except (httpx.HTTPError, ValueError):
        raise HTTPException(status_code=503, detail="The mock restaurant service is unavailable.") from None


@app.get("/agent/capabilities")
async def agent_capabilities(account_id: int) -> dict[str, Any]:
    """Report staff assistant tools for the selected active demo account."""
    from agent.mcp_server import account_scope, assistant_capabilities
    try:
        with account_scope(account_id):
            return await assistant_capabilities()
    except PermissionError:
        raise HTTPException(status_code=403, detail="The selected demo account is unavailable or disabled.") from None
    except (httpx.HTTPError, ValueError):
        raise HTTPException(status_code=503, detail="Could not verify the selected demo account.") from None


@app.get("/health/dependencies")
async def dependency_health() -> dict[str, object]:
    """Report live mock connector health and honest provider integration state."""
    mock_base_url = os.getenv("MOCK_POS_BASE_URL", "http://localhost:8001").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(1.5, connect=0.75)) as client:
            response = await client.get(f"{mock_base_url}/health")
            response.raise_for_status()
        mock_status = "online"
    except (httpx.HTTPError, ValueError):
        mock_status = "offline"

    def provider_state(key_name: str, detail: str) -> dict[str, str]:
        if os.getenv(key_name):
            return {
                "status": "configured_unverified",
                "detail": detail,
            }
        return {
            "status": "not_configured",
            "detail": "Provider integration and credentials are not configured.",
        }

    return {
        "agent_api": {"status": "online", "detail": "FastAPI agent is responding."},
        "mock_pos": {
            "status": mock_status,
            "detail": "Mock POS, scheduling, and inventory service.",
        },
        "elevenlabs": provider_state("ELEVENLABS_API_KEY", "Credentials found; session greeting TTS is available."),
        "daytona": provider_state("DAYTONA_API_KEY", "Credentials found; run the MarketMan delivery report to verify sandbox access."),
    }


class DaytonaTaskRequest(BaseModel):
    kind: str = Field(default="next_delivery_report", pattern="^next_delivery_report$")
    account_id: int = Field(gt=0)


@app.post("/tasks/daytona", status_code=202)
async def create_daytona_task(payload: DaytonaTaskRequest) -> dict[str, str]:
    """Queue the manager-only MarketMan YTD next-delivery report."""
    from agent.mcp_server import _require_manager, account_scope
    try:
        with account_scope(payload.account_id):
            await _require_manager()
    except PermissionError:
        raise HTTPException(status_code=403, detail="The selected profile must be an active manager.") from None
    except (httpx.HTTPError, ValueError):
        raise HTTPException(status_code=503, detail="Could not verify the selected demo account.") from None
    if not os.getenv("DAYTONA_API_KEY"):
        raise HTTPException(status_code=503, detail="Daytona is not configured on the agent service.")
    mock_base_url = os.getenv("MOCK_POS_BASE_URL", "http://localhost:8001").rstrip("/")
    task_id = start_delivery_report_task(mock_base_url)
    return {"task_id": task_id, "status": "queued"}


@app.get("/tasks/daytona/{task_id}")
async def read_daytona_task(task_id: str) -> dict[str, Any]:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Daytona task not found.")
    return task


@app.post("/voice/greeting")
async def synthesize_session_greeting(payload: GreetingRequest) -> Response:
    """Synthesize the staff session greeting without exposing provider credentials."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="ElevenLabs TTS is not configured.")

    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
    greeting = f"What should we do today {payload.role.strip()}, {payload.user.strip()}?"
    try:
        from elevenlabs.client import AsyncElevenLabs

        client = AsyncElevenLabs(api_key=api_key)
        audio_stream = client.text_to_speech.convert(
            voice_id=voice_id,
            output_format="mp3_22050_32",
            text=greeting,
            model_id=os.getenv("ELEVENLABS_TTS_MODEL_ID", "eleven_flash_v2_5"),
        )
        audio = b"".join([chunk async for chunk in audio_stream])
    except Exception:
        raise HTTPException(status_code=502, detail="ElevenLabs could not synthesize the session greeting.") from None

    return Response(content=audio, media_type="audio/mpeg")


@app.post("/voice/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)) -> dict[str, str]:
    """Transcribe a captured utterance using ElevenLabs Scribe."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="ElevenLabs is not configured on the agent service.")
    audio_bytes = await audio.read(15 * 1024 * 1024 + 1)
    if not audio_bytes or len(audio_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio must be between 1 byte and 15 MB.")
    try:
        from elevenlabs.client import AsyncElevenLabs
        client = AsyncElevenLabs(api_key=api_key)
        result = await client.speech_to_text.convert(
            file=audio_bytes,
            model_id=os.getenv("ELEVENLABS_STT_MODEL_ID", "scribe_v1"),
            tag_audio_events=False,
            language_code="eng",
        )
    except Exception:
        raise HTTPException(status_code=502, detail="ElevenLabs could not transcribe the recording.") from None
    return {"transcript": str(getattr(result, "text", "")).strip()}


@app.post("/voice/turn")
async def process_voice_turn(
    session_id: str = Form(..., min_length=1, max_length=120),
    role: str = Form(..., min_length=1, max_length=80),
    user: str = Form(..., min_length=1, max_length=80),
    account_id: int = Form(default=105, gt=0),
    audio: UploadFile = File(...),
) -> dict[str, Any]:
    """Transcribe one captured staff utterance and return an ElevenLabs spoken reply."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="ElevenLabs is not configured on the agent service.")
    audio_bytes = await audio.read(15 * 1024 * 1024 + 1)
    if not audio_bytes or len(audio_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio must be between 1 byte and 15 MB.")

    try:
        from elevenlabs.client import AsyncElevenLabs

        client = AsyncElevenLabs(api_key=api_key)
        transcription = await client.speech_to_text.convert(
            file=audio_bytes,
            model_id=os.getenv("ELEVENLABS_STT_MODEL_ID", "scribe_v1"),
            tag_audio_events=False,
            language_code="eng",
        )
        transcript = str(getattr(transcription, "text", "")).strip()
        if not transcript:
            raise HTTPException(status_code=422, detail="No speech was detected in the recording.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="ElevenLabs could not transcribe the recording.") from None

    if not session_id or len(session_id) > 120 or not role or len(role) > 80 or not user or len(user) > 80:
        raise HTTPException(status_code=422, detail="Session, role, and user fields are required and must be within limits.")
    turn = await process_agent_turn(TurnRequest(
        session_id=session_id,
        transcript=transcript,
        account_id=account_id,
        role=role.strip().lower(),
    ))
    try:
        speech = client.text_to_speech.convert(
            voice_id=os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB"),
            output_format="mp3_22050_32",
            text=turn.reply,
            model_id=os.getenv("ELEVENLABS_TTS_MODEL_ID", "eleven_flash_v2_5"),
        )
        audio_out = b"".join([chunk async for chunk in speech])
    except Exception:
        raise HTTPException(status_code=502, detail="The agent replied, but ElevenLabs could not synthesize speech.") from None

    import base64
    return {
        "session_id": session_id,
        "transcript": transcript,
        "reply": turn.reply,
        "audio_base64": base64.b64encode(audio_out).decode("ascii"),
        "audio_content_type": "audio/mpeg",
        "latency_ms": turn.latency_ms,
    }


class VoiceReplyRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=80)
    user: str = Field(min_length=1, max_length=80)
    transcript: str = Field(min_length=1, max_length=4000)
    account_id: int = Field(default=105, gt=0)


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


@app.post("/voice/speech")
async def synthesize_text(payload: SpeechRequest) -> Response:
    """Synthesize short UI prompts using the configured ElevenLabs voice."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="ElevenLabs is not configured on the agent service.")
    try:
        from elevenlabs.client import AsyncElevenLabs

        client = AsyncElevenLabs(api_key=api_key)
        stream = client.text_to_speech.convert(
            voice_id=os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB"),
            output_format="mp3_22050_32",
            text=payload.text,
            model_id=os.getenv("ELEVENLABS_TTS_MODEL_ID", "eleven_flash_v2_5"),
        )
        return Response(content=b"".join([chunk async for chunk in stream]), media_type="audio/mpeg")
    except Exception:
        raise HTTPException(status_code=502, detail="ElevenLabs could not synthesize speech.") from None


@app.post("/voice/reply")
async def process_transcribed_voice_turn(payload: VoiceReplyRequest) -> dict[str, Any]:
    """Run a recognized staff utterance through Remi and return ElevenLabs TTS."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    turn = await process_agent_turn(TurnRequest(
        session_id=payload.session_id,
        transcript=payload.transcript.strip(),
        account_id=payload.account_id,
        role=payload.role.strip().lower(),
    ))
    audio_out = b""
    audio_error = None
    try:
        if not api_key:
            raise ValueError("ElevenLabs is not configured.")
        from elevenlabs.client import AsyncElevenLabs

        client = AsyncElevenLabs(api_key=api_key)
        speech = client.text_to_speech.convert(
            voice_id=os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB"),
            output_format="mp3_22050_32",
            text=turn.reply,
            model_id=os.getenv("ELEVENLABS_TTS_MODEL_ID", "eleven_flash_v2_5"),
        )
        audio_out = b"".join([chunk async for chunk in speech])
    except Exception:
        audio_error = "The agent replied, but ElevenLabs speech is unavailable."
    import base64
    return {
        "session_id": payload.session_id,
        "transcript": payload.transcript.strip(),
        "reply": turn.reply,
        "audio_base64": base64.b64encode(audio_out).decode("ascii"),
        "audio_content_type": "audio/mpeg",
        "audio_error": audio_error,
        "latency_ms": turn.latency_ms,
    }


@app.post("/agent/turn", response_model=TurnResponse)
async def process_agent_turn(payload: TurnRequest) -> TurnResponse:
    """Processes a conversational turn for a session, injecting shared store context."""
    start_time = time.perf_counter()

    # 1. Fetch concise shared store context from in-memory cache (<1ms)
    # Read tools fetch current data under the selected demo account. Do not
    # inject a shared roster or cached availability into every conversation.
    store_context = ""

    # 2. Configure LangGraph session checkpoint
    config = {
        "configurable": {
            "thread_id": f"{payload.account_id}:{payload.session_id}",
            "store_context": store_context,
            "account_id": payload.account_id,
        }
    }

    # 3. Invoke LangGraph workflow with input turn.
    # Note: Only pass new messages in input_state so MemorySaver preserves accumulated
    # state (current_draft, order_confirmed, previous messages) across turns for this thread_id.
    input_state: dict[str, Any] = {
        "messages": [{"role": "user", "content": payload.transcript}],
        "session_id": payload.session_id,
        "account_id": payload.account_id,
        "role": payload.role,
    }

    from agent.mcp_server import _require_active_account, account_scope
    try:
        with account_scope(payload.account_id):
            account = await _require_active_account()
            input_state["role"] = str(account.get("role", "")).strip().lower()
            async with _session_locks[config["configurable"]["thread_id"]]:
                final_state = await session_graph.ainvoke(input_state, config=config)
    except PermissionError:
        raise HTTPException(status_code=403, detail="The selected demo account is unavailable or disabled.") from None
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Could not verify the selected demo account with the mock service.") from None
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Graph turn execution error: {exc}")

    last_reply = ""
    for msg in reversed(final_state.get("messages", [])):
        if hasattr(msg, "content"):
            last_reply = str(msg.content)
            break
        elif isinstance(msg, dict) and msg.get("role") == "assistant":
            last_reply = str(msg.get("content", ""))
            break

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    return TurnResponse(
        session_id=payload.session_id,
        reply=last_reply,
        order_draft=final_state.get("current_draft", []),
        order_confirmed=final_state.get("order_confirmed", False),
        latency_ms=round(elapsed_ms, 2),
        store_context_summary=store_context,
    )


class InboundWebhookPayload(BaseModel):
    type: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    sender: str | None = None
    body: str | None = None


@app.post("/webhooks/inbound-sms")
async def receive_inbound_sms(payload: InboundWebhookPayload) -> dict[str, Any]:
    """Catches incoming staff SMS replies (e.g. from Resend or local simulator)."""
    from agent.notifications import record_inbound_reply

    sender = payload.sender or payload.data.get("from", "Unknown Staff")
    body = payload.body or payload.data.get("subject", "No content")
    email_id = payload.data.get("email_id")

    record = record_inbound_reply(sender=sender, body=body, raw_email_id=email_id)
    return {"status": "recorded", "reply": record}
