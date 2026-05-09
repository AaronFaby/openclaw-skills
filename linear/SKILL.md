---
name: linear
description: Full-control Linear (linear.app) operations for issue/project tracking, backlog grooming, roadmaps, TODO capture, comments, priorities, and project/issue lookup. Use this whenever the user asks about Linear, tickets, issues, projects, roadmaps, cycles, backlog, product work, code backlog, creating/updating/commenting on Linear issues, syncing TODOs into Linear, or tracking work. Prefer canned CLI commands over hand-written GraphQL for common operations; raw GraphQL remains available for advanced cases.
---

# Linear full-control skill

Use this skill for Linear issue/project operations. Linear is the system of record for projects, product work, code backlog, and issues. The user has authorized Linear access through `LINEAR_API_KEY`, but keep the grid clean: never expose secrets, never read secret files into context, and never print authorization headers.

## Security model

- Use the local wrapper only:
  - `/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py`
  - or `linear-graphql` if it is on PATH.
- The wrapper reads `LINEAR_API_KEY` from environment or `/home/netwatch/.openclaw/secrets/linear-api-key` and never prints it.
- Never run `env`, `printenv LINEAR_API_KEY`, `set`, shell tracing (`set -x`), verbose curl, or anything that can leak headers/tokens.
- Never ask the user to paste the key in chat.
- Write operations are audited to `~/.openclaw/logs/linear-actions.jsonl` by the wrapper.

## Authority and guardrails

Normal operational writes are allowed when requested:

- create issues/projects
- idempotently create projects or issues when a clear key is available
- update issue priority by label (`none`, `urgent`, `high`, `medium`, `low`)
- add comments with source context
- list/search/lookup issues, teams, projects
- move work into Linear from chat/repo TODOs when asked

Ask for explicit Aaron approval before high-blast-radius actions:

- deleting or archiving issues/projects
- bulk edits affecting more than 5 issues
- workspace/team/project settings changes
- destructive label/status/project restructuring
- operations involving secrets, customer data, or external publication

The wrapper enforces some of this:

- `issue-archive` and `project-archive` require `--confirm`
- `bulk-priority-set` requires `--confirm-bulk` for more than 5 issues

## Prefer canned commands

Use canned commands for common operations. Only hand-write GraphQL if the command does not cover the needed operation.

Common command help:

```bash
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py --help
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py issue-create --help
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py bulk-priority-set --help
```

### Read/lookup

Viewer smoke test:

```bash
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py --pretty viewer
```

Teams:

```bash
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py --pretty team-list --limit 20
```

Issues:

```bash
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py --pretty issue-list --limit 10
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py --pretty issue-list --team-key ENG --query-text "nightly backup"
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py --pretty issue-lookup --identifier ENG-123
```

Projects:

```bash
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py --pretty project-lookup --project-name "OpenClaw Hardening"
```

### Create project idempotently

Use `--if-missing` when the project name is intended to be unique. The wrapper returns the existing exact-name project instead of creating a duplicate.

```bash
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py --pretty project-create \
  --name "OpenClaw Hardening" \
  --description "Security and reliability hardening work." \
  --team-key ENG \
  --if-missing \
  --source "wyzz:discord-delegation"
```

### Create issue idempotently

Best idempotency key: existing Linear identifier via `--key-identifier`. If no identifier exists, use `--if-missing` only when title + team + project are a safe unique key.

```bash
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py --pretty issue-create \
  --team-key ENG \
  --title "Harden nightly backup wrapper" \
  --description "Make hot-repo rebase safe with manual stash/restore." \
  --project-name "OpenClaw Hardening" \
  --priority high \
  --if-missing \
  --source "wyzz:code-audit"
```

### Add comment

Comments append a small source footer by default. Use useful context like `wyzz:session:<short-id>` or `netwatch:delegation`; never include secrets.

```bash
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py --pretty comment-add \
  --identifier ENG-123 \
  --body "Implemented manual stash/rebase/restore and verified with hot-repo simulation." \
  --source "wyzz:verification"
```

### Set priority by label

Priority mapping:

- `none=0`
- `urgent=1`
- `high=2`
- `medium=3`
- `low=4`

```bash
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py --pretty priority-set \
  --identifier ENG-123 \
  --priority urgent \
  --source "wyzz:triage"
```

### Bulk priority update from JSON

Input may be a list or `{ "updates": [...] }`. Each item must include exactly one of `identifier` or `issueId`, plus a priority label/int.

```json
{
  "updates": [
    { "identifier": "ENG-123", "priority": "urgent" },
    { "identifier": "ENG-124", "priority": "high" }
  ]
}
```

```bash
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py --pretty bulk-priority-set \
  --input /tmp/linear-priorities.json \
  --source "wyzz:backlog-grooming"
```

If more than 5 issues are affected, get Aaron's approval first, then pass `--confirm-bulk`.

### Destructive archive commands

Archive commands require `--confirm`, but tool guardrails are not a substitute for approval. Ask Aaron first unless he already explicitly approved the destructive action. Linear's project archive API is exposed as `projectDelete`; the wrapper names it `project-archive` to make the intent clearer.

```bash
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py --pretty issue-archive --identifier ENG-123 --confirm
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py --pretty project-archive --project-name "Old Project" --confirm
```

## Raw GraphQL fallback

Use raw GraphQL for unsupported operations only.

Inline query:

```bash
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py --pretty raw \
  --query 'query Me { viewer { id name email } }'
```

Backward-compatible old style still works:

```bash
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py --pretty \
  --query 'query Me { viewer { id name email } }'
```

For complex mutations, write a temporary JSON payload outside tracked repos, then call `raw --file`.

## Common workflow

1. Discover team/project/issue IDs with `team-list`, `project-lookup`, `issue-list`, or `issue-lookup`.
2. Prefer canned create/update/comment commands.
3. For writes, include `--source` with non-secret context.
4. Inspect response for `success: true` and absence of `errors`.
5. Report the identifier/title/url and what changed.

## Gotchas

- Linear personal API keys use `Authorization: <LINEAR_API_KEY>`, not `Bearer`; the wrapper handles this.
- Do not leave meaningful TODOs only in chat, files, or memory. Create/groom/prioritize them in Linear.
- Do not print raw environment or secret file contents. The wrapper is designed to keep tokens out of context.
- Idempotent issue creation is only safe when a clear unique key exists; otherwise ask before creating duplicates.
- Bulk/destructive Linear edits can damage the source-of-truth backlog. Get Aaron approval before high-blast-radius changes.

## References

Read `references/graphql-basics.md` only when raw GraphQL is necessary or a canned command does not support the requested operation.

## Output style

Be concise. For successful writes, include:

- action performed
- issue/project identifier or name
- title/name
- URL
- important changed fields

If Linear returns errors, quote the error messages and stop. Do not pretend success.
