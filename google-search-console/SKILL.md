---
name: google-search-console
description: Query Google Search Console (Webmasters v3) data from local CLI scripts. Use when asked to check GSC properties, search performance (queries/pages/clicks/impressions/CTR/position), sitemap status, and indexing diagnostics via URL Inspection.
---

# Google Search Console

Use this skill to pull operational SEO data from Google Search Console with local OAuth credentials.

## Use this workflow

1. Set local auth env vars (no secrets in repo):
   - `GSC_CLIENT_SECRET_FILE` → OAuth client JSON path (desktop app credential)
   - `GSC_TOKEN_FILE` → token cache path (optional; default is `~/.config/openclaw/google-search-console-token.json`)
   - `GSC_SCOPES` → optional comma-separated scopes
2. Run a command. If token is missing/expired, the script opens local OAuth flow and saves refreshed token.
3. Use `--json` for machine-readable output.
4. Use `--dry-run` to print request payloads without calling Google.

## Commands

Run from workspace root:

- `python3 skills/google-search-console/scripts/gsc_cli.py sites`
- `python3 skills/google-search-console/scripts/gsc_cli.py analytics --site-url "sc-domain:example.com" --start-date 2026-02-01 --end-date 2026-02-27 --dimensions query page --row-limit 50`
- `python3 skills/google-search-console/scripts/gsc_cli.py sitemaps --site-url "sc-domain:example.com"`
- `python3 skills/google-search-console/scripts/gsc_cli.py inspect --site-url "sc-domain:example.com" --inspection-url "https://example.com/some-page"`

## Aaron-focused examples

### 1) Coverage/indexing check for a problem URL

```bash
python3 skills/google-search-console/scripts/gsc_cli.py inspect \
  --site-url "sc-domain:macaddress.net" \
  --inspection-url "https://macaddress.net/blog/new-post" \
  --json
```

If inspection fails with 403/404, verify URL Inspection API is enabled in the same Google Cloud project used by the OAuth client and that the property is verified.

### 2) Top queries for last 28 days

```bash
python3 skills/google-search-console/scripts/gsc_cli.py analytics \
  --site-url "sc-domain:macaddress.net" \
  --start-date 2026-01-30 \
  --end-date 2026-02-27 \
  --dimensions query \
  --row-limit 100
```

### 3) Top pages by clicks

```bash
python3 skills/google-search-console/scripts/gsc_cli.py analytics \
  --site-url "sc-domain:macaddress.net" \
  --start-date 2026-02-01 \
  --end-date 2026-02-27 \
  --dimensions page \
  --row-limit 100
```

### 4) Date comparison workflow (manual two-call diff)

```bash
# period A
python3 skills/google-search-console/scripts/gsc_cli.py analytics \
  --site-url "sc-domain:macaddress.net" \
  --start-date 2026-01-01 --end-date 2026-01-31 \
  --dimensions query --row-limit 200 --json > /tmp/gsc-jan.json

# period B
python3 skills/google-search-console/scripts/gsc_cli.py analytics \
  --site-url "sc-domain:macaddress.net" \
  --start-date 2026-02-01 --end-date 2026-02-27 \
  --dimensions query --row-limit 200 --json > /tmp/gsc-feb.json
```

Then compare query click/impression deltas in downstream analysis.

## Weekly Report

**Script:** `skills/google-search-console/scripts/gsc_weekly_report.py`

Queries both `sc-domain:macaddress.net` and `sc-domain:subagentic.ai`, generates a formatted SEO report, and sends it via Gmail SMTP.

### Features
- **HTML email output:** Report is converted from markdown to HTML via `md_to_html()` and sent as a multipart HTML/plain-text email — renders properly in mail clients (no raw markdown in inbox).
- **AI-generated recommendations:** Uses `claude-haiku-4-5` to review actual data and write 3–5 actionable SEO recommendations. Falls back to hardcoded rule-based logic if the API call fails.
- **Auth handling:** Script force-resolves `GSC_CLIENT_SECRET_FILE` and `GSC_TOKEN_FILE` using `Path.home()` — shell `$HOME` env vars are intentionally ignored to prevent literal `$HOME` strings from breaking subprocess auth.
- **Gmail SMTP:** Delegates send to `skills/gmail-imap-ops/scripts/gmail_smtp_send.py` with the `--html` flag for multipart delivery.

### Usage

```bash
# Dry-run (default) — prints report, no email sent
python3 skills/google-search-console/scripts/gsc_weekly_report.py

# Send live email
python3 skills/google-search-console/scripts/gsc_weekly_report.py --send

# Report only — skip email entirely
python3 skills/google-search-console/scripts/gsc_weekly_report.py --report-only
```

### Launchd schedule
- **Plist:** `~/Library/LaunchAgents/com.openclaw.gsc-weekly-report.plist`
- **Schedule:** Mondays at 6:15 AM PT
- **First live send:** 2026-03-02 ✅

---

## Notes

- Use property identifiers exactly as Search Console expects (`sc-domain:example.com` or `https://example.com/`).
- URL Inspection uses a different API surface (`searchconsole.googleapis.com`) and can be unavailable if not enabled or not authorized.
- Start with read-only scope. Expand scope only if write operations are needed.
- `gsc_cli.py` supports `--non-interactive` flag: blocks the browser OAuth flow (safe for cron/headless runs) but still allows silent token refresh via `refresh_token` when a valid cached token exists.
- `gsc_cli.py` `_load_creds()` was fixed 2026-03-02 to refresh when token is `not valid OR expired` (previously only refreshed when both conditions hit simultaneously).

## References

- `references/auth-and-scopes.md`
- `references/endpoints-quick-reference.md`
