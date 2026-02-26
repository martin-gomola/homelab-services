#!/usr/bin/env python3
"""
Upsert Open WebUI configuration for:
- Context7 (MCP)
- Codex Gateway (OpenAPI)
- Tool-ready model entries (native function calling + tool bindings)

Reads defaults from local .env in this directory.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def build_base_url(dotenv: dict[str, str], cli_base_url: str | None) -> str:
    if cli_base_url:
        return cli_base_url.rstrip("/")
    if os.environ.get("OPENWEBUI_BASE_URL"):
        return os.environ["OPENWEBUI_BASE_URL"].rstrip("/")
    port = dotenv.get("OPENWEBUI_PORT", "3040")
    return f"http://localhost:{port}"


def request_json(
    *,
    base_url: str,
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    insecure: bool = False,
) -> Any:
    url = urllib.parse.urljoin(base_url + "/", path.lstrip("/"))
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    ssl_ctx = ssl._create_unverified_context() if insecure else None

    try:
        with urllib.request.urlopen(req, timeout=45, context=ssl_ctx) as resp:
            body = resp.read().decode("utf-8")
            if not body:
                return {}
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"{method} {url} failed ({exc.code}): {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc}") from exc


def auth_token(
    *,
    base_url: str,
    email: str | None,
    password: str | None,
    token: str | None,
    insecure: bool,
) -> str:
    if token:
        return token
    if not email:
        raise RuntimeError("Missing admin email. Set --email or OPENWEBUI_ADMIN_EMAIL.")
    if not password:
        if sys.stdin.isatty():
            password = getpass.getpass("Open WebUI admin password: ")
        else:
            raise RuntimeError(
                "Missing admin password. Set --password or OPENWEBUI_ADMIN_PASSWORD."
            )
    signin_payload = {"email": email, "password": password}
    resp = request_json(
        base_url=base_url,
        path="/api/v1/auths/signin",
        method="POST",
        payload=signin_payload,
        insecure=insecure,
    )
    t = resp.get("token")
    if not t:
        raise RuntimeError("Sign-in succeeded but no token in response.")
    return t


def upsert_connections(existing: list[dict[str, Any]], desired: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    def key(conn: dict[str, Any]) -> str:
        info = conn.get("info", {}) if isinstance(conn.get("info"), dict) else {}
        cid = str(info.get("id") or "").strip()
        ctype = str(conn.get("type", "openapi")).strip()
        if cid:
            return f"{ctype}:{cid}"
        # fallback key if id missing
        return f"{ctype}:{conn.get('url','')}:{conn.get('path','')}"

    for conn in existing:
        k = key(conn)
        if k not in by_id:
            order.append(k)
        by_id[k] = conn

    for conn in desired:
        k = key(conn)
        if k not in by_id:
            order.append(k)
        by_id[k] = conn

    return [by_id[k] for k in order]


def parse_csv(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def unique_strings(items: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def tool_id_for_connection(conn: dict[str, Any]) -> str | None:
    info = conn.get("info", {}) if isinstance(conn.get("info"), dict) else {}
    conn_id = str(info.get("id") or "").strip()
    if not conn_id:
        return None

    conn_type = str(conn.get("type") or "").strip()
    if conn_type == "mcp":
        return f"server:mcp:{conn_id}"
    return f"server:{conn_id}"


def get_model_by_id(
    *,
    base_url: str,
    token: str,
    model_id: str,
    insecure: bool,
) -> dict[str, Any] | None:
    path = "/api/v1/models/model?" + urllib.parse.urlencode({"id": model_id})
    try:
        model = request_json(
            base_url=base_url,
            path=path,
            method="GET",
            token=token,
            insecure=insecure,
        )
        return model if isinstance(model, dict) else None
    except RuntimeError as err:
        if "(404)" in str(err):
            return None
        raise


def get_prompt_by_command(
    *,
    base_url: str,
    token: str,
    command: str,
    insecure: bool,
) -> dict[str, Any] | None:
    path = "/api/v1/prompts/command/" + urllib.parse.quote(command, safe="")
    try:
        prompt = request_json(
            base_url=base_url,
            path=path,
            method="GET",
            token=token,
            insecure=insecure,
        )
        return prompt if isinstance(prompt, dict) else None
    except RuntimeError as err:
        if "(404)" in str(err):
            return None
        raise


def upsert_prompt(
    *,
    base_url: str,
    token: str,
    command: str,
    name: str,
    content: str,
    insecure: bool,
) -> str:
    existing = get_prompt_by_command(
        base_url=base_url,
        token=token,
        command=command,
        insecure=insecure,
    )

    payload = {
        "command": command,
        "name": name,
        "content": content,
        "data": {},
        "meta": {},
        "tags": [],
    }

    if existing and existing.get("id"):
        request_json(
            base_url=base_url,
            path=f"/api/v1/prompts/id/{existing['id']}/update",
            method="POST",
            payload=payload,
            token=token,
            insecure=insecure,
        )
        return "update"

    request_json(
        base_url=base_url,
        path="/api/v1/prompts/create",
        method="POST",
        payload=payload,
        token=token,
        insecure=insecure,
    )
    return "create"


def build_model_upsert_payload(
    *,
    model_id: str,
    desired_tool_ids: list[str],
    existing_model: dict[str, Any] | None,
    replace_model_tool_ids: bool,
    function_calling_mode: str,
) -> dict[str, Any]:
    existing_meta = {}
    existing_params = {}
    base_model_id = None
    existing_name = None
    is_active = True

    if existing_model:
        if isinstance(existing_model.get("meta"), dict):
            existing_meta = dict(existing_model["meta"])
        if isinstance(existing_model.get("params"), dict):
            existing_params = dict(existing_model["params"])
        if existing_model.get("base_model_id") is not None:
            base_model_id = existing_model.get("base_model_id")
        if existing_model.get("name"):
            existing_name = str(existing_model["name"])
        if isinstance(existing_model.get("is_active"), bool):
            is_active = existing_model["is_active"]

    existing_tool_ids = (
        existing_meta.get("toolIds") if isinstance(existing_meta.get("toolIds"), list) else []
    )
    existing_tool_ids = [str(item) for item in existing_tool_ids if str(item).strip()]

    if replace_model_tool_ids:
        merged_tool_ids = unique_strings(desired_tool_ids)
    else:
        merged_tool_ids = unique_strings(existing_tool_ids + desired_tool_ids)

    existing_meta["toolIds"] = merged_tool_ids
    if "profile_image_url" not in existing_meta:
        existing_meta["profile_image_url"] = "/static/favicon.png"

    existing_params["function_calling"] = function_calling_mode

    return {
        "id": model_id,
        "base_model_id": base_model_id,
        "name": existing_name or model_id,
        "meta": existing_meta,
        "params": existing_params,
        "is_active": is_active,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Upsert Context7/Codex tool servers and tool-ready model settings in Open WebUI."
    )
    parser.add_argument("--base-url", help="Open WebUI base URL (default: http://localhost:$OPENWEBUI_PORT)")
    parser.add_argument("--email", help="Open WebUI admin email")
    parser.add_argument("--password", help="Open WebUI admin password")
    parser.add_argument("--token", help="Existing Open WebUI bearer token (skip sign-in)")
    parser.add_argument(
        "--tool-model-ids",
        help=(
            "Comma-separated model IDs to upsert for tool usage "
            "(default: OPENWEBUI_TOOL_MODEL_IDS or ministral-3:8b)"
        ),
    )
    parser.add_argument(
        "--skip-model-upsert",
        action="store_true",
        help="Only upsert tool server connections (skip model settings)",
    )
    parser.add_argument(
        "--replace-model-tool-ids",
        action="store_true",
        help="Replace model meta.toolIds with desired IDs instead of merging",
    )
    parser.add_argument(
        "--non-native-model-ids",
        help=(
            "Comma-separated model IDs that should use function_calling=default "
            "(default: OPENWEBUI_TOOL_MODEL_NON_NATIVE_IDS)"
        ),
    )
    parser.add_argument(
        "--skip-prompt-upsert",
        action="store_true",
        help="Do not upsert the /codex prompt shortcut",
    )
    parser.add_argument(
        "--codex-command",
        help=(
            "Slash command name without leading '/' "
            "(default: OPENWEBUI_CODEX_SLASH_COMMAND or codex)"
        ),
    )
    parser.add_argument(
        "--codex-prompt-name",
        help=(
            "Prompt display name for the slash command "
            "(default: OPENWEBUI_CODEX_SLASH_NAME or 'Codex Gateway Shortcut')"
        ),
    )
    parser.add_argument(
        "--codex-prompt-content",
        help=(
            "Prompt content inserted by the slash command "
            "(default: OPENWEBUI_CODEX_SLASH_CONTENT)"
        ),
    )
    parser.add_argument("--insecure", action="store_true", help="Disable TLS certificate validation")
    parser.add_argument("--dry-run", action="store_true", help="Do not write; print planned connections")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_dir = script_dir.parent
    if not (repo_dir / ".env").exists() and not (repo_dir / ".env.example").exists():
        repo_dir = script_dir
    dotenv = load_env_file(repo_dir / ".env")

    base_url = build_base_url(dotenv, args.base_url)
    email = args.email or os.environ.get("OPENWEBUI_ADMIN_EMAIL")
    password = args.password or os.environ.get("OPENWEBUI_ADMIN_PASSWORD")

    context7_key = os.environ.get("CONTEXT7_API_KEY") or dotenv.get("MCPO_CONTEXT7_API_KEY", "")
    codex_key = os.environ.get("CODEX_GATEWAY_API_KEY") or dotenv.get("CODEX_GATEWAY_API_KEY", "")
    codex_url = os.environ.get("CODEX_GATEWAY_URL", "http://codex-gateway:8091")
    context7_url = os.environ.get("CONTEXT7_MCP_URL", "https://mcp.context7.com/mcp")
    default_tool_model_ids = (
        args.tool_model_ids
        or os.environ.get("OPENWEBUI_TOOL_MODEL_IDS")
        or dotenv.get("OPENWEBUI_TOOL_MODEL_IDS")
        or "ministral-3:8b"
    )
    tool_model_ids = unique_strings(parse_csv(default_tool_model_ids))
    non_native_model_ids = set(
        parse_csv(
            args.non_native_model_ids
            or os.environ.get("OPENWEBUI_TOOL_MODEL_NON_NATIVE_IDS")
            or dotenv.get("OPENWEBUI_TOOL_MODEL_NON_NATIVE_IDS")
        )
    )
    codex_slash_enabled_raw = (
        os.environ.get("OPENWEBUI_CODEX_SLASH_ENABLE")
        or dotenv.get("OPENWEBUI_CODEX_SLASH_ENABLE")
        or "true"
    )
    codex_slash_enabled = codex_slash_enabled_raw.lower() in {"1", "true", "yes", "on"}
    codex_command = (
        args.codex_command
        or os.environ.get("OPENWEBUI_CODEX_SLASH_COMMAND")
        or dotenv.get("OPENWEBUI_CODEX_SLASH_COMMAND")
        or "codex"
    ).lstrip("/")
    codex_prompt_name = (
        args.codex_prompt_name
        or os.environ.get("OPENWEBUI_CODEX_SLASH_NAME")
        or dotenv.get("OPENWEBUI_CODEX_SLASH_NAME")
        or "Codex Gateway Shortcut"
    )
    codex_prompt_content = (
        args.codex_prompt_content
        or os.environ.get("OPENWEBUI_CODEX_SLASH_CONTENT")
        or dotenv.get("OPENWEBUI_CODEX_SLASH_CONTENT")
        or "Use Codex Gateway tool delegate_delegate_post to complete this task: "
    )

    if not context7_key:
        raise RuntimeError("Missing Context7 key (CONTEXT7_API_KEY or MCPO_CONTEXT7_API_KEY in .env).")
    if not codex_key:
        raise RuntimeError("Missing Codex key (CODEX_GATEWAY_API_KEY in .env).")

    token = auth_token(
        base_url=base_url,
        email=email,
        password=password,
        token=args.token,
        insecure=args.insecure,
    )

    desired = [
        {
            "url": context7_url,
            "path": "",
            "type": "mcp",
            "auth_type": "bearer",
            "headers": {},
            "key": context7_key,
            "config": {"enable": True, "access_grants": []},
            "info": {"id": "context7", "name": "Context7", "description": "Context7 MCP"},
        },
        {
            "url": codex_url,
            "path": "openapi.json",
            "type": "openapi",
            "auth_type": "bearer",
            "headers": {},
            "key": codex_key,
            "config": {"enable": True, "access_grants": []},
            "info": {
                "id": "codex-gateway",
                "name": "Codex Gateway",
                "description": "Codex execution gateway",
            },
        },
    ]

    # Verify desired connections before write.
    for conn in desired:
        request_json(
            base_url=base_url,
            path="/api/v1/configs/tool_servers/verify",
            method="POST",
            payload=conn,
            token=token,
            insecure=args.insecure,
        )

    existing_resp = request_json(
        base_url=base_url,
        path="/api/v1/configs/tool_servers",
        method="GET",
        token=token,
        insecure=args.insecure,
    )
    existing = existing_resp.get("TOOL_SERVER_CONNECTIONS", [])
    merged = upsert_connections(existing, desired)
    desired_tool_ids = unique_strings(
        [tid for conn in desired if (tid := tool_id_for_connection(conn))]
    )

    model_plan: list[dict[str, Any]] = []
    if not args.skip_model_upsert:
        for model_id in tool_model_ids:
            existing_model = get_model_by_id(
                base_url=base_url,
                token=token,
                model_id=model_id,
                insecure=args.insecure,
            )
            model_payload = build_model_upsert_payload(
                model_id=model_id,
                desired_tool_ids=desired_tool_ids,
                existing_model=existing_model,
                replace_model_tool_ids=args.replace_model_tool_ids,
                function_calling_mode=(
                    "default" if model_id in non_native_model_ids else "native"
                ),
            )
            model_plan.append(
                {
                    "action": "update" if existing_model else "create",
                    "model": model_payload,
                }
            )

    if args.dry_run:
        connections_summary = [
            {
                "type": c.get("type"),
                "id": (c.get("info") or {}).get("id"),
                "name": (c.get("info") or {}).get("name"),
                "url": c.get("url"),
                "path": c.get("path"),
            }
            for c in merged
        ]
        print("Planned tool servers:")
        print(json.dumps(connections_summary, indent=2))
        if not args.skip_model_upsert:
            print("Planned model upserts:")
            print(
                json.dumps(
                    [
                        {
                            "action": item.get("action"),
                            "id": item.get("model", {}).get("id"),
                            "function_calling": (
                                item.get("model", {}).get("params", {}).get("function_calling")
                            ),
                            "toolIds": item.get("model", {}).get("meta", {}).get("toolIds", []),
                        }
                        for item in model_plan
                    ],
                    indent=2,
                )
            )
        if codex_slash_enabled and not args.skip_prompt_upsert:
            print("Planned prompt upsert:")
            print(
                json.dumps(
                    {
                        "command": f"/{codex_command}",
                        "name": codex_prompt_name,
                        "content": codex_prompt_content,
                    },
                    indent=2,
                )
            )
        return 0

    set_resp = request_json(
        base_url=base_url,
        path="/api/v1/configs/tool_servers",
        method="POST",
        payload={"TOOL_SERVER_CONNECTIONS": merged},
        token=token,
        insecure=args.insecure,
    )
    applied = set_resp.get("TOOL_SERVER_CONNECTIONS", [])
    print("Applied tool servers:")
    for conn in applied:
        info = conn.get("info", {}) if isinstance(conn.get("info"), dict) else {}
        print(
            f"- {conn.get('type','openapi')} {info.get('name','(unnamed)')} "
            f"[id={info.get('id','')}] {conn.get('url','')}"
        )

    if not args.skip_model_upsert and model_plan:
        import_payload = {"models": [item["model"] for item in model_plan]}
        request_json(
            base_url=base_url,
            path="/api/v1/models/import",
            method="POST",
            payload=import_payload,
            token=token,
            insecure=args.insecure,
        )
        print("Applied model settings:")
        for item in model_plan:
            model = item.get("model", {})
            print(
                f"- {item.get('action')} {model.get('id')} "
                f"(function_calling={model.get('params', {}).get('function_calling')}, "
                f"toolIds={','.join(model.get('meta', {}).get('toolIds', []))})"
            )

    if codex_slash_enabled and not args.skip_prompt_upsert:
        action = upsert_prompt(
            base_url=base_url,
            token=token,
            command=codex_command,
            name=codex_prompt_name,
            content=codex_prompt_content,
            insecure=args.insecure,
        )
        print(f"Applied prompt: {action} /{codex_command} ({codex_prompt_name})")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        raise SystemExit(1)
