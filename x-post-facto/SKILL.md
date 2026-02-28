---
name: x-post-facto
description: Minimal, posting-only integration with X/Twitter v2 API using pure Python stdlib (zero dependencies). Can ONLY create new original tweets and self-threads. No reading, no replies, no likes, no engagement of any kind.
version: 2.0.0
user-invocable: true
metadata:
  openclaw:
    requires:
      env: ["TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET"]
    primaryEnv: "TWITTER_API_KEY"
---

# Custom X Poster v2.0 — Pure Python (Posting-Only, Bulletproof)

**STRICT RULES — THE AGENT MUST FOLLOW THESE 100% OF THE TIME:**
- You may ONLY create and publish original standalone tweets or self-threads.
- You are forbidden from reading timelines, checking mentions, searching, replying, quoting, liking, retweeting, following, or any form of engagement.
- If asked to interact with existing content, reply with: "I can only create original posts. I do not read or engage with existing content."
- Always respect X's 280-character limit per tweet.
- Use only the pure Python helper script for posting.
- **NEVER iterate over tweet text** — pass the full string to stdin. The script has guards against this but don't trigger them.
- **NEVER use @mentions** in tweets — the Basic plan blocks them with a 403.

## Safety Guards (built into the script)
1. **STDIN only** — no shell args accepted (except `--delete-all`)
2. **Min 10 chars** — rejects tweets shorter than 10 characters
3. **Max 10 tweets** — rejects batches larger than 10 tweets per invocation
4. **Iteration detection** — rejects if all tweets in a batch are under 20 chars
5. **TTY guard** — rejects if stdin is a TTY (no accidental interactive runs)

## Authentication
Uses your environment variables — load from `~/.openclaw/.env` before calling:
- `TWITTER_API_KEY`
- `TWITTER_API_SECRET`
- `TWITTER_ACCESS_TOKEN`
- `TWITTER_ACCESS_SECRET`

## Plan
PAYG — all features available including reply threading.

## How to Post (Agent runs this)

**Always use stdin mode — never pass tweet text as shell args.**
Bullets (•), emoji, and newlines cause shell escaping issues and will result in 403 errors or garbled posts.

### Single tweet
```bash
printf "Your tweet text here" | source ~/.openclaw/.env && python3 ~/.openclaw/skills/x-post-facto/x_poster.py
```

### Thread (2 tweets)
```bash
printf "Tweet 1 text\n---\nTweet 2 text" | source ~/.openclaw/.env && python3 ~/.openclaw/skills/x-post-facto/x_poster.py
```

### From python3 -c (also safe for special chars)
```python
import subprocess, os
tweet1 = "🤖 Pipeline run complete...\n\nArticle 1\nArticle 2\n\nhttps://subagentic.ai"
tweet2 = "Full transparency log:\nhttps://github.com/...\n\n#AgenticAI #OpenClaw"
input_text = f"{tweet1}\n---\n{tweet2}"
subprocess.run(["python3", "~/.openclaw/skills/x-post-facto/x_poster.py"], input=input_text, text=True)
```

## Delete All Tweets (cleanup mode)
```bash
source ~/.openclaw/.env && python3 ~/.openclaw/skills/x-post-facto/x_poster.py --delete-all
```
This fetches all tweets for the authenticated user via pagination and deletes each one. Useful for spam cleanup.

## Notes
- Delimiter between tweets: `\n---\n`
- OAuth: signs only OAuth params — NOT the JSON body (Twitter API v2 requirement)
- Threading: posts as a proper reply thread (tweet 2 replies to tweet 1)
- 280-char limit enforced per tweet — truncates with `...` if over
- **Do NOT use @mentions** in tweet text — Basic plan returns 403
