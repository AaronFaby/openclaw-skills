#!/usr/bin/env python3
"""Google Search Console (Webmasters v3) helper CLI.

Features:
- List verified sites/properties
- Query Search Analytics
- List sitemaps for a property
- URL Inspection helper (Search Console URL Inspection API)

Credential loading pattern (no secrets in repo):
- GSC_CLIENT_SECRET_FILE: OAuth client JSON (Desktop app client)
- GSC_TOKEN_FILE: token file path (default: ~/.config/openclaw/google-search-console-token.json)
- GSC_SCOPES: comma-separated OAuth scopes (optional)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

Request = None
Credentials = None

DEFAULT_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
WEBMASTERS_BASE = "https://www.googleapis.com/webmasters/v3"
INSPECTION_BASE = "https://searchconsole.googleapis.com/v1"


def _ensure_google_auth() -> None:
    global Request, Credentials
    if Request is not None and Credentials is not None:
        return
    try:
        from google.auth.transport.requests import Request as _Request
        from google.oauth2.credentials import Credentials as _Credentials
    except Exception as exc:
        raise RuntimeError(
            "Missing dependency: google-auth. Install with: pip install google-auth google-auth-oauthlib requests"
        ) from exc
    Request = _Request
    Credentials = _Credentials


def _token_file() -> Path:
    return Path(
        os.environ.get(
            "GSC_TOKEN_FILE",
            os.path.expanduser("~/.config/openclaw/google-search-console-token.json"),
        )
    )


def _scopes() -> List[str]:
    raw = os.environ.get("GSC_SCOPES", "")
    if not raw.strip():
        return DEFAULT_SCOPES
    return [s.strip() for s in raw.split(",") if s.strip()]


def _load_creds(interactive: bool = True) -> Credentials:
    _ensure_google_auth()
    token_path = _token_file()
    scopes = _scopes()

    creds: Optional[Credentials] = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes=scopes)

    if creds and creds.valid:
        return creds

    if creds and creds.refresh_token and (not creds.valid or creds.expired):
        creds.refresh(Request())
        _save_token(creds, token_path)
        return creds

    if not interactive:
        raise RuntimeError(
            "No valid token available. Run an interactive command first to authenticate."
        )

    client_secret = os.environ.get("GSC_CLIENT_SECRET_FILE", "").strip()
    if not client_secret:
        raise RuntimeError(
            "GSC_CLIENT_SECRET_FILE is not set. Provide your OAuth client JSON path."
        )

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency: google-auth-oauthlib. Install with: pip install google-auth-oauthlib"
        ) from exc

    flow = InstalledAppFlow.from_client_secrets_file(client_secret, scopes=scopes)
    creds = flow.run_local_server(port=0)
    _save_token(creds, token_path)
    return creds


def _save_token(creds: Credentials, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(creds.to_json(), encoding="utf-8")


def _auth_header(creds: Credentials) -> Dict[str, str]:
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_token(creds, _token_file())
    if not creds.valid:
        raise RuntimeError("Credentials are not valid. Re-authentication required.")
    return {"Authorization": f"Bearer {creds.token}"}


def _request(
    creds: Optional[Credentials],
    method: str,
    url: str,
    *,
    json_body: Optional[Dict[str, Any]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    if dry_run:
        payload = {
            "method": method,
            "url": url,
            "json": json_body,
        }
        print(json.dumps(payload, indent=2))
        return payload

    if creds is None:
        raise RuntimeError("Credentials are required unless --dry-run is used.")

    headers = _auth_header(creds)
    headers["Content-Type"] = "application/json"

    resp = requests.request(method, url, headers=headers, json=json_body, timeout=60)

    if resp.status_code >= 400:
        detail = ""
        try:
            detail = json.dumps(resp.json(), indent=2)
        except Exception:
            detail = resp.text

        if "urlInspection" in url and resp.status_code in (403, 404):
            detail += (
                "\n\nHint: URL Inspection requires the Search Console URL Inspection API "
                "enabled in your Google Cloud project, and the inspected URL must belong "
                "to a verified property."
            )
        raise RuntimeError(f"HTTP {resp.status_code}: {detail}")

    if not resp.text.strip():
        return {}

    return resp.json()


def cmd_sites(args: argparse.Namespace) -> None:
    creds = _load_creds(interactive=not args.non_interactive) if not args.dry_run else None
    url = f"{WEBMASTERS_BASE}/sites"
    data = _request(creds, "GET", url, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(data, indent=2))
        return

    entries = data.get("siteEntry", []) if isinstance(data, dict) else []
    if not entries:
        print("No sites returned.")
        return

    for e in entries:
        print(f"- {e.get('siteUrl')} [{e.get('permissionLevel', 'unknown')}]")


def _parse_filters(filter_args: List[str]) -> List[Dict[str, str]]:
    filters: List[Dict[str, str]] = []
    for raw in filter_args:
        parts = raw.split("=", 2)
        if len(parts) != 3:
            raise ValueError(
                f"Invalid filter '{raw}'. Expected: dimension=operator=expression"
            )
        dimension, operator, expression = parts
        filters.append(
            {
                "dimension": dimension,
                "operator": operator,
                "expression": expression,
            }
        )
    return filters


def cmd_analytics(args: argparse.Namespace) -> None:
    creds = _load_creds(interactive=not args.non_interactive) if not args.dry_run else None
    site_quoted = quote(args.site_url, safe="")
    url = f"{WEBMASTERS_BASE}/sites/{site_quoted}/searchAnalytics/query"

    body: Dict[str, Any] = {
        "startDate": args.start_date,
        "endDate": args.end_date,
        "rowLimit": args.row_limit,
        "startRow": args.start_row,
    }

    if args.dimensions:
        body["dimensions"] = args.dimensions
    if args.search_type:
        body["type"] = args.search_type
    if args.aggregation_type:
        body["aggregationType"] = args.aggregation_type
    if args.data_state:
        body["dataState"] = args.data_state
    if args.filter:
        body["dimensionFilterGroups"] = [
            {"groupType": "and", "filters": _parse_filters(args.filter)}
        ]

    data = _request(creds, "POST", url, json_body=body, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(data, indent=2))
        return

    rows = data.get("rows", []) if isinstance(data, dict) else []
    if not rows:
        print("No rows returned.")
        return

    for row in rows:
        keys = row.get("keys", [])
        clicks = row.get("clicks", 0)
        impressions = row.get("impressions", 0)
        ctr = row.get("ctr", 0)
        position = row.get("position", 0)
        print(
            f"- keys={keys} | clicks={clicks} | impressions={impressions} | ctr={ctr:.4f} | position={position:.2f}"
        )


def cmd_sitemaps(args: argparse.Namespace) -> None:
    creds = _load_creds(interactive=not args.non_interactive) if not args.dry_run else None
    site_quoted = quote(args.site_url, safe="")
    url = f"{WEBMASTERS_BASE}/sites/{site_quoted}/sitemaps"
    data = _request(creds, "GET", url, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(data, indent=2))
        return

    sitemaps = data.get("sitemap", []) if isinstance(data, dict) else []
    if not sitemaps:
        print("No sitemaps returned.")
        return

    for sm in sitemaps:
        path = sm.get("path", "")
        last_submitted = sm.get("lastSubmitted") or "n/a"
        status = sm.get("isPending")
        status_text = "pending" if status else "processed"
        print(f"- {path} | {status_text} | lastSubmitted={last_submitted}")


def cmd_inspect(args: argparse.Namespace) -> None:
    creds = _load_creds(interactive=not args.non_interactive) if not args.dry_run else None
    url = f"{INSPECTION_BASE}/urlInspection/index:inspect"
    body = {
        "inspectionUrl": args.inspection_url,
        "siteUrl": args.site_url,
        "languageCode": args.language,
    }

    data = _request(creds, "POST", url, json_body=body, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(data, indent=2))
        return

    result = data.get("inspectionResult", {})
    index_status = result.get("indexStatusResult", {})
    rich = result.get("richResultsResult", {})

    print(f"- coverageState: {index_status.get('coverageState', 'n/a')}")
    print(f"- verdict: {index_status.get('verdict', 'n/a')}")
    print(f"- indexingState: {index_status.get('indexingState', 'n/a')}")
    print(f"- pageFetchState: {index_status.get('pageFetchState', 'n/a')}")
    print(f"- lastCrawlTime: {index_status.get('lastCrawlTime', 'n/a')}")
    print(f"- robotsTxtState: {index_status.get('robotsTxtState', 'n/a')}")
    print(f"- richResultsVerdict: {rich.get('verdict', 'n/a')}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Google Search Console CLI helper")
    p.add_argument("--dry-run", action="store_true", help="Print request payload instead of calling API")
    p.add_argument("--non-interactive", action="store_true", help="Do not start OAuth browser flow")

    sub = p.add_subparsers(dest="command", required=True)

    p_sites = sub.add_parser("sites", help="List verified sites/properties")
    p_sites.add_argument("--json", action="store_true", help="Print raw JSON")
    p_sites.set_defaults(func=cmd_sites)

    p_ana = sub.add_parser("analytics", help="Query Search Analytics")
    p_ana.add_argument("--site-url", required=True, help="Property URL, e.g. sc-domain:example.com or https://example.com/")
    p_ana.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    p_ana.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    p_ana.add_argument(
        "--dimensions",
        nargs="*",
        default=[],
        help="Dimensions, e.g. query page country device date",
    )
    p_ana.add_argument("--row-limit", type=int, default=25)
    p_ana.add_argument("--start-row", type=int, default=0)
    p_ana.add_argument(
        "--search-type",
        choices=["web", "image", "video", "news", "discover", "googleNews"],
        default="web",
    )
    p_ana.add_argument(
        "--aggregation-type",
        choices=["auto", "byPage", "byProperty", "byNewsShowcasePanel"],
    )
    p_ana.add_argument("--data-state", choices=["final", "all"])
    p_ana.add_argument(
        "--filter",
        action="append",
        default=[],
        help="dimension=operator=expression (repeatable), e.g. query=contains=brand",
    )
    p_ana.add_argument("--json", action="store_true", help="Print raw JSON")
    p_ana.set_defaults(func=cmd_analytics)

    p_sm = sub.add_parser("sitemaps", help="List sitemaps for a property")
    p_sm.add_argument("--site-url", required=True)
    p_sm.add_argument("--json", action="store_true", help="Print raw JSON")
    p_sm.set_defaults(func=cmd_sitemaps)

    p_in = sub.add_parser("inspect", help="Inspect URL indexing status (if API is enabled)")
    p_in.add_argument("--site-url", required=True, help="Must match a verified property")
    p_in.add_argument("--inspection-url", required=True, help="Absolute URL to inspect")
    p_in.add_argument("--language", default="en-US")
    p_in.add_argument("--json", action="store_true", help="Print raw JSON")
    p_in.set_defaults(func=cmd_inspect)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        args.func(args)
        return 0
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
