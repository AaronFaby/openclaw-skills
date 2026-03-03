#!/usr/bin/env python3
"""
Cloudflare Zone Analytics Fetcher

Full report (default: last 24 hours) with graceful fallbacks.
Backwards-compatible flags: --days, --format csv/json.
"""

import sys
import os
import json
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import requests
except ImportError:
    print("Error: requests module not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

API_URL = "https://api.cloudflare.com/client/v4/graphql"


def load_credentials(env_path=None):
    if not env_path:
        env_path = Path.home() / ".openclaw/workspace/.secrets/cloudflare.env"

    api_key = os.environ.get("CLOUDFLARE_API_KEY")
    zone_id = os.environ.get("CLOUDFLARE_ZONE_ID")
    if api_key and zone_id:
        return api_key, zone_id

    if Path(env_path).exists():
        for line in Path(env_path).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()
        return os.environ.get("CLOUDFLARE_API_KEY"), os.environ.get("CLOUDFLARE_ZONE_ID")

    return None, None


def parse_iso_datetime(value: str, flag_name: str) -> datetime:
    v = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        print(f"Error: invalid {flag_name} value '{value}'. Use ISO format like 2026-03-02T00:00:00Z", file=sys.stderr)
        sys.exit(1)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0)


def parse_time_window(args) -> Tuple[datetime, datetime, str]:
    now = datetime.now(timezone.utc).replace(microsecond=0)

    since = parse_iso_datetime(args.since, "--since") if args.since else None
    until = parse_iso_datetime(args.until, "--until") if args.until else None

    if since or until:
        if since is None:
            print("Error: --since is required when --until is provided", file=sys.stderr)
            sys.exit(1)
        until = until or now
        if since >= until:
            print("Error: --since must be earlier than --until", file=sys.stderr)
            sys.exit(1)
        return since, until, f"{since.isoformat()} to {until.isoformat()}"

    if args.hours is not None:
        if args.hours <= 0:
            print("Error: --hours must be > 0", file=sys.stderr)
            sys.exit(1)
        return now - timedelta(hours=args.hours), now, f"last {args.hours} hours"

    if args.days is not None:
        if args.days <= 0:
            print("Error: --days must be > 0", file=sys.stderr)
            sys.exit(1)
        return now - timedelta(days=args.days), now, f"last {args.days} days"

    return now - timedelta(hours=24), now, "last 24 hours"


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def run_query(api_key: str, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"query": query, "variables": variables},
        timeout=45,
    )
    response.raise_for_status()
    return response.json()


def extract_zone(payload: Dict[str, Any]) -> Dict[str, Any]:
    zones = (((payload or {}).get("data") or {}).get("viewer") or {}).get("zones") or []
    return zones[0] if zones else {}


def to_num(v: Any) -> float:
    try:
        return float(v or 0)
    except (ValueError, TypeError):
        return 0.0


def fmt_int(v: Any) -> str:
    return f"{int(round(to_num(v))):,}"


def fmt_bytes(v: Any) -> str:
    b = to_num(v)
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while b >= 1024 and i < len(units) - 1:
        b /= 1024
        i += 1
    return f"{int(b)} {units[i]}" if i == 0 else f"{b:.2f} {units[i]}"


def safe_pct(n: Any, d: Any) -> str:
    dn = to_num(d)
    if dn <= 0:
        return "n/a"
    return f"{(100 * to_num(n) / dn):.1f}%"


def merge_map_items(rows: List[Dict[str, Any]], field: str, key_field: str, numeric_fields: List[str]) -> List[Dict[str, Any]]:
    agg: Dict[str, Dict[str, float]] = {}
    for r in rows:
        for item in ((r.get("sum") or {}).get(field) or []):
            key = str(item.get(key_field) if item.get(key_field) is not None else "Unknown")
            if key not in agg:
                agg[key] = {k: 0.0 for k in numeric_fields}
            for nf in numeric_fields:
                agg[key][nf] += to_num(item.get(nf))

    out = []
    for k, vals in agg.items():
        row = {key_field: k}
        row.update(vals)
        out.append(row)

    if numeric_fields:
        out.sort(key=lambda x: x.get(numeric_fields[0], 0), reverse=True)
    return out


