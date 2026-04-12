---
name: discrawl
description: Search and inspect Discord server history locally with discrawl. Use this whenever the user wants to search Discord messages, find old conversations, inspect a guild or thread archive, look up what someone said, search mentions, browse archived members, or query Discord history from local SQLite instead of relying on native Discord search. Also use it when the user explicitly mentions discrawl, local Discord archives, syncing Discord history, or wants information from Discord that native search misses.
compatibility:
  tools: Read, Edit, Bash
  dependencies: discrawl, Discord bot token or OpenClaw Discord config
---

# Discrawl

Use this skill to search and inspect archived Discord history through the locally installed `discrawl` CLI.

## What this skill is for

Run this skill when the user wants to:

- search Discord history locally
- find discussions by keyword, author, channel, or time range
- inspect what a specific person said
- search structured user or role mentions
- browse archived member profiles
- query the local SQLite archive directly
- initialize or refresh a local Discord archive before searching

This skill is for **finding information**, not sending messages. If the user wants to message Discord, use the Discord message tooling instead.

## Command location

Prefer the bundled helper script for common search tasks:

```bash
python ~/.openclaw/skills/discrawl/scripts/discrawl_query.py search "OpenClaw"
```

It normalizes discrawl output into predictable JSON.

When you need raw CLI access, prefer `discrawl` from `PATH`.

If it is not on `PATH`, use the installed binary directly:

```bash
/home/linuxbrew/.linuxbrew/bin/discrawl
```

## Safe operating model

`discrawl` is a bot-token crawler that mirrors Discord data into local SQLite.

Important consequences:

- searches are local after sync
- `init`, `sync`, and `tail` modify the local archive, not Discord content
- do not use user tokens
- never expose bot tokens or raw secret values in chat output
- prefer `doctor` before first use or after auth/config changes

## Default workflow

1. Confirm the CLI is available.
2. Run `discrawl doctor` to verify config, token resolution, auth, DB, and FTS wiring.
3. If this is first-time setup, initialize with either:
   - `discrawl init --from-openclaw ~/.openclaw/openclaw.json`
   - or env-based setup with `DISCORD_BOT_TOKEN`
4. If the archive is missing or stale, run `discrawl sync --full`.
5. Prefer the helper script for supported workflows so output is normalized JSON.
6. Use the narrowest search command that matches the user's question.
7. Return a concise answer with quoted hits, channel context, and timestamps when useful.

## Search workflow selection

Choose commands like this:

- broad keyword/topic lookup → `search`
- exact message slices by channel/author/time → `messages`
- user or role mention discovery → `mentions`
- person/profile lookup → `members search` / `members show`
- guild/channel inventory → `channels list` / `channels show`
- health or coverage check → `status` / `doctor`
- advanced ad hoc analysis → `sql`

## Preferred helper-script patterns

### Health check

```bash
python ~/.openclaw/skills/discrawl/scripts/discrawl_query.py doctor
python ~/.openclaw/skills/discrawl/scripts/discrawl_query.py status
```

### Normalized keyword search

```bash
python ~/.openclaw/skills/discrawl/scripts/discrawl_query.py search --channel cron "allowlist"
```

### Normalized message slice

```bash
python ~/.openclaw/skills/discrawl/scripts/discrawl_query.py messages --channel cron --days 7 --limit 20
```

### Normalized mention lookup

```bash
python ~/.openclaw/skills/discrawl/scripts/discrawl_query.py mentions --target Asynchronous --type user --limit 10
```

### Normalized member lookup

```bash
python ~/.openclaw/skills/discrawl/scripts/discrawl_query.py member-search "Asynchronous"
python ~/.openclaw/skills/discrawl/scripts/discrawl_query.py member-show --messages 5 asynchronous0805
```

Use raw `discrawl` commands when the helper script does not cover the needed operation yet.

## Core command patterns

### Quick sanity check

```bash
discrawl doctor
```

### First-time setup from OpenClaw

```bash
discrawl init --from-openclaw ~/.openclaw/openclaw.json
```

### Full archive refresh

```bash
discrawl sync --full
```

### Keyword search

```bash
discrawl search "panic: nil pointer"
discrawl search --channel billing --author steipete --limit 50 "invoice"
discrawl --json search "websocket closed"
```

### Time-bounded message lookup

```bash
discrawl messages --channel maintainers --days 7 --all
discrawl messages --channel maintainers --author steipete --limit 50
discrawl messages --channel maintainers --last 100 --sync
```

### Mentions lookup

```bash
discrawl mentions --target steipete --type user --limit 50
discrawl mentions --channel maintainers --days 7
```

### Member lookup

```bash
discrawl members search "design engineer"
discrawl members show --messages 10 steipete
```

### Read-only SQL

```bash
discrawl sql 'select count(*) as messages from messages'
```

## How to answer the user well

When reporting findings:

- lead with the answer, not the raw command dump
- include channel/thread name when relevant
- include timestamps for important hits
- quote the most relevant snippets
- mention if results depend on archive freshness
- say when you had to run `sync` first

If the archive is stale or missing, say so plainly and fix that before claiming no results.

## Guardrails

- Do not invent unsupported discrawl subcommands or flags.
- Do not assume the archive is current unless you checked `status`, ran `sync`, or the user said it is current.
- Prefer targeted search scope before falling back to broad SQL.
- Use `--json` when structured output will make parsing or summarization cleaner.
- If auth fails, troubleshoot with `doctor` before retry-spamming sync/tail.
- If the user wants a live-updating mirror, use `tail`; otherwise prefer one-shot `sync` plus search.

## References

Read these when needed:

- `references/command-recipes.md` for search recipes, setup paths, troubleshooting, and helper-script examples

## Output contract

Default answer shape:

- one-line answer
- 2-5 key findings as bullets
- exact follow-up command to refine the search, if helpful

If the user asks for raw output, JSON, or SQL results, provide that instead.
