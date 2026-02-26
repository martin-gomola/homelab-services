#!/usr/bin/env python3
"""Patch Open WebUI middleware for robust non-native tool-calling flow."""

from pathlib import Path


TARGET = Path("/app/backend/open_webui/utils/middleware.py")

PATCHES = [
    (
        """        if tools_dict:
            if metadata.get("params", {}).get("function_calling") == "native":
                # If the function calling is native, then call the tools function calling handler
                metadata["tools"] = tools_dict
                form_data["tools"] = [
                    {"type": "function", "function": tool.get("spec", {})}
                    for tool in tools_dict.values()
                ]

        else:
            # If the function calling is not native, then call the tools function calling handler
            try:
                form_data, flags = await chat_completion_tools_handler(
                    request, form_data, extra_params, user, models, tools_dict
                )
                sources.extend(flags.get("sources", []))
            except Exception as e:
                log.exception(e)
""",
        """        if tools_dict and metadata.get("params", {}).get("function_calling") == "native":
            # Native function calling: pass tools through the model API.
            metadata["tools"] = tools_dict
            form_data["tools"] = [
                {"type": "function", "function": tool.get("spec", {})}
                for tool in tools_dict.values()
            ]
        elif tools_dict:
            # Non-native function calling: use helper prompt + JSON extraction.
            try:
                form_data, flags = await chat_completion_tools_handler(
                    request, form_data, extra_params, user, models, tools_dict
                )
                sources.extend(flags.get("sources", []))
            except Exception as e:
                log.exception(e)
""",
        "non-native routing",
    ),
    (
        """        try:
            content = content[content.find("{") : content.rfind("}") + 1]
            if not content:
                raise Exception("No JSON object found in the response")

            result = json.loads(content)
""",
        """        try:
            def _json_candidates(raw: str) -> list[str]:
                candidates: list[str] = []

                # First, try fenced JSON blocks.
                for match in re.findall(r"```(?:json)?\\s*([\\s\\S]*?)```", raw, flags=re.IGNORECASE):
                    value = match.strip()
                    if value:
                        candidates.append(value)

                # Then, try every balanced {...} region.
                start = None
                depth = 0
                for idx, ch in enumerate(raw):
                    if ch == "{":
                        if depth == 0:
                            start = idx
                        depth += 1
                    elif ch == "}" and depth > 0:
                        depth -= 1
                        if depth == 0 and start is not None:
                            value = raw[start : idx + 1].strip()
                            if value:
                                candidates.append(value)
                            start = None

                # Keep first occurrence ordering while removing duplicates.
                seen = set()
                unique_candidates: list[str] = []
                for candidate in candidates:
                    if candidate in seen:
                        continue
                    seen.add(candidate)
                    unique_candidates.append(candidate)
                return unique_candidates

            result = None
            for candidate in _json_candidates(content):
                try:
                    result = json.loads(candidate)
                    break
                except Exception:
                    continue

            if result is None:
                raise Exception("No valid JSON object found in the response")
""",
        "JSON extraction",
    ),
    (
        """                tool_function_name = tool_call.get("name", None)
                if tool_function_name not in tools:
                    return body, {}

                tool_function_params = tool_call.get("parameters", {})
""",
        """                tool_function_name = tool_call.get("name") or tool_call.get("function", {}).get("name")
                if tool_function_name not in tools:
                    return body, {}

                tool_function_params = tool_call.get("parameters")
                if tool_function_params is None:
                    tool_function_params = tool_call.get("arguments")
                if tool_function_params is None:
                    tool_function_params = tool_call.get("function", {}).get("arguments", {})

                if isinstance(tool_function_params, str):
                    try:
                        tool_function_params = ast.literal_eval(tool_function_params)
                    except Exception:
                        try:
                            tool_function_params = json.loads(tool_function_params)
                        except Exception:
                            tool_function_params = {}

                if not isinstance(tool_function_params, dict):
                    tool_function_params = {}
""",
        "tool call parsing",
    ),
]


def main() -> int:
    content = TARGET.read_text(encoding="utf-8")
    changed = False

    for old, new, label in PATCHES:
        if new in content:
            continue
        if old not in content:
            raise RuntimeError(f"Expected middleware block not found for patch: {label}")
        content = content.replace(old, new)
        changed = True

    if changed:
        TARGET.write_text(content, encoding="utf-8")
        print("Patched middleware for non-native tool flow and robust JSON/tool parsing.")
    else:
        print("Patch already applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
