from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from fastapi import HTTPException, status

from .config import SETTINGS
from .text_format import normalize_mattermost_markdown


def trim_tail(text: str) -> str:
    if len(text) <= SETTINGS.max_output_chars:
        return text
    return text[-SETTINGS.max_output_chars :]


def build_cmd(task: str, model: str, output_file: Path) -> list[str]:
    cmd = [
        SETTINGS.codex_bin,
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "workspace-write" if SETTINGS.allow_write else "read-only",
        "--cd",
        str(SETTINGS.workdir),
        "--output-last-message",
        str(output_file),
    ]

    if model:
        cmd.extend(["--model", model])

    if SETTINGS.default_reasoning_effort:
        cmd.extend(["-c", f'model_reasoning_effort="{SETTINGS.default_reasoning_effort}"'])
    if SETTINGS.disable_context7:
        cmd.extend(["-c", "mcp_servers.context7.enabled=false"])

    cmd.append(task)
    return cmd


def run_codex(task: str, model: str, timeout_seconds: int) -> str:
    if not SETTINGS.workdir.exists() or not SETTINGS.workdir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"CODEX_WORKDIR is unavailable: {SETTINGS.workdir}",
        )

    with tempfile.NamedTemporaryFile(
        mode="w",
        prefix="codex-last-",
        suffix=".txt",
        dir=SETTINGS.state_dir,
        delete=False,
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
    return normalize_mattermost_markdown(response)

