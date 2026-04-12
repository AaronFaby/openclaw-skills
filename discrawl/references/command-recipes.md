# Discrawl Command Recipes

Use these recipes to search Discord history locally without making up flags like a gonk.

## Binary path

Prefer:

```bash
discrawl
```

Fallback if `PATH` is missing it:

```bash
/home/linuxbrew/.linuxbrew/bin/discrawl
```

## Helper script

For the common cases, prefer the bundled wrapper:

```bash
python ~/.openclaw/skills/discrawl/scripts/discrawl_query.py search "OpenClaw"
```

It normalizes output into predictable JSON for:
- `doctor`
- `status`
- `search`
- `messages`
- `mentions`
- `members-list`
- `member-search`
- `member-show`

Examples:

```bash
python ~/.openclaw/skills/discrawl/scripts/discrawl_query.py doctor
python ~/.openclaw/skills/discrawl/scripts/discrawl_query.py status
python ~/.openclaw/skills/discrawl/scripts/discrawl_query.py search --channel cron "allowlist"
python ~/.openclaw/skills/discrawl/scripts/discrawl_query.py messages --channel cron --days 7 --limit 20
python ~/.openclaw/skills/discrawl/scripts/discrawl_query.py mentions --target Asynchronous --type user --limit 10
python ~/.openclaw/skills/discrawl/scripts/discrawl_query.py member-show --messages 5 asynchronous0805
```

Use raw `discrawl` below when you need coverage outside the helper's current surface.

## Setup and health

### Reuse OpenClaw's Discord config

```bash
discrawl init --from-openclaw ~/.openclaw/openclaw.json
```

### Pick a specific OpenClaw account

```bash
discrawl init --from-openclaw ~/.openclaw/openclaw.json --account atlas
```

### Env-only setup

```bash
export DISCORD_BOT_TOKEN="..."
discrawl init
```

### Verify everything quickly

```bash
discrawl doctor
```

Use `doctor` when:
- first setting up
- auth fails
- sync behaves strangely
- you are unsure where the token is coming from

## Refreshing the archive

### Full sync

```bash
discrawl sync --full
```

### Sync every discovered guild

```bash
discrawl sync --full --all
```

### Sync a specific guild

```bash
discrawl sync --guild 123456789012345678
```

### Sync only some channels

```bash
discrawl sync --channels 111,222 --since 2026-03-01T00:00:00Z
```

Notes:
- `--since` limits the initial backfill window
- long syncs emit progress logs
- if the archive is already mostly complete, routine refreshes are cheaper than first backfill

## Search recipes

### Broad keyword search

```bash
discrawl search "panic: nil pointer"
discrawl search "payment failed"
```

### Narrow by guild/channel/author

```bash
discrawl search --guild 123456789012345678 "payment failed"
discrawl search --channel billing --author steipete --limit 50 "invoice"
```

### Include messages that have little or no body text

```bash
discrawl search --include-empty "GitHub"
```

### JSON output for machine-friendly parsing

```bash
discrawl --json search "websocket closed"
```

## Message slice recipes

Use `messages` when the user really means "show me what happened in channel X over time" instead of fuzzy keyword search.

```bash
discrawl messages --channel maintainers --days 7 --all
discrawl messages --channel maintainers --hours 6 --all
discrawl messages --channel "#maintainers" --since 2026-03-01T00:00:00Z
discrawl messages --channel 1456744319972282449 --author steipete --limit 50
discrawl messages --channel maintainers --last 100 --sync
```

Notes:
- `--channel` accepts id, exact name, `#name`, or partial match
- at least one filter is required
- `--sync` is useful when the user wants the freshest possible read before querying

## Mention recipes

Use `mentions` when the user cares about who tagged whom or which role got pinged.

```bash
discrawl mentions --channel maintainers --days 7
discrawl mentions --target steipete --type user --limit 50
discrawl mentions --target 1456406468898197625
discrawl --json mentions --type role --days 1
```

## Member recipes

Use member search when the user is trying to identify people, bios, handles, URLs, or recent activity.

```bash
discrawl members list
discrawl members search "peter"
discrawl members search "github"
discrawl members search "design engineer"
discrawl members show steipete
discrawl members show --messages 25 steipete
```

Useful facts:
- member search can match archived profile fields like bio, website, GitHub, or X handles
- `members show` can include recent message context
- this is archive-based, not magic; if Discord never exposed the field, discrawl will not invent it

## Channel and status recipes

```bash
discrawl channels list
discrawl channels show 123456789012345678
discrawl status
discrawl tail
discrawl tail --repair-every 30m
```

Use `tail` only when the user wants a live-updating archive. For one-shot research, `sync` plus search is usually cleaner.

## SQL recipes

Use SQL when the user wants counts, grouping, or a custom query the built-in commands do not cover.

```bash
discrawl sql 'select count(*) as messages from messages'
discrawl sql 'select guild_id, count(*) as messages from messages group by guild_id order by messages desc'
discrawl sql 'select author_username, count(*) as c from messages group by author_username order by c desc limit 20'
```

Keep SQL read-only.

## Troubleshooting

### "discord token not found in env or openclaw config"
- set `DISCORD_BOT_TOKEN`, or
- initialize from `~/.openclaw/openclaw.json`, or
- check `discrawl doctor`

### Search returns nothing
- archive may be stale or empty
- run `discrawl sync --full`
- confirm correct guild/channel scope
- try broader terms before assuming the discussion never happened

### Help output is odd or terse
Some discrawl commands return terse help/error text. Prefer the known-good command recipes above and only improvise when the upstream docs clearly support it.

## Recommended response style

When summarizing results for the user:
- answer first
- include the best 1-3 supporting hits
- note channel, author, and timestamp where useful
- mention archive freshness if relevant
- suggest the next narrowing command if the result set is noisy
