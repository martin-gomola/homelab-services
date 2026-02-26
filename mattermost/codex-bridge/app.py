import json
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field


CODEX_BIN = os.environ.get("CODEX_BIN", "codex")
CODEX_BRIDGE_API_KEY = os.environ.get("CODEX_BRIDGE_API_KEY", "")
CODEX_DEFAULT_MODEL = os.environ.get("CODEX_DEFAULT_MODEL", "gpt-5-codex").strip()
CODEX_DEFAULT_REASONING_EFFORT = os.environ.get(
    "CODEX_DEFAULT_REASONING_EFFORT", "low"
).strip()
CODEX_DISABLE_CONTEXT7 = os.environ.get("CODEX_DISABLE_CONTEXT7", "true").lower() == "true"
CODEX_ALLOW_WRITE = os.environ.get("CODEX_ALLOW_WRITE", "false").lower() == "true"
CODEX_WORKDIR = Path(os.environ.get("CODEX_WORKDIR", "/workspace")).resolve()
CODEX_STATE_DIR = Path(os.environ.get("CODEX_STATE_DIR", "/tmp/codex-bridge"))
CODEX_STATE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TIMEOUT_SECONDS = int(os.environ.get("CODEX_TIMEOUT_SECONDS", "300"))
MAX_TIMEOUT_SECONDS = int(os.environ.get("CODEX_MAX_TIMEOUT_SECONDS", "900"))
MAX_PROMPT_CHARS = int(os.environ.get("CODEX_MAX_PROMPT_CHARS", "12000"))
MAX_OUTPUT_CHARS = int(os.environ.get("CODEX_MAX_OUTPUT_CHARS", "24000"))

security = HTTPBearer(auto_error=False)
app = FastAPI(
    title="Codex OpenAI Bridge",
    description="OpenAI-compatible chat-completions bridge backed by Codex CLI auth token.",
    version="0.1.0",
)


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Any = ""


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    stream: bool = False
    timeout_seconds: int | None = Field(default=None, ge=10, le=3600)


def trim_tail(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[-MAX_OUTPUT_CHARS:]


def validate_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> None:
    if not CODEX_BRIDGE_API_KEY:
        return
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    if credentials.credentials != CODEX_BRIDGE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
        )


def extract_content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if not isinstance(item, dict):
                continue
            text = item.get("text") or item.get("content")
            if isinstance(text, str):
                parts.append(text)
        return "\n".join(part for part in parts if part.strip())
    if content is None:
        return ""
    return json.dumps(content, ensure_ascii=False)


def build_codex_task(messages: list[ChatMessage]) -> str:
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="messages cannot be empty",
        )

    system_lines: list[str] = []
    convo_lines: list[str] = []
    for message in messages:
        text = extract_content_text(message.content).strip()
        if not text:
            continue
        if message.role == "system":
            system_lines.append(text)
        else:
            convo_lines.append(f"{message.role}: {text}")

    if not convo_lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user/assistant/tool message content to process",
        )

    sections = [
        "You are answering inside Mattermost chat.",
        "Reply with plain text, concise and useful.",
    ]
    if system_lines:
        sections.extend(["", "System instructions:", "\n\n".join(system_lines)])
    sections.extend(["", "Conversation:", "\n\n".join(convo_lines), "", "Assistant:"])

    task = "\n".join(sections).strip()
    if len(task) > MAX_PROMPT_CHARS:
        task = "[Earlier context truncated]\n" + task[-MAX_PROMPT_CHARS:]
    return task


def build_cmd(task: str, model: str, output_file: Path) -> list[str]:
    cmd = [
        CODEX_BIN,
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "workspace-write" if CODEX_ALLOW_WRITE else "read-only",
        "--cd",
        str(CODEX_WORKDIR),
        "--output-last-message",
        str(output_file),
    ]

    if model:
        cmd.extend(["--model", model])

    if CODEX_DEFAULT_REASONING_EFFORT:
        cmd.extend(["-c", f'model_reasoning_effort="{CODEX_DEFAULT_REASONING_EFFORT}"'])
    if CODEX_DISABLE_CONTEXT7:
        cmd.extend(["-c", "mcp_servers.context7.enabled=false"])

    cmd.append(task)
    return cmd


def run_codex(task: str, model: str, timeout_seconds: int) -> str:
    if not CODEX_WORKDIR.exists() or not CODEX_WORKDIR.is_dir():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"CODEX_WORKDIR is unavailable: {CODEX_WORKDIR}",
        )

    with tempfile.NamedTemporaryFile(
        mode="w", prefix="codex-last-", suffix=".txt", dir=CODEX_STATE_DIR, delete=False
    ) as tmp:
        output_file = Path(tmp.name)

    cmd = build_cmd(task, model, output_file)
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env={**os.environ, "HOME": os.environ.get("HOME", "/home/codex")},
        )
    except subprocess.TimeoutExpired as err:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Codex timed out after {timeout_seconds} seconds",
        ) from err

    response = ""
    if output_file.exists():
        response = output_file.read_text(encoding="utf-8", errors="replace").strip()
        output_file.unlink(missing_ok=True)

    if not response:
        response = trim_tail(completed.stdout or "").strip()

    if completed.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Codex CLI failed. "
                f"return_code={completed.returncode}, stderr={trim_tail(completed.stderr or '')}"
            ),
        )
    if not response:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Codex returned an empty response",
        )
    return response


def completion_payload(model: str, message: str, completion_id: str, created: int) -> dict[str, Any]:
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": message},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def stream_events(model: str, message: str, completion_id: str, created: int):
    base = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
    }

    first = {
        **base,
        "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
    }
    yield f"data: {json.dumps(first, ensure_ascii=False)}\n\n"

    second = {
        **base,
        "choices": [{"index": 0, "delta": {"content": message}, "finish_reason": None}],
    }
    yield f"data: {json.dumps(second, ensure_ascii=False)}\n\n"

    third = {
        **base,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(third, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {
        "ok": True,
        "codex_bin": CODEX_BIN,
        "workdir": str(CODEX_WORKDIR),
        "default_model": CODEX_DEFAULT_MODEL,
        "allow_write": CODEX_ALLOW_WRITE,
        "disable_context7": CODEX_DISABLE_CONTEXT7,
        "auth_required": bool(CODEX_BRIDGE_API_KEY),
    }


@app.get("/v1/models")
def models(_auth: None = Depends(validate_api_key)) -> dict[str, Any]:
    configured = [m.strip() for m in os.environ.get("CODEX_MODEL_IDS", "").split(",") if m.strip()]
    if not configured:
        configured = [CODEX_DEFAULT_MODEL or "gpt-5-codex"]
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
    model = (request.model or CODEX_DEFAULT_MODEL or "gpt-5-codex").strip()
    timeout_seconds = min(request.timeout_seconds or DEFAULT_TIMEOUT_SECONDS, MAX_TIMEOUT_SECONDS)
    task = build_codex_task(request.messages)
    message = run_codex(task, model, timeout_seconds)
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    if request.stream:
        return StreamingResponse(
            stream_events(model, message, completion_id, created),
            media_type="text/event-stream",
        )

    return completion_payload(model, message, completion_id, created)
