#!/usr/bin/env python3
"""
Upsert Open WebUI tool server connections for:
- Context7 (MCP)
- Codex Gateway (OpenAPI)

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Upsert Context7 MCP + Codex Gateway tool servers in Open WebUI.")
    parser.add_argument("--base-url", help="Open WebUI base URL (default: http://localhost:$OPENWEBUI_PORT)")
    parser.add_argument("--email", help="Open WebUI admin email")
    parser.add_argument("--password", help="Open WebUI admin password")
    parser.add_argument("--token", help="Existing Open WebUI bearer token (skip sign-in)")
    parser.add_argument("--insecure", action="store_true", help="Disable TLS certificate validation")
    parser.add_argument("--dry-run", action="store_true", help="Do not write; print planned connections")
    args = parser.parse_args()

    repo_dir = Path(__file__).resolve().parent
    dotenv = load_env_file(repo_dir / ".env")

    base_url = build_base_url(dotenv, args.base_url)
    email = args.email or os.environ.get("OPENWEBUI_ADMIN_EMAIL")
    password = args.password or os.environ.get("OPENWEBUI_ADMIN_PASSWORD")

    context7_key = os.environ.get("CONTEXT7_API_KEY") or dotenv.get("MCPO_CONTEXT7_API_KEY", "")
    codex_key = os.environ.get("CODEX_GATEWAY_API_KEY") or dotenv.get("CODEX_GATEWAY_API_KEY", "")
    codex_url = os.environ.get("CODEX_GATEWAY_URL", "http://codex-gateway:8091")
    context7_url = os.environ.get("CONTEXT7_MCP_URL", "https://mcp.context7.com/mcp")

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

    if args.dry_run:
        summary = [
            {
                "type": c.get("type"),
                "id": (c.get("info") or {}).get("id"),
                "name": (c.get("info") or {}).get("name"),
                "url": c.get("url"),
                "path": c.get("path"),
            }
            for c in merged
        ]
        print(json.dumps(summary, indent=2))
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
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        raise SystemExit(1)