def fetch_analytics(api_key: str, zone_id: str, since: datetime, until: datetime) -> Dict[str, Any]:
    q = """
    query($zoneTag: string!, $since: Time!, $until: Time!) {
      viewer {
        zones(filter: { zoneTag: $zoneTag }) {
          httpRequests1hGroups(
            limit: 10000
            filter: { datetime_geq: $since, datetime_lt: $until }
          ) {
            dimensions { date datetime }
            sum {
              bytes
              cachedBytes
              cachedRequests
              edgeRequestBytes
              encryptedBytes
              encryptedRequests
              pageViews
              requests
              threats
              browserMap { uaBrowserFamily pageViews }
              contentTypeMap { edgeResponseContentTypeName requests bytes }
              countryMap { clientCountryName requests bytes threats }
              responseStatusMap { edgeResponseStatus requests }
            }
            uniq { uniques }
          }
        }
      }
    }
    """

    variables = {"zoneTag": zone_id, "since": iso(since), "until": iso(until)}
    result = {"window": variables.copy(), "sections": {}, "warnings": []}

    try:
        payload = run_query(api_key, q, variables)
    except requests.exceptions.RequestException as e:
        result["warnings"].append(f"request failed: {e}")
        return result

    if payload.get("errors"):
        for err in payload["errors"]:
            result["warnings"].append(err.get("message", "query error"))

    zone = extract_zone(payload)
    rows = zone.get("httpRequests1hGroups") or []
    if rows:
        result["sections"]["hourly"] = rows

        # Pre-aggregate breakdowns for easy formatting.
        result["sections"]["countries"] = merge_map_items(
            rows, "countryMap", "clientCountryName", ["requests", "bytes", "threats"]
        )
        result["sections"]["status_codes"] = merge_map_items(
            rows, "responseStatusMap", "edgeResponseStatus", ["requests"]
        )
        result["sections"]["content_types"] = merge_map_items(
            rows, "contentTypeMap", "edgeResponseContentTypeName", ["requests", "bytes"]
        )
        result["sections"]["browsers"] = merge_map_items(
            rows, "browserMap", "uaBrowserFamily", ["pageViews"]
        )
    else:
        result["warnings"].append("No hourly data returned for this window")

    return result


