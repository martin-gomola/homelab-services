#!/usr/bin/env python3
import argparse
import html
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0 Safari/537.36"
)


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    return value.replace(",,", ", ").strip()


def normalize_transport_types(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(",") if item.strip()]


def parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def load_route_config(path: str, route_name: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    routes = data.get("routes", {})
    if route_name not in routes:
        raise KeyError(f"Route '{route_name}' not found in {path}")
    route = dict(routes[route_name])
    route["route_name"] = route_name
    return route


def resolve_route(args: argparse.Namespace) -> dict:
    if bool(args.config) != bool(args.route):
        raise ValueError("Pass both --config and --route together, or neither.")

    if args.config and args.route:
        route = load_route_config(args.config, args.route)
    else:
        route = {
            "from_stop": args.from_stop,
            "from_code": args.from_code,
            "to_stop": args.to_stop,
            "to_code": args.to_code,
            "timezone": args.timezone,
            "limit": args.limit,
            "direct": args.direct,
            "af": args.af,
            "trt": args.trt,
            "label": args.route or "Commute",
        }

    for key in ("from_stop", "from_code", "to_stop", "to_code"):
        if not route.get(key):
            raise ValueError(f"Missing route config value: {key}")

    route["timezone"] = route.get("timezone", args.timezone)
    route["limit"] = int(route.get("limit", args.limit))
    route["direct"] = parse_bool(route.get("direct", args.direct))
    route["af"] = parse_bool(route.get("af", args.af))
    route["trt"] = normalize_transport_types(route.get("trt", args.trt))
    route["label"] = route.get("label") or route.get("route_name") or "Commute"
    route["from_stop"] = str(route["from_stop"])
    route["from_code"] = str(route["from_code"])
    route["to_stop"] = str(route["to_stop"])
    route["to_code"] = str(route["to_code"])
    return route


def build_query_params(route: dict, now: datetime) -> dict:
    params = {
        "date": now.strftime("%d.%m.%Y"),
        "time": now.strftime("%H:%M"),
        "f": route["from_stop"],
        "fc": route["from_code"],
        "t": route["to_stop"],
        "tc": route["to_code"],
    }
    if route.get("direct"):
        params["direct"] = "true"
    if route.get("af"):
        params["af"] = "true"
    if route.get("trt"):
        params["trt"] = ",".join(route["trt"])
    return params


def fetch_page(route: dict) -> tuple[str, str, datetime]:
    tz_name = route["timezone"]
    now = datetime.now(ZoneInfo(tz_name))
    params = build_query_params(route, now)
    url = "https://cp.sk/vlakbusmhd/spojenie/vysledky/?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        text = response.read().decode("utf-8", "ignore")
    return url, text, now


def parse_connections(page: str, now: datetime, limit: int) -> list[dict]:
    trips = []
    for part in page.split('<div id="connectionBox-')[1:]:
        chunk = part.split('<div class="connection-expand">', 1)[0]
        departure_match = re.search(r'<h2 class="[^"]*\bdate\b[^"]*">\s*([^<\s]+)', chunk)
        departure_date_match = re.search(r'<span class="date-after">(\d{1,2})\.(\d{1,2})\.', chunk)
        duration_match = re.search(r"Celkový čas\s*<strong>([^<]+)</strong>", chunk)
        time_matches = re.findall(r'<p class="reset time[^>]*>([^<]+)</p>', chunk)
        line_matches = re.findall(r"<h3[^>]*>.*?<span>(.*?)</span>.*?</h3>", chunk, re.S)
        stop_matches = re.findall(r'<strong class="name[^"]*">(.*?)</strong>', chunk, re.S)

        if not departure_match or len(time_matches) < 2:
            continue

        departure = html.unescape(departure_match.group(1)).strip()
        arrival = html.unescape(time_matches[-1]).strip()
        duration = html.unescape(duration_match.group(1)).strip() if duration_match else ""
        lines = [normalize_text(html.unescape(item).strip()) for item in line_matches]
        stops = [normalize_text(html.unescape(item).strip()) for item in stop_matches]

        departure_dt = now.replace(
            hour=int(departure.split(":")[0]),
            minute=int(departure.split(":")[1]),
            second=0,
            microsecond=0,
        )
        if departure_date_match:
            day = int(departure_date_match.group(1))
            month = int(departure_date_match.group(2))
            departure_dt = departure_dt.replace(day=day, month=month)
            if departure_dt < now:
                departure_dt = departure_dt.replace(year=departure_dt.year + 1)
        elif departure_dt < now:
            departure_dt = departure_dt + timedelta(days=1)

        minutes_until = max(0, int((departure_dt - now).total_seconds() // 60))

        trips.append(
            {
                "departure": departure,
                "arrival": arrival,
                "duration": duration,
                "lines": list(dict.fromkeys(lines)),
                "from_stop": stops[0] if stops else None,
                "to_stop": stops[-1] if stops else None,
                "minutes_until": minutes_until,
            }
        )

        if len(trips) >= limit:
            break

    return trips


def build_payload(args: argparse.Namespace) -> dict:
    route = resolve_route(args)
    url, page, now = fetch_page(route)
    trips = parse_connections(page=page, now=now, limit=route["limit"])
    if not trips:
        return {
            "state": "unavailable",
            "error": None,
            "route_name": route["label"],
            "route_from": route["from_stop"],
            "route_to": route["to_stop"],
            "direct_only": route["direct"],
            "advanced_filters": route["af"],
            "transport_types": route["trt"],
            "query_url": url,
            "updated_at": now.isoformat(),
            "connections": [],
        }

    first = trips[0]
    return {
        "state": first["departure"],
        "error": None,
        "next_departure": first["departure"],
        "next_arrival": first["arrival"],
        "next_duration": first["duration"],
        "next_lines": first["lines"],
        "next_minutes_until": first["minutes_until"],
        "route_name": route["label"],
        "route_from": route["from_stop"],
        "route_to": route["to_stop"],
        "direct_only": route["direct"],
        "advanced_filters": route["af"],
        "transport_types": route["trt"],
        "query_url": url,
        "updated_at": now.isoformat(),
        "connections": trips,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    parser.add_argument("--route")
    parser.add_argument("--from-stop")
    parser.add_argument("--from-code")
    parser.add_argument("--to-stop")
    parser.add_argument("--to-code")
    parser.add_argument("--timezone", default="Europe/Bratislava")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--direct", action="store_true")
    parser.add_argument("--af", action="store_true")
    parser.add_argument("--trt")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        payload = build_payload(args)
    except Exception as exc:
        payload = {
            "state": "unavailable",
            "error": str(exc),
            "route_name": args.route or "Commute",
            "route_from": normalize_text(args.from_stop),
            "route_to": normalize_text(args.to_stop),
            "connections": [],
        }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
