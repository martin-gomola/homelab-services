from __future__ import annotations

import os
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.responses import StreamingResponse

from .auth import validate_api_key
from .config import SETTINGS
from .openai_compat import completion_payload, new_completion_meta, stream_events
from .runner import run_codex
from .schemas import ChatCompletionRequest
from .text_format import build_codex_task

app = FastAPI(
    title="Codex OpenAI Bridge",
    description="OpenAI-compatible chat-completions bridge backed by Codex CLI auth token.",
    version="0.1.0",
)


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {
        "ok": True,
        "codex_bin": SETTINGS.codex_bin,
        "workdir": str(SETTINGS.workdir),
        "default_model": SETTINGS.default_model,
        "allow_write": SETTINGS.allow_write,
        "disable_context7": SETTINGS.disable_context7,
        "auth_required": bool(SETTINGS.bridge_api_key),
    }


@app.get("/v1/models")
def models(_auth: None = Depends(validate_api_key)) -> dict[str, Any]:
    configured = [m.strip() for m in os.environ.get("CODEX_MODEL_IDS", "").split(",") if m.strip()]
    if not configured:
        configured = [SETTINGS.default_model or "gpt-5-codex"]
    return {
        "object": "list",
        "data": [
            {
                "id": model,
                "object": "model",
                "created": 0,
                "owned_by": "openai",
            }
            for model in configured
        ],
    }


@app.post("/v1/chat/completions")
def chat_completions(
    request: ChatCompletionRequest,
    _auth: None = Depends(validate_api_key),
):
    model = (request.model or SETTINGS.default_model or "gpt-5-codex").strip()
    timeout_seconds = min(
        request.timeout_seconds or SETTINGS.default_timeout_seconds,
        SETTINGS.max_timeout_seconds,
    )
    task = build_codex_task(request.messages)
    message = run_codex(task, model, timeout_seconds)
    completion_id, created = new_completion_meta()

    if request.stream:
        return StreamingResponse(
            stream_events(model, message, completion_id, created),
            media_type="text/event-stream",
        )

    return completion_payload(model, message, completion_id, created)

