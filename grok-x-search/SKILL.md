---
name: grok-x-search
description: "Search X/Twitter using xAI Grok's native x_search tool via the xAI Python SDK. Use when you need real-time tweets, X posts, threads, or discussions with citations."
triggers: ["grok x", "search x", "search twitter", "find tweets", "x search", "twitter search", "x_search", "xai sdk"]
metadata: {"clawdbot":{"emoji":"🐦","requires":{"env":["XAI_API_KEY"]},"primaryEnv":"XAI_API_KEY"}}
---

Search X/Twitter using xAI Grok's native `x_search` tool via the xai-sdk Python SDK. Returns Grok's synthesized answer plus citation URLs to the original tweets/posts.

## API Key

The script loads `XAI_API_KEY` automatically from `~/.openclaw/.env`. You can also set it as an environment variable.

## Python / Venv

This skill uses a dedicated Python venv. Always invoke with the venv python:

```
{baseDir}/venv/bin/python {baseDir}/scripts/x_search.py ...
```

## Run

### Basic X search (JSON output)

```bash
{baseDir}/venv/bin/python {baseDir}/scripts/x_search.py "query here"
```

### Plain text output

```bash
{baseDir}/venv/bin/python {baseDir}/scripts/x_search.py "query here" --text
```

### With date filters

```bash
# Last 7 days
{baseDir}/venv/bin/python {baseDir}/scripts/x_search.py "AI news" --days 7

# Specific date range
{baseDir}/venv/bin/python {baseDir}/scripts/x_search.py "AI news" --from 2026-01-01 --to 2026-02-24
```

### Filter by handles

```bash
# Only these accounts
{baseDir}/venv/bin/python {baseDir}/scripts/x_search.py "product launch" --handles @elonmusk,@xai

# Exclude accounts
{baseDir}/venv/bin/python {baseDir}/scripts/x_search.py "AI drama" --exclude-handles @bots,@spam
```

### Image/video understanding

```bash
{baseDir}/venv/bin/python {baseDir}/scripts/x_search.py "funny memes" --images --videos
```

### Debug raw response

```bash
{baseDir}/venv/bin/python {baseDir}/scripts/x_search.py "query" --raw
```

Raw API response object is dumped to stderr.

## CLI Flags

| Flag | Description |
|---|---|
| `"query"` | **(positional, required)** Search query |
| `--model <id>` | Model ID (default: `grok-4-1-fast`) |
| `--handles @a,@b` | Only search these X handles (comma-separated) |
| `--exclude-handles @a,@b` | Exclude these X handles (comma-separated) |
| `--from YYYY-MM-DD` | Start date filter |
| `--to YYYY-MM-DD` | End date filter |
| `--days <n>` | Shorthand: `--from` = today minus N days |
| `--images` | Enable image understanding |
| `--videos` | Enable video understanding |
| `--raw` | Dump raw response object to stderr |
| `--text` | Output plain text instead of JSON |

## Output Shape (JSON, default)

```json
{
  "query": "...",
  "response": "Grok's full text answer synthesizing tweets",
  "citations": ["https://x.com/user/status/123", "..."]
}
```

With `--text`, only Grok's text response is printed to stdout (no JSON wrapper).

## Notes

- Uses `xai-sdk` 1.7.0 Python SDK directly (not OpenAI SDK, not Node.js)
- `x_search` is a server-side Grok tool — Grok searches X internally and synthesizes an answer
- Citations are extracted from the final response object
- Handle `@` prefixes are stripped automatically
- `--days N` sets `from_date` to N days ago (UTC); ignored if `--from` is also set
