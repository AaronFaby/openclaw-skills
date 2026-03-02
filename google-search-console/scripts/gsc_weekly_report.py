#!/usr/bin/env python3
"""Weekly GSC report generator + email sender.

Fetches last 7 days of Search Analytics data and sitemap status for all
configured properties, produces a markdown report, and emails it via the
gmail-imap-ops SMTP script.

Usage (dry-run, default):
    python3 skills/google-search-console/scripts/gsc_weekly_report.py

Usage (real send):
    python3 skills/google-search-console/scripts/gsc_weekly_report.py --send

Environment:
    GSC_CLIENT_SECRET_FILE  Path to OAuth client JSON
    GSC_TOKEN_FILE          Path to cached token file
    GSC_SCOPES              Comma-separated OAuth scopes (optional)
    GMAIL_ENV_FILE          Path to gmail.env credentials file (optional)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

# ── paths ──────────────────────────────────────────────────────────────────
WORKSPACE = Path(__file__).resolve().parents[3]  # …/workspace
GSC_CLI = WORKSPACE / "skills" / "google-search-console" / "scripts" / "gsc_cli.py"
SMTP_SEND = WORKSPACE / "skills" / "gmail-imap-ops" / "scripts" / "gmail_smtp_send.py"
REPORTS_DIR = WORKSPACE / "memory" / "reports" / "gsc"

PROPERTIES = [
    "sc-domain:macaddress.net",
    "sc-domain:subagentic.ai",
]
RECIPIENT = "asynchronously@icloud.com"
TOP_N_QUERIES = 15
TOP_N_PAGES = 10


# ── GSC helpers ────────────────────────────────────────────────────────────

def _run_gsc(args: list[str], env: dict) -> dict | list | None:
    """Run gsc_cli.py and return parsed JSON, or None on error.

    Note: --non-interactive is a global flag and must precede the subcommand.
    The args list passed here starts with the subcommand (e.g. 'analytics'),
    so we prepend global flags before it.
    """
    cmd = [sys.executable, str(GSC_CLI), "--non-interactive"] + args + ["--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        # Log the error to stderr for cron log visibility
        print(f"[gsc] cmd failed (exit {result.returncode}): {' '.join(cmd[3:5])}", file=sys.stderr)
        if result.stderr.strip():
            # Print only last 3 lines of stderr (skip library warnings)
            last_lines = [l for l in result.stderr.splitlines() if not l.strip().startswith("/") and "Warning" not in l and "warn(" not in l]
            if last_lines:
                print(f"[gsc] stderr: {last_lines[-1]}", file=sys.stderr)
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _date_range() -> tuple[str, str]:
    today = date.today()
    # GSC data lags ~2 days; anchor end to 2 days ago for completeness
    end = today - timedelta(days=2)
    start = end - timedelta(days=6)  # 7-day window
    return start.isoformat(), end.isoformat()


def _pct(n: float) -> str:
    return f"{n * 100:.1f}%"


def _pos(n: float) -> str:
    return f"{n:.1f}"


# ── markdown → HTML ────────────────────────────────────────────────────────

def md_to_html(text: str) -> str:
    """Convert the GSC report's markdown subset to HTML (stdlib only)."""

    lines = text.splitlines()
    out: list[str] = []
    in_table = False
    in_list = False
    table_row_idx = 0  # for alternating row colours

    def flush_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    def flush_table():
        nonlocal in_table, table_row_idx
        if in_table:
            out.append("</tbody></table>")
            in_table = False
            table_row_idx = 0

    def inline(s: str) -> str:
        """Handle **bold**, _italic_, and bare URLs."""
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"_(.+?)_", r"<em>\1</em>", s)
        # Linkify bare http URLs
        s = re.sub(r"(?<![\"'>])(https?://[^\s<>\"]+)", r'<a href="\1">\1</a>', s)
        return s

    for line in lines:
        # Horizontal rule
        if re.fullmatch(r"-{3,}", line.strip()):
            flush_list()
            flush_table()
            out.append("<hr>")
            continue

        # ATX headings
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            flush_list()
            flush_table()
            level = len(m.group(1))
            out.append(f"<h{level}>{inline(m.group(2).strip())}</h{level}>")
            continue

        # Table rows
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            # Detect separator row (---|--- pattern)
            if all(re.fullmatch(r":?-+:?", c) for c in cells if c):
                # Open tbody on the separator row (header already added)
                out.append("<tbody>")
                table_row_idx = 0
                continue
            if not in_table:
                flush_list()
                in_table = True
                out.append('<table><thead>')
                row_html = "".join(f"<th>{inline(c)}</th>" for c in cells)
                out.append(f"<tr>{row_html}</tr></thead>")
            else:
                cls = 'class="alt"' if table_row_idx % 2 else ""
                row_html = "".join(f"<td>{inline(c)}</td>" for c in cells)
                out.append(f"<tr {cls}>{row_html}</tr>" if cls else f"<tr>{row_html}</tr>")
                table_row_idx += 1
            continue
        else:
            flush_table()

        # Unordered list items
        m = re.match(r"^[-*]\s+(.*)", line)
        if m:
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(m.group(1))}</li>")
            continue

        # Blank line — close open blocks
        if not line.strip():
            flush_list()
            out.append("<p></p>")
            continue

        # Plain paragraph / inline text (catch-all)
        flush_list()
        out.append(f"<p>{inline(line)}</p>")

    flush_list()
    flush_table()

    body = "\n".join(out)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: #1a1a1a;
    max-width: 700px;
    margin: 32px auto;
    padding: 0 16px;
  }}
  h1 {{ font-size: 1.6em; border-bottom: 2px solid #e0e0e0; padding-bottom: 6px; }}
  h2 {{ font-size: 1.3em; margin-top: 2em; color: #2c3e50; }}
  h3 {{ font-size: 1.1em; margin-top: 1.5em; color: #34495e; }}
  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
    font-size: 13px;
  }}
  th, td {{
    border: 1px solid #d0d0d0;
    padding: 6px 10px;
    text-align: left;
  }}
  th {{ background: #f0f4f8; font-weight: 600; }}
  tr.alt td {{ background: #f8f9fa; }}
  ul {{ padding-left: 1.4em; }}
  li {{ margin: 4px 0; }}
  hr {{ border: none; border-top: 1px solid #e0e0e0; margin: 1.5em 0; }}
  a {{ color: #2980b9; text-decoration: none; }}
  p:empty {{ margin: 0.4em 0; }}
</style>
</head>
<body>
{body}
</body>
</html>"""


# ── Anthropic recommendations ──────────────────────────────────────────────

def _load_anthropic_key() -> str | None:
    """Load ANTHROPIC_API_KEY from .secrets/anthropic.env."""
    env_file = WORKSPACE / ".secrets" / "anthropic.env"
    if not env_file.exists():
        return None
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def _anthropic_recommendations(prop: str, rows: list, p_rows: list, sitemaps: list) -> str | None:
    """Call Anthropic claude-haiku-4-5 for SEO recommendations.

    Returns a markdown bullet list string, or None on failure.
    """
    api_key = _load_anthropic_key()
    if not api_key:
        return None

    display = prop.replace("sc-domain:", "")

    # Build a plain-text data summary for the prompt
    summary_parts = [f"Site: {display}"]

    if rows:
        summary_parts.append("\nTop search queries (click | impressions | CTR | avg position):")
        for r in rows[:10]:
            q = r.get("keys", ["?"])[0]
            clicks = int(r.get("clicks", 0))
            impr = int(r.get("impressions", 0))
            ctr = f"{r.get('ctr', 0) * 100:.1f}%"
            pos = f"{r.get('position', 0):.1f}"
            summary_parts.append(f"  - \"{q}\": {clicks} clicks, {impr} impressions, {ctr} CTR, pos {pos}")
    else:
        summary_parts.append("\nNo query data available.")

    if p_rows:
        summary_parts.append("\nTop pages by clicks:")
        for r in p_rows[:5]:
            page = r.get("keys", ["?"])[0]
            clicks = int(r.get("clicks", 0))
            impr = int(r.get("impressions", 0))
            pos = f"{r.get('position', 0):.1f}"
            summary_parts.append(f"  - {page}: {clicks} clicks, {impr} impressions, pos {pos}")
    else:
        summary_parts.append("\nNo page data available.")

    if sitemaps:
        summary_parts.append("\nSitemaps:")
        for sm in sitemaps:
            contents = sm.get("contents", [])
            indexed = sum(int(c.get("indexed", 0) or 0) for c in contents)
            submitted = sum(int(c.get("submitted", 0) or 0) for c in contents)
            sm_status = "pending" if sm.get("isPending") else "processed"
            summary_parts.append(
                f"  - {sm.get('path', '?')}: {sm_status} | submitted {submitted} | indexed {indexed}"
            )

    data_summary = "\n".join(summary_parts)

    prompt = (
        "You are an SEO analyst reviewing last week's Google Search Console data. "
        "Based on the data below, provide 3-5 specific, actionable recommendations "
        "to improve search visibility and click-through rates. "
        "Format your response as a markdown bullet list (- item). "
        "Be concrete — reference actual queries or pages from the data where relevant.\n\n"
        f"{data_summary}"
    )

    payload = json.dumps({
        "model": "claude-haiku-4-5",
        "max_tokens": 512,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body.get("content", [])
        if content and content[0].get("type") == "text":
            return content[0]["text"].strip()
        return None
    except Exception as exc:
        print(f"[gsc] Anthropic API call failed: {exc}", file=sys.stderr)
        return None


def _hardcoded_recommendations(rows: list, p_rows: list, sitemaps: list) -> list[str]:
    """Fallback rule-based recommendations (kept as safety net)."""
    recs = []

    if rows:
        low_ctr = [
            r for r in rows
            if r.get("impressions", 0) >= 100 and r.get("ctr", 1) < 0.03
        ]
        if low_ctr:
            recs.append(
                f"**Low CTR, high impression queries** (improve title/meta): "
                + ", ".join(f'"{r["keys"][0]}"' for r in low_ctr[:3])
            )

        page2 = [
            r for r in rows
            if 10 < r.get("position", 0) <= 20
        ]
        if page2:
            recs.append(
                f"**Near page-1 queries** (positions 11–20, worth a content push): "
                + ", ".join(f'"{r["keys"][0]}" (pos {_pos(r["position"])})'
                            for r in page2[:3])
            )

        top_click = sorted(rows, key=lambda r: r.get("clicks", 0), reverse=True)[:3]
        if top_click:
            recs.append(
                "**Top click drivers** (maintain & interlink): "
                + ", ".join(f'"{r["keys"][0]}"' for r in top_click)
            )

    if p_rows:
        dead_pages = [
            r for r in p_rows
            if r.get("impressions", 0) >= 50 and r.get("clicks", 0) == 0
        ]
        if dead_pages:
            recs.append(
                "**Pages with impressions but 0 clicks** (check titles/snippets): "
                + ", ".join(r["keys"][0] for r in dead_pages[:2])
            )

    if sitemaps:
        pending_sm = [sm for sm in sitemaps if sm.get("isPending")]
        if pending_sm:
            recs.append(
                f"**Sitemap(s) still pending** — check for crawl errors: "
                + ", ".join(sm.get("path", "?") for sm in pending_sm)
            )

    return recs


# ── report builders ────────────────────────────────────────────────────────

def build_property_section(prop: str, start: str, end: str, env: dict) -> str:
    display = prop.replace("sc-domain:", "")
    lines = [f"## {display}\n"]

    # ── Top queries ──────────────────────────────────────────────────────
    q_data = _run_gsc(
        [
            "analytics",
            "--site-url", prop,
            "--start-date", start,
            "--end-date", end,
            "--dimensions", "query",
            "--row-limit", str(TOP_N_QUERIES),
        ],
        env,
    )
    rows = (q_data or {}).get("rows", [])

    lines.append(f"### Top Queries ({start} → {end})\n")
    if rows:
        lines.append("| # | Query | Clicks | Impressions | CTR | Avg Position |")
        lines.append("|---|-------|-------:|------------:|----:|-------------:|")
        for i, r in enumerate(rows, 1):
            q = r.get("keys", ["?"])[0]
            clicks = int(r.get("clicks", 0))
            impr = int(r.get("impressions", 0))
            ctr = _pct(r.get("ctr", 0))
            pos = _pos(r.get("position", 0))
            lines.append(f"| {i} | {q} | {clicks} | {impr} | {ctr} | {pos} |")
    else:
        lines.append("_No query data returned._")
    lines.append("")

    # ── Top pages ────────────────────────────────────────────────────────
    p_data = _run_gsc(
        [
            "analytics",
            "--site-url", prop,
            "--start-date", start,
            "--end-date", end,
            "--dimensions", "page",
            "--row-limit", str(TOP_N_PAGES),
        ],
        env,
    )
    p_rows = (p_data or {}).get("rows", [])

    lines.append(f"### Top Pages by Clicks\n")
    if p_rows:
        lines.append("| # | Page | Clicks | Impressions | CTR | Avg Position |")
        lines.append("|---|------|-------:|------------:|----:|-------------:|")
        for i, r in enumerate(p_rows, 1):
            page = r.get("keys", ["?"])[0]
            # truncate long URLs for readability
            page_disp = page if len(page) <= 70 else page[:67] + "…"
            clicks = int(r.get("clicks", 0))
            impr = int(r.get("impressions", 0))
            ctr = _pct(r.get("ctr", 0))
            pos = _pos(r.get("position", 0))
            lines.append(f"| {i} | {page_disp} | {clicks} | {impr} | {ctr} | {pos} |")
    else:
        lines.append("_No page data returned._")
    lines.append("")

    # ── Sitemaps ─────────────────────────────────────────────────────────
    sm_data = _run_gsc(["sitemaps", "--site-url", prop], env)
    sitemaps = (sm_data or {}).get("sitemap", [])

    lines.append("### Sitemaps\n")
    if sitemaps:
        for sm in sitemaps:
            path = sm.get("path", "?")
            pending = sm.get("isPending", False)
            last_sub = sm.get("lastSubmitted", "n/a")
            last_dl = sm.get("lastDownloaded", "n/a")
            status = "⏳ pending" if pending else "✅ processed"
            contents = sm.get("contents", [])
            indexed = sum(int(c.get("indexed", 0) or 0) for c in contents)
            submitted = sum(int(c.get("submitted", 0) or 0) for c in contents)
            lines.append(f"- **{path}** — {status}")
            lines.append(f"  - Last submitted: {last_sub} | Last downloaded: {last_dl}")
            if submitted:
                lines.append(f"  - URLs submitted: {submitted} | indexed: {indexed}")
    else:
        lines.append("_No sitemap data returned._")
    lines.append("")

    # ── Recommendations ──────────────────────────────────────────────────
    lines.append("### Recommendations\n")

    # Try AI-generated recommendations first
    ai_recs = _anthropic_recommendations(prop, rows, p_rows, sitemaps)
    if ai_recs:
        lines.append(ai_recs)
    else:
        # Fall back to hardcoded rule-based logic
        recs = _hardcoded_recommendations(rows, p_rows, sitemaps)
        if recs:
            for r in recs:
                lines.append(f"- {r}")
        else:
            lines.append("_No specific recommendations this week — everything looks healthy._")
    lines.append("")

    return "\n".join(lines)


def build_report(start: str, end: str, env: dict) -> str:
    today_str = date.today().strftime("%A, %B %-d, %Y")
    header = f"""# Weekly Search Console Report
**Generated:** {today_str}
**Data window:** {start} → {end}

---

"""
    sections = []
    for prop in PROPERTIES:
        print(f"  Fetching data for {prop}…", file=sys.stderr)
        sections.append(build_property_section(prop, start, end, env))

    footer = """---
*Report generated by gsc_weekly_report.py — edit PROPERTIES list in script to add/remove sites.*
"""
    return header + "\n".join(sections) + footer


# ── email + output ─────────────────────────────────────────────────────────

def save_report(report: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"gsc-weekly-{date.today().isoformat()}.md"
    out = REPORTS_DIR / filename
    out.write_text(report, encoding="utf-8")
    return out


def send_report(report_md: str, dry_run: bool, env: dict) -> None:
    subject = f"GSC Weekly Report — {date.today().strftime('%b %-d, %Y')}"
    smtp_env = {**env}
    gmail_env_file = os.environ.get(
        "GMAIL_ENV_FILE",
        str(WORKSPACE / ".secrets" / "gmail.env"),
    )

    html_body = md_to_html(report_md)

    cmd = [
        sys.executable, str(SMTP_SEND),
        "--to", RECIPIENT,
        "--subject", subject,
        "--body", html_body,
        "--html",
        "--env", gmail_env_file,
    ]
    if not dry_run:
        cmd.append("--no-dry-run")

    result = subprocess.run(cmd, capture_output=True, text=True, env=smtp_env)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        print(f"[email] subprocess exited {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


# ── main ───────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Weekly GSC report + email")
    ap.add_argument(
        "--send", dest="send", action="store_true", default=False,
        help="Actually send the email (default: dry-run only)",
    )
    ap.add_argument(
        "--report-only", action="store_true", default=False,
        help="Generate and save report but skip email entirely",
    )
    ap.add_argument(
        "--output", metavar="FILE",
        help="Write report to this path (in addition to default memory/reports/gsc/)",
    )
    args = ap.parse_args()

    # Build env for subprocess calls (inherit + required GSC vars)
    env = {**os.environ}
    # Always force-expand these paths — env vars inherited from shell may contain
    # unexpanded $HOME literals which Python's Path() won't resolve.
    env["GSC_CLIENT_SECRET_FILE"] = str(WORKSPACE / ".secrets" / "google-oauth.json")
    env["GSC_TOKEN_FILE"] = str(Path.home() / ".config" / "openclaw" / "google-search-console-token.json")
    env.setdefault(
        "GSC_SCOPES",
        "https://www.googleapis.com/auth/webmasters.readonly",
    )

    start, end = _date_range()
    print(f"[gsc-weekly] Building report for {start} → {end}", file=sys.stderr)

    report = build_report(start, end, env)

    # Always save to memory/reports/gsc/
    saved_path = save_report(report)
    print(f"[gsc-weekly] Report saved: {saved_path}", file=sys.stderr)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"[gsc-weekly] Also written to: {args.output}", file=sys.stderr)

    if args.report_only:
        print(report)
        return 0

    dry_run = not args.send
    mode = "DRY-RUN" if dry_run else "REAL SEND"
    print(f"[gsc-weekly] Email mode: {mode}", file=sys.stderr)
    send_report(report, dry_run=dry_run, env=env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
