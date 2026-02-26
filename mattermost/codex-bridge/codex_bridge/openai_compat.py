from __future__ import annotations

import json
import time
import uuid
from typing import Any, Generator


def completion_payload(
    model: str, message: str, completion_id: str, created: int
) -> dict[str, Any]:
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


def stream_events(
    model: str, message: str, completion_id: str, created: int
) -> Generator[str, None, None]:
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


def new_completion_meta() -> tuple[str, int]:
    return f"chatcmpl-{uuid.uuid4().hex}", int(time.time())

