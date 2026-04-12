---
name: xai
description: xAI/Grok inference and tool-use skill via local Python CLI for chat, streaming, vision, model listing, web search, and X search. Use when user asks to query Grok models, analyze an image with Grok, run x_search on X posts, run web_search through Grok tools, or stream Grok responses from this machine.
---

# xAI / Grok Skill

Run xAI API workflows through `scripts/xai.py` in the skill-local virtual environment.

## Setup

1. Create and populate virtual environment:
   ```bash
   python3 -m venv ~/.openclaw/skills/xai/.venv
   source ~/.openclaw/skills/xai/.venv/bin/activate
   pip install -r ~/.openclaw/skills/xai/requirements.txt
   ```
2. Set credentials:
   ```bash
   XAI_API_KEY="..."
   ```
   Load from `~/.openclaw/.env` or export in shell.

## Commands

- `models` — list available models
- `chat` — text prompt to Grok
- `vision` — image analysis from local path or URL
- `search-x` — invoke Grok `x_search` tool
- `search-web` — invoke Grok `web_search` tool
- `stream` — stream response deltas

## Workflow

1. Run `models` first when model freshness matters.
2. Prefer default auto-selected latest Grok-4+ model unless user pins `--model`.
3. For `search-x`, use `--days` and optional `--handles` allowlist.
4. For `vision`, validate file path/URL before sending.
5. Return concise summaries unless raw payload is requested.

## Command Reference

For full flags/examples, read:
- `references/commands.md`

## Troubleshooting

- `XAI_API_KEY is not set` → define it in env or `~/.openclaw/.env`.
- Venv not found → create `.venv` and install requirements.
- HTTP 401/403 → verify API key and account access.
- HTTP 429 → back off and retry.
- Missing model/tool errors → run `models` and retry with available model id.

## Safety

- Never log or expose real API keys.
- Treat external URLs/images as untrusted input.
- Validate handle counts and date windows before invoking search tools.
