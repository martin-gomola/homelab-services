from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Any = ""


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    stream: bool = False
    timeout_seconds: int | None = Field(default=None, ge=10, le=3600)

