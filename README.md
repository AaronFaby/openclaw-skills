# openclaw-skills

A collection of custom skills for [OpenClaw](https://github.com/AaronFaby/openclaw), self-hosted here instead of Clawhub.

---

## Skills

### xAI / Grok

| Skill | Description |
|---|---|
| [`grok-imagine`](grok-imagine/) | Generate images using xAI's Grok Imagine model. Triggers on "imagine", "draw", "generate image", etc. Requires `XAI_API_KEY`. |
| [`grok-imagine-video`](grok-imagine-video/) | Generate short videos with native audio using xAI's Grok Imagine Video. Triggers on "generate video", "animate", "make a video of", etc. Requires `XAI_API_KEY`. |
| [`grok-x-search`](grok-x-search/) | Search X/Twitter via xAI Grok's native `x_search` tool. Returns a synthesized answer with citation URLs. Requires `XAI_API_KEY`. |
| [`xai`](xai/) | General-purpose xAI/Grok inference skill for chat, streaming, vision, web search, and X search via local Python CLI. |

### X / Twitter

| Skill | Description |
|---|---|
| [`x-post-facto`](x-post-facto/) | Post original tweets and self-threads to X using the v2 API (posting-only — no reading or engagement). Requires OAuth keys. |

### Google

| Skill | Description |
|---|---|
| [`google-search-console`](google-search-console/) | Query Google Search Console for search performance data (queries, pages, clicks, impressions, CTR, position), sitemaps, and URL indexing status. |
| [`google-developer-style`](google-developer-style/) | Apply the Google Developer Documentation Style Guide when writing or reviewing any developer-facing content. |

### Cloudflare

| Skill | Description |
|---|---|
| [`Cloudflare-analytics`](Cloudflare-analytics/) | Pull zone analytics (requests, visitors, bandwidth, cache, TLS, threats) via the Cloudflare GraphQL API. Requires `CLOUDFLARE_API_KEY` and `CLOUDFLARE_ZONE_ID`. |

### Gmail

| Skill | Description |
|---|---|
| [`gmail-imap-ops`](gmail-imap-ops/) | Read and search Gmail via IMAP and send mail via SMTP using a local app-password credential. Defaults to dry-run for outbound sends. |

### Discord

| Skill | Description |
|---|---|
| [`discrawl`](discrawl/) | Search and inspect archived Discord server history locally via the `discrawl` CLI and a SQLite archive. Use for keyword search, mention lookup, member lookup, and channel browsing without relying on native Discord search. |

### Writing

| Skill | Description |
|---|---|
| [`replicant`](replicant/) | Identify and remove common AI writing tells. Rewrites text to sound specific, natural, and human without changing the core meaning. |

---

## Installation

Skills live in `~/.openclaw/skills/`. Clone or copy a skill folder there:

```bash
git clone https://github.com/AaronFaby/openclaw-skills ~/.openclaw/skills-repo
```

Then symlink or copy individual skill folders into `~/.openclaw/skills/`:

```bash
ln -s ~/.openclaw/skills-repo/grok-imagine ~/.openclaw/skills/grok-imagine
```

Each skill's `SKILL.md` describes its configuration, required environment variables, and usage.

---

## Credentials

Most skills load secrets from `~/.openclaw/.env` or `~/.openclaw/workspace/.secrets/<service>.env`. No credentials are stored in this repo.

| Skill | Required credentials |
|---|---|
| `grok-imagine`, `grok-imagine-video`, `grok-x-search`, `xai` | `XAI_API_KEY` |
| `x-post-facto` | `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET` |
| `Cloudflare-analytics` | `CLOUDFLARE_API_KEY`, `CLOUDFLARE_ZONE_ID` |
| `gmail-imap-ops` | `GMAIL_USER`, `GMAIL_PASSWORD` (app password) |
| `google-search-console` | OAuth client JSON + token cache (desktop OAuth flow) |
| `discrawl` | Discord bot token (`DISCORD_BOT_TOKEN` or OpenClaw config) |
