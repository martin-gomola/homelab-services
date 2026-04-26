#!/usr/bin/env python3
"""Small TRIP by-token API helper with compact local docs.

The performance win is the built-in API catalog for agents. Runtime API calls
read credentials from environment variables or trip/.env; nothing is persisted.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://localhost:8050"
DEFAULT_ENV_FILE = "trip/.env"

API_CATALOG: dict[str, dict[str, Any]] = {
    "categories": {
        "method": "GET",
        "path": "/api/by_token/categories",
        "purpose": "List exact category names for the current API-token user.",
        "required": [],
        "optional": [],
        "cli": "trip_api.py categories list",
        "returns": "array of {id, name, color, image, image_id}",
        "notes": ["Use before place creation because category names are case-sensitive."],
    },
    "place": {
        "method": "POST",
        "path": "/api/by_token/place",
        "purpose": "Create a place from explicit coordinates and metadata.",
        "required": ["category", "name", "lat", "lng", "place"],
        "optional": [
            "image",
            "allowdog",
            "description",
            "price",
            "duration",
            "favorite",
            "visited",
            "gpx",
            "restroom",
        ],
        "cli": (
            "trip_api.py place create --category Culture --name 'Example' "
            "--lat 48.1486 --lng 17.1077 --place 'Bratislava'"
        ),
        "returns": "PlaceRead object",
        "notes": ["category must already exist and match case exactly."],
    },
    "google-search": {
        "method": "POST",
        "path": "/api/by_token/google-search",
        "purpose": "Create a place resolved by Google from a name, Maps place URL, or short link.",
        "required": ["q"],
        "optional": ["category"],
        "cli": "trip_api.py place google-search --query 'British Museum' --category Culture",
        "returns": "PlaceRead object",
        "notes": [
            "Requires a TRIP API token and a Google API key configured in the TRIP account.",
            "Google type mapping wins over the provided category when it maps cleanly.",
        ],
    },
}

API_DOC_SOURCES = [
    "https://itskovacs.github.io/trip/docs/trip-api/generating-api-key/",
    "https://itskovacs.github.io/trip/docs/trip-api/place-creation/",
    "https://itskovacs.github.io/trip/docs/trip-api/place-google-search/",
]


class TripApiError(RuntimeError):
    pass


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        values[key] = value
    return values


def normalize_base_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if not value:
        raise TripApiError("Base URL cannot be empty")
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value


def env_values(args: argparse.Namespace) -> dict[str, str]:
    return parse_env_file(Path(args.env_file).expanduser())


def resolve_base_url(args: argparse.Namespace, *, default_local: bool = False) -> str:
    values = env_values(args)
    base_url = (
        getattr(args, "base_url", None)
        or os.environ.get("TRIP_BASE_URL")
        or values.get("TRIP_LOCAL_BASE_URL")
        or (DEFAULT_BASE_URL if default_local else None)
    )
    if not base_url and default_local:
        base_url = DEFAULT_BASE_URL
    if not base_url:
        raise TripApiError("No base URL set. Pass --base-url or set TRIP_BASE_URL.")
    return normalize_base_url(base_url)


def resolve_credentials(args: argparse.Namespace) -> tuple[str, str]:
    values = env_values(args)
    base_url = resolve_base_url(args, default_local=True)

    token = None
    env_name = getattr(args, "token_env", None)
    if env_name and os.environ.get(env_name):
        token = os.environ[env_name]
    if not token:
        token = values.get(env_name or "TRIP_API_TOKEN")
    if not token:
        raise TripApiError(f"No API token set. Set {env_name or 'TRIP_API_TOKEN'} or provide --env-file.")
    return base_url, token


def request_json(base_url: str, token: str, method: str, path: str, payload: Any | None = None) -> Any:
    if not path.startswith("/"):
        path = "/" + path
    url = base_url + path
    body = None
    headers = {
        "Accept": "application/json",
        "User-Agent": "trip-planner-cli/1.0",
        "X-Api-Token": token,
    }
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            text = raw.decode("utf-8", errors="replace")
            if not text:
                return None
            content_type = response.headers.get("Content-Type", "")
            if "json" in content_type:
                return json.loads(text)
            return text
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise TripApiError(f"HTTP {exc.code} {exc.reason}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise TripApiError(f"Request failed: {exc.reason}") from exc


def request_public_json(base_url: str, path: str) -> Any:
    if not path.startswith("/"):
        path = "/" + path
    request = urllib.request.Request(
        base_url + path,
        headers={"Accept": "application/json", "User-Agent": "trip-planner-cli/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise TripApiError(f"HTTP {exc.code} {exc.reason}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise TripApiError(f"Request failed: {exc.reason}") from exc


def print_json(data: Any) -> None:
    if data is None:
        return
    if isinstance(data, str):
        print(data)
        return
    print(json.dumps(data, indent=2, sort_keys=True))


def load_json_arg(value: str | None) -> Any | None:
    if value is None:
        return None
    if value == "-":
        return json.load(sys.stdin)
    if value.startswith("@"):
        with Path(value[1:]).expanduser().open("r", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(value)


def add_bool(parser: argparse.ArgumentParser, name: str) -> None:
    parser.add_argument(f"--{name}", dest=name.replace("-", "_"), action="store_true", default=None)
    parser.add_argument(f"--no-{name}", dest=name.replace("-", "_"), action="store_false")


def maybe_dry_run(args: argparse.Namespace, method: str, path: str, payload: Any | None) -> bool:
    if not getattr(args, "dry_run", False):
        return False
    base_url, _token = resolve_credentials(args)
    print(f"{method.upper()} {base_url}{path if path.startswith('/') else '/' + path}")
    print("X-Api-Token: <token-from-env>")
    if payload is not None:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return True


def cmd_config(args: argparse.Namespace) -> None:
    values = env_values(args)
    token_env = getattr(args, "token_env", "TRIP_API_TOKEN")
    token_source = "none"
    if token_env and os.environ.get(token_env):
        token_source = f"env:{token_env}"
    elif values.get(token_env):
        token_source = f"env-file:{args.env_file}"
    print_json(
        {
            "base_url": resolve_base_url(args, default_local=True),
            "env_file": args.env_file,
            "env_file_found": Path(args.env_file).expanduser().exists(),
            "token": "set" if token_source != "none" else "missing",
            "token_source": token_source,
        }
    )


def cmd_categories_list(args: argparse.Namespace) -> None:
    if maybe_dry_run(args, "GET", "/api/by_token/categories", None):
        return
    base_url, token = resolve_credentials(args)
    print_json(request_json(base_url, token, "GET", "/api/by_token/categories"))


def place_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.json:
        payload = load_json_arg(args.json)
        if not isinstance(payload, dict):
            raise TripApiError("--json must resolve to a JSON object")
        return payload
    payload: dict[str, Any] = {
        "category": args.category,
        "name": args.name,
        "lat": args.lat,
        "lng": args.lng,
        "place": args.place,
    }
    optional_fields = [
        "image",
        "allowdog",
        "description",
        "price",
        "duration",
        "favorite",
        "visited",
        "restroom",
    ]
    for field in optional_fields:
        value = getattr(args, field)
        if value is not None:
            payload[field] = value
    if args.gpx_file:
        payload["gpx"] = Path(args.gpx_file).expanduser().read_text(encoding="utf-8")
    elif args.gpx is not None:
        payload["gpx"] = args.gpx
    return payload


def cmd_place_create(args: argparse.Namespace) -> None:
    payload = place_payload(args)
    if maybe_dry_run(args, "POST", "/api/by_token/place", payload):
        return
    base_url, token = resolve_credentials(args)
    print_json(request_json(base_url, token, "POST", "/api/by_token/place", payload))


def cmd_google_search(args: argparse.Namespace) -> None:
    payload: dict[str, Any] = {"q": args.query}
    if args.category:
        payload["category"] = args.category
    if maybe_dry_run(args, "POST", "/api/by_token/google-search", payload):
        return
    base_url, token = resolve_credentials(args)
    print_json(request_json(base_url, token, "POST", "/api/by_token/google-search", payload))


def cmd_raw(args: argparse.Namespace) -> None:
    payload = load_json_arg(args.json)
    if maybe_dry_run(args, args.method, args.path, payload):
        return
    base_url, token = resolve_credentials(args)
    print_json(request_json(base_url, token, args.method, args.path, payload))


def format_endpoint(name: str, spec: dict[str, Any]) -> str:
    required = ", ".join(spec["required"]) or "none"
    optional = ", ".join(spec["optional"]) or "none"
    notes = " ".join(spec["notes"])
    return (
        f"{name}: {spec['method']} {spec['path']}\n"
        f"  purpose: {spec['purpose']}\n"
        f"  required: {required}\n"
        f"  optional: {optional}\n"
        f"  cli: {spec['cli']}\n"
        f"  returns: {spec['returns']}\n"
        f"  notes: {notes}"
    )


def cmd_docs_brief(args: argparse.Namespace) -> None:
    print("TRIP by-token API compact context")
    print("Auth: X-Api-Token header; never print token values.")
    print("Default local base URL: http://localhost:8050")
    print("Use `docs live` for a cheap running-app drift check before browsing.")
    for name, spec in API_CATALOG.items():
        required = ", ".join(spec["required"]) or "none"
        optional = ", ".join(spec["optional"]) or "none"
        print(f"- {name}: {spec['method']} {spec['path']}; required={required}; optional={optional}; cli={spec['cli']}")


def cmd_docs_endpoint(args: argparse.Namespace) -> None:
    names = list(API_CATALOG) if args.endpoint == "all" else [args.endpoint]
    for index, name in enumerate(names):
        if index:
            print()
        print(format_endpoint(name, API_CATALOG[name]))


def cmd_docs_json(args: argparse.Namespace) -> None:
    print_json({"endpoints": API_CATALOG, "sources": API_DOC_SOURCES})


def cmd_docs_live(args: argparse.Namespace) -> None:
    base_url = resolve_base_url(args, default_local=True)
    openapi = request_public_json(base_url, "/openapi.json")
    paths = openapi.get("paths", {})
    live: dict[str, list[str]] = {}
    for path, operations in sorted(paths.items()):
        if path.startswith("/api/by_token") and isinstance(operations, dict):
            live[path] = sorted(method.upper() for method in operations)

    catalog_paths = {spec["path"]: spec["method"] for spec in API_CATALOG.values()}
    missing_from_catalog = []
    missing_from_live = []
    for path, methods in live.items():
        for method in methods:
            if catalog_paths.get(path) != method:
                missing_from_catalog.append(f"{method} {path}")
    for path, method in catalog_paths.items():
        if method not in live.get(path, []):
            missing_from_live.append(f"{method} {path}")

    print_json(
        {
            "base_url": base_url,
            "live_by_token_paths": live,
            "catalog_matches_live": not missing_from_catalog and not missing_from_live,
            "missing_from_catalog": missing_from_catalog,
            "missing_from_live": missing_from_live,
        }
    )


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", help="Override TRIP base URL")
    parser.add_argument("--env-file", default=os.environ.get("TRIP_ENV_FILE", DEFAULT_ENV_FILE))
    parser.add_argument("--token-env", default="TRIP_API_TOKEN", help="Environment variable to read token from")
    parser.add_argument("--dry-run", action="store_true", help="Print request details without sending it")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Call TRIP by-token APIs without exposing tokens.")
    add_common(parser)
    subcommands = parser.add_subparsers(dest="command", required=True)

    docs = subcommands.add_parser("docs", help="Compact local TRIP API reference for agents")
    docs_sub = docs.add_subparsers(dest="docs_command", required=True)
    docs_brief = docs_sub.add_parser("brief", help="Print the compact API cheat sheet")
    docs_brief.set_defaults(func=cmd_docs_brief)
    docs_endpoint = docs_sub.add_parser("endpoint", help="Print one endpoint reference")
    docs_endpoint.add_argument("endpoint", choices=["all", *API_CATALOG.keys()])
    docs_endpoint.set_defaults(func=cmd_docs_endpoint)
    docs_json = docs_sub.add_parser("json", help="Print the API catalog as JSON")
    docs_json.set_defaults(func=cmd_docs_json)
    docs_live = docs_sub.add_parser("live", help="Compare the catalog with the running app OpenAPI")
    docs_live.set_defaults(func=cmd_docs_live)

    config = subcommands.add_parser("config", help="Show resolved config without printing tokens")
    config.set_defaults(func=cmd_config)

    categories = subcommands.add_parser("categories", help="Category API commands")
    categories_sub = categories.add_subparsers(dest="categories_command", required=True)
    categories_list = categories_sub.add_parser("list", help="List categories")
    categories_list.set_defaults(func=cmd_categories_list)

    place = subcommands.add_parser("place", help="Place API commands")
    place_sub = place.add_subparsers(dest="place_command", required=True)

    create = place_sub.add_parser("create", help="Create a place")
    create.add_argument("--json", help="JSON object, @file, or - for stdin")
    create.add_argument("--category")
    create.add_argument("--name")
    create.add_argument("--lat", type=float)
    create.add_argument("--lng", type=float)
    create.add_argument("--place")
    create.add_argument("--image")
    add_bool(create, "allowdog")
    create.add_argument("--description")
    create.add_argument("--price", type=float)
    create.add_argument("--duration", type=int)
    add_bool(create, "favorite")
    add_bool(create, "visited")
    add_bool(create, "restroom")
    create.add_argument("--gpx")
    create.add_argument("--gpx-file")
    create.set_defaults(func=cmd_place_create)

    google = place_sub.add_parser("google-search", help="Create a place by Google query, place URL, or short link")
    google.add_argument("--query", "-q", required=True)
    google.add_argument("--category")
    google.set_defaults(func=cmd_google_search)

    raw = subcommands.add_parser("raw", help="Call any by-token endpoint")
    raw.add_argument("method", choices=["GET", "POST", "PUT", "PATCH", "DELETE", "get", "post", "put", "patch", "delete"])
    raw.add_argument("path")
    raw.add_argument("--json", help="JSON value, @file, or - for stdin")
    raw.set_defaults(func=cmd_raw)
    return parser


def validate_required_create_args(args: argparse.Namespace) -> None:
    if getattr(args, "func", None) is not cmd_place_create or args.json:
        return
    missing = [name for name in ["category", "name", "lat", "lng", "place"] if getattr(args, name) is None]
    if missing:
        joined = ", ".join(f"--{name}" for name in missing)
        raise TripApiError(f"Missing required place fields: {joined}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        validate_required_create_args(args)
        args.func(args)
    except TripApiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