def totals(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    t = {
        "requests": 0.0,
        "pageViews": 0.0,
        "bytes": 0.0,
        "cachedBytes": 0.0,
        "cachedRequests": 0.0,
        "encryptedRequests": 0.0,
        "encryptedBytes": 0.0,
        "edgeRequestBytes": 0.0,
        "threats": 0.0,
        "uniques": 0.0,
    }
    for r in rows:
        s = r.get("sum") or {}
        u = r.get("uniq") or {}
        for k in [
            "requests",
            "pageViews",
            "bytes",
            "cachedBytes",
            "cachedRequests",
            "encryptedRequests",
            "encryptedBytes",
            "edgeRequestBytes",
            "threats",
        ]:
            t[k] += to_num(s.get(k))
        t["uniques"] += to_num(u.get("uniques"))
    return t


def format_human(bundle: Dict[str, Any], timeframe_label: str) -> str:
    s = bundle.get("sections") or {}
    rows = s.get("hourly") or []
    t = totals(rows)

    lines = [
        "Cloudflare Analytics Report",
        f"• Window: {timeframe_label}",
        f"• UTC range: {bundle['window']['since']} → {bundle['window']['until']}",
        "",
        "Overview",
        f"• Requests: {fmt_int(t['requests'])}",
        f"• Page views: {fmt_int(t['pageViews'])}",
        f"• Unique visitors (hourly-summed): {fmt_int(t['uniques'])}",
        f"• Bandwidth (edge response): {fmt_bytes(t['bytes'])}",
        f"• Edge request bytes: {fmt_bytes(t['edgeRequestBytes'])}",
        f"• Cached bandwidth: {fmt_bytes(t['cachedBytes'])} ({safe_pct(t['cachedBytes'], t['bytes'])})",
        f"• Cached requests: {fmt_int(t['cachedRequests'])} ({safe_pct(t['cachedRequests'], t['requests'])})",
        f"• Encrypted requests: {fmt_int(t['encryptedRequests'])} ({safe_pct(t['encryptedRequests'], t['requests'])})",
        f"• Encrypted bandwidth: {fmt_bytes(t['encryptedBytes'])} ({safe_pct(t['encryptedBytes'], t['bytes'])})",
        f"• Threats: {fmt_int(t['threats'])}",
    ]

    countries = s.get("countries") or []
    if countries:
        lines += ["", "Top countries (by requests)"]
        for c in countries[:5]:
            lines.append(
                f"• {c.get('clientCountryName','Unknown')}: {fmt_int(c.get('requests'))} req | "
                f"{fmt_bytes(c.get('bytes'))} | {fmt_int(c.get('threats'))} threats"
            )

    statuses = s.get("status_codes") or []
    if statuses:
        lines += ["", "Response status breakdown"]
        for st in statuses[:8]:
            code = st.get("edgeResponseStatus", "unknown")
            req = st.get("requests", 0)
            lines.append(f"• {code}: {fmt_int(req)} ({safe_pct(req, t['requests'])})")

    ctypes = s.get("content_types") or []
    if ctypes:
        lines += ["", "Top content types"]
        for ct in ctypes[:5]:
            name = ct.get("edgeResponseContentTypeName") or "unknown"
            lines.append(f"• {name}: {fmt_int(ct.get('requests'))} req | {fmt_bytes(ct.get('bytes'))}")

    browsers = s.get("browsers") or []
    if browsers:
        lines += ["", "Top browsers (by page views)"]
        for b in browsers[:5]:
            lines.append(f"• {b.get('uaBrowserFamily','Unknown')}: {fmt_int(b.get('pageViews'))} views")

    if rows:
        peak = max(rows, key=lambda r: to_num((r.get("sum") or {}).get("requests")))
        peak_dt = (peak.get("dimensions") or {}).get("datetime", "n/a")
        peak_req = (peak.get("sum") or {}).get("requests", 0)
        lines += ["", "Traffic pattern", f"• Peak hour (UTC): {peak_dt} with {fmt_int(peak_req)} requests"]

    warnings = bundle.get("warnings") or []
    if warnings:
        lines += ["", "Notes"]
        for w in warnings:
            lines.append(f"• {w}")

    return "\n".join(lines)


def format_csv(rows: List[Dict[str, Any]]) -> str:
    lines = ["datetime_utc,visitors,pageviews,requests,bandwidth_mb,cached_kb"]
    for r in rows:
        dt = (r.get("dimensions") or {}).get("datetime", "")
        s = r.get("sum") or {}
        u = r.get("uniq") or {}
        lines.append(
            f"{dt},{int(to_num(u.get('uniques')))},{int(to_num(s.get('pageViews')))}"
            f",{int(to_num(s.get('requests')))},{to_num(s.get('bytes'))/(1024**2):.1f},{to_num(s.get('cachedBytes'))/1024:.0f}"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Fetch Cloudflare Zone Analytics")
    parser.add_argument("--hours", type=int, help="Rolling window in hours (default when no window flags: 24)")
    parser.add_argument("--since", help="Start time (ISO 8601, e.g. 2026-03-02T00:00:00Z)")
    parser.add_argument("--until", help="End time (ISO 8601, defaults to now when used with --since)")
    parser.add_argument("--days", type=int, help="Legacy rolling window in days (backward compatibility)")
    parser.add_argument("--format", choices=["human", "json", "csv"], default="human")
    parser.add_argument("--env", help="Path to .env file with credentials")
    parser.add_argument("--zone-id", help="Cloudflare Zone ID (overrides env)")
    parser.add_argument("--api-key", help="Cloudflare API key (overrides env)")
    args = parser.parse_args()

    api_key, zone_id = load_credentials(args.env)
    if args.api_key:
        api_key = args.api_key
    if args.zone_id:
        zone_id = args.zone_id

    if not api_key or not zone_id:
        print("Error: CLOUDFLARE_API_KEY and CLOUDFLARE_ZONE_ID must be set", file=sys.stderr)
        print("Set them in environment or provide ~/.openclaw/workspace/.secrets/cloudflare.env", file=sys.stderr)
        sys.exit(1)

    since, until, timeframe_label = parse_time_window(args)
    bundle = fetch_analytics(api_key, zone_id, since, until)

    rows = (bundle.get("sections") or {}).get("hourly") or []
    if not rows:
        print("No analytics data available", file=sys.stderr)
        for w in bundle.get("warnings") or []:
            print(f"Warning: {w}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(bundle, indent=2))
    elif args.format == "csv":
        print(format_csv(rows))
    else:
        print(format_human(bundle, timeframe_label))


if __name__ == "__main__":
    main()
