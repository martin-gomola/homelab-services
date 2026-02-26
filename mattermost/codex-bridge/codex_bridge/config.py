from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    codex_bin: str
    bridge_api_key: str
    default_model: str
    default_reasoning_effort: str
    disable_context7: bool
    allow_write: bool
    workdir: Path
    state_dir: Path
    default_timeout_seconds: int
    max_timeout_seconds: int
    max_prompt_chars: int
    max_output_chars: int


def _read_bool(name: str, default: str) -> bool:
    return os.environ.get(name, default).lower() == "true"


def load_settings() -> Settings:
    state_dir = Path(os.environ.get("CODEX_STATE_DIR", "/tmp/codex-bridge"))
    state_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        codex_bin=os.environ.get("CODEX_BIN", "codex"),
        bridge_api_key=os.environ.get("CODEX_BRIDGE_API_KEY", ""),
        default_model=os.environ.get("CODEX_DEFAULT_MODEL", "gpt-5-codex").strip(),
        default_reasoning_effort=os.environ.get(
            "CODEX_DEFAULT_REASONING_EFFORT", "low"
        ).strip(),
        disable_context7=_read_bool("CODEX_DISABLE_CONTEXT7", "true"),
        allow_write=_read_bool("CODEX_ALLOW_WRITE", "false"),
        workdir=Path(os.environ.get("CODEX_WORKDIR", "/workspace")).resolve(),
        state_dir=state_dir,
        default_timeout_seconds=int(os.environ.get("CODEX_TIMEOUT_SECONDS", "300")),
        max_timeout_seconds=int(os.environ.get("CODEX_MAX_TIMEOUT_SECONDS", "900")),
        max_prompt_chars=int(os.environ.get("CODEX_MAX_PROMPT_CHARS", "12000")),
        max_output_chars=int(os.environ.get("CODEX_MAX_OUTPUT_CHARS", "24000")),
    )


SETTINGS = load_settings()

