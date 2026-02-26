from __future__ import annotations

import json
import re
from typing import Any

from fastapi import HTTPException, status

from .config import SETTINGS
from .schemas import ChatMessage


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


def normalize_mattermost_markdown(text: str) -> str:
    # Normalize common raw citation style: (site : https://url) -> ([site](https://url))
    text = re.sub(
        r"\(([^()\n:]{2,80})\s*:\s*(https?://[^\s)]+)\)",
        r"([\1](\2))",
        text,
    )
    normalized_lines: list[str] = []
    for line in text.splitlines():
        source_match = re.match(
            r"^\s*(?:[-*•]\s*)?(.{2,140}?)\s*:\s*(https?://\S+)\s*$",
            line,
        )
        if source_match:
            label = source_match.group(1).strip().rstrip(":")
            url = source_match.group(2).rstrip(".,;")
            normalized_lines.append(f"- [{label}]({url})")
            continue

        bare_url_match = re.match(r"^\s*(?:[-*•]\s*)?(https?://\S+)\s*$", line)
        if bare_url_match:
            url = bare_url_match.group(1).rstrip(".,;")
            normalized_lines.append(f"- [Source]({url})")
            continue

        normalized_lines.append(line)

    text = "\n".join(normalized_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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
        "Format replies using Mattermost Markdown for readability.",
        "Prefer this structure for non-trivial answers:",
        "- First line: short title.",
        "- Then concise bullet points.",
        "- Put sources in a final 'Sources' list as [label](url).",
        "Never emit raw citation format like '(site : https://example.com)'.",
        "Keep replies concise unless the user asks for detail.",
    ]
    if system_lines:
        sections.extend(["", "System instructions:", "\n\n".join(system_lines)])
    sections.extend(["", "Conversation:", "\n\n".join(convo_lines), "", "Assistant:"])

    task = "\n".join(sections).strip()
    if len(task) > SETTINGS.max_prompt_chars:
        task = "[Earlier context truncated]\n" + task[-SETTINGS.max_prompt_chars :]
    return task

