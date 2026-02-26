#!/usr/bin/env python3
"""Patch default tools prompt to prioritize delegate tool for real-time queries."""

from pathlib import Path


TARGET = Path("/app/backend/open_webui/config.py")

INSERT_AFTER = """- If one or more tools match the query, construct a JSON response containing a "tool_calls" array with objects that include:
   - "name": The tool's name.
   - "parameters": A dictionary of required parameters and their corresponding values.
"""

INSERT_TEXT = """- If the query asks for current, latest, real-time, live, weather, prices, or time-sensitive external information, and a tool named "delegate_delegate_post" exists, prefer using "delegate_delegate_post" instead of documentation lookup tools.
"""


def main() -> int:
    content = TARGET.read_text(encoding="utf-8")
    if INSERT_TEXT in content:
        print("Prompt priority patch already applied.")
        return 0

    if INSERT_AFTER not in content:
        raise RuntimeError("Expected default tools prompt block not found.")

    content = content.replace(INSERT_AFTER, INSERT_AFTER + "\n" + INSERT_TEXT)
    TARGET.write_text(content, encoding="utf-8")
    print("Patched default tools prompt with delegate priority.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
