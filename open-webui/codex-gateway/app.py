import os
import subprocess
import tempfile
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field


CODEX_BIN = os.environ.get("CODEX_BIN", "codex")
CODEX_GATEWAY_API_KEY = os.environ.get("CODEX_GATEWAY_API_KEY", "")
CODEX_DEFAULT_MODEL = os.environ.get("CODEX_DEFAULT_MODEL", "").strip()
CODEX_WORKSPACE_ROOT = Path(
    os.environ.get("CODEX_WORKSPACE_ROOT", "/workspace")
).resolve()
CODEX_STATE_DIR = Path(os.environ.get("CODEX_STATE_DIR", "/tmp/codex-gateway"))
CODEX_STATE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TIMEOUT_SECONDS = int(os.environ.get("CODEX_TIMEOUT_SECONDS", "300"))
MAX_TIMEOUT_SECONDS = int(os.environ.get("CODEX_MAX_TIMEOUT_SECONDS", "900"))
MAX_TASK_CHARS = int(os.environ.get("CODEX_MAX_TASK_CHARS", "8000"))
MAX_OUTPUT_CHARS = int(os.environ.get("CODEX_MAX_OUTPUT_CHARS", "24000"))
ALLOW_WRITE = os.environ.get("CODEX_ALLOW_WRITE", "false").lower() == "true"

security = HTTPBearer(auto_error=False)
app = FastAPI(
    title="Codex Gateway",
    description="Restricted HTTP wrapper for Codex CLI delegation.",
    version="0.1.0",
)


class DelegateRequest(BaseModel):
    task: str = Field(
        ...,
        min_length=3,
        description="Task for Codex. Keep it explicit and actionable.",
    )
    repo_subdir: str = Field(
        default=".",
        description="Relative path under CODEX_WORKSPACE_ROOT.",
    )
    model: str | None = Field(
        default=None,
        description="Optional Codex model override, e.g. o3 or gpt-5-codex.",
    )
    timeout_seconds: int | None = Field(
        default=None,
        ge=10,
        le=3600,
        description="Per-request timeout; capped by CODEX_MAX_TIMEOUT_SECONDS.",
    )


class DelegateResponse(BaseModel):
    success: bool
    return_code: int
    duration_seconds: float
    workdir: str
    message: str
    stdout_tail: str
    stderr_tail: str


def trim_tail(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[-MAX_OUTPUT_CHARS:]


def validate_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> None:
    if not CODEX_GATEWAY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CODEX_GATEWAY_API_KEY is not configured",
        )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    if credentials.credentials != CODEX_GATEWAY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
        )


def resolve_workdir(repo_subdir: str) -> Path:
    target = (CODEX_WORKSPACE_ROOT / repo_subdir).resolve()
    if target != CODEX_WORKSPACE_ROOT and CODEX_WORKSPACE_ROOT not in target.parents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="repo_subdir escapes workspace root",
        )
    if not target.exists() or not target.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Directory does not exist: {repo_subdir}",
        )
    return target


def build_cmd(request: DelegateRequest, workdir: Path, output_file: Path) -> list[str]:
    cmd = [
        CODEX_BIN,
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "workspace-write" if ALLOW_WRITE else "read-only",
        "--cd",
        str(workdir),
        "--output-last-message",
        str(output_file),
    ]

    model = (request.model or CODEX_DEFAULT_MODEL).strip()
    if model:
        cmd.extend(["--model", model])

    cmd.append(request.task)
    return cmd


@app.get("/healthz")
def healthz() -> dict:
    return {
        "ok": True,
        "codex_bin": CODEX_BIN,
        "workspace_root": str(CODEX_WORKSPACE_ROOT),
        "allow_write": ALLOW_WRITE,
    }


@app.post("/delegate", response_model=DelegateResponse)
def delegate(
    request: DelegateRequest,
    _auth: None = Depends(validate_api_key),
) -> DelegateResponse:
    if len(request.task) > MAX_TASK_CHARS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task too long. Max {MAX_TASK_CHARS} characters.",
        )

    workdir = resolve_workdir(request.repo_subdir)
    timeout_seconds = min(
        request.timeout_seconds or DEFAULT_TIMEOUT_SECONDS,
        MAX_TIMEOUT_SECONDS,
    )

    with tempfile.NamedTemporaryFile(
        mode="w", prefix="codex-last-", suffix=".txt", dir=CODEX_STATE_DIR, delete=False
    ) as tmp:
        output_path = Path(tmp.name)

    cmd = build_cmd(request, workdir, output_path)

    start = time.monotonic()
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

    duration = round(time.monotonic() - start, 2)
    message = ""
    if output_path.exists():
        message = output_path.read_text(encoding="utf-8", errors="replace").strip()
        output_path.unlink(missing_ok=True)

    return DelegateResponse(
        success=completed.returncode == 0,
        return_code=completed.returncode,
        duration_seconds=duration,
        workdir=str(workdir),
        message=message,
        stdout_tail=trim_tail(completed.stdout or ""),
        stderr_tail=trim_tail(completed.stderr or ""),
    )
