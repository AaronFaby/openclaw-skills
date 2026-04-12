# xAI CLI Command Reference

## Global Flag

| Flag | Values | Default | Description |
|---|---|---|---|
| `--format` | `raw` \| `pretty` | `pretty` | Output format |

## Commands

### `models`
List available model IDs from `/v1/models`.

```bash
python scripts/xai.py models
```

### `chat`
Single-turn text completion via `/v1/responses`.

```bash
python scripts/xai.py chat --prompt "Explain zero-knowledge proofs in 3 bullets"
python scripts/xai.py chat --model grok-4-1-fast-reasoning --prompt "Summarize this"
```

### `vision`
Image analysis with prompt (supports local file path or URL).

```bash
python scripts/xai.py vision --image ./image.png --prompt "Describe key objects"
python scripts/xai.py vision --image https://example.com/cat.jpg --prompt "What is in this image?"
```

### `search-x`
Run Grok with server-side `x_search` tool.

```bash
python scripts/xai.py search-x --query "latest xAI announcements" --days 3
python scripts/xai.py search-x --query "AI chips" --days 7 --handles elonmusk,karpathy
```

| Flag | Default | Description |
|---|---|---|
| `--query` | required | Search intent |
| `--days` | `7` | Date window from today backward |
| `--handles` | optional | Comma-separated allowlist (max 10) |

### `search-web`
Run Grok with server-side `web_search` tool.

```bash
python scripts/xai.py search-web --query "latest CUDA release notes"
```

### `stream`
Stream text deltas from `/v1/responses`.

```bash
python scripts/xai.py stream --prompt "Write a short cyberpunk haiku"
python scripts/xai.py stream --model grok-4-1-fast-reasoning --prompt "Live-think about TLS handshake"
```

## Notes

- Model auto-selection prefers latest Grok-4+ family returned by `/v1/models`.
- Pass `--model` to pin a specific model ID.
- `raw` format returns full API payloads for debugging.
