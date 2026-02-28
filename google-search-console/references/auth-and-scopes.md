# Google Search Console auth and scopes

## Required packages

Install locally (user environment, not bundled secrets):

```bash
pip install google-auth google-auth-oauthlib requests
```

## Environment variables

- `GSC_CLIENT_SECRET_FILE` (required for first login)
  - Path to OAuth client JSON (Desktop app type) from Google Cloud Console.
- `GSC_TOKEN_FILE` (optional)
  - Token cache path. Default: `~/.config/openclaw/google-search-console-token.json`.
- `GSC_SCOPES` (optional)
  - Comma-separated scopes. Default:
    - `https://www.googleapis.com/auth/webmasters.readonly`

## OAuth behavior

1. Script attempts to load token from `GSC_TOKEN_FILE`.
2. If token is expired and has refresh token, script refreshes automatically.
3. If token is missing/invalid, script uses local OAuth browser flow and saves token.

## Practical scope guidance

- Read-only reporting: `https://www.googleapis.com/auth/webmasters.readonly`
- Manage Search Console entities: `https://www.googleapis.com/auth/webmasters`

Keep least-privilege default unless write operations are explicitly needed.

## URL Inspection constraints

URL Inspection endpoint is outside Webmasters v3 base path and requires:

- Search Console URL Inspection API enabled in the Google Cloud project
- OAuth client from the same project used for token flow
- URL belonging to a verified Search Console property

If these are missing, calls typically fail with 403/404.
