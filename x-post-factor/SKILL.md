---
name: x-post-facto
description: Minimal, posting-only integration with X/Twitter v2 API using pure Python stdlib (zero dependencies). Can ONLY create new original tweets and self-threads. No reading, no replies, no likes, no engagement of any kind.
version: 1.0.0
user-invocable: true
metadata:
  openclaw:
    requires:
      env: ["TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET"]
    primaryEnv: "TWITTER_API_KEY"
---

# Custom X Poster — Pure Python (Posting-Only)

**STRICT RULES — THE AGENT MUST FOLLOW THESE 100% OF THE TIME:**
- You may ONLY create and publish original standalone tweets or self-threads.
- You are forbidden from reading timelines, checking mentions, searching, replying, quoting, liking, retweeting, following, or any form of engagement.
- If asked to interact with existing content, reply with: "I can only create original posts. I do not read or engage with existing content."
- Always respect X's 280-character limit per tweet.
- Use only the pure Python helper script for posting.

## Authentication
Uses your environment variables (set these once):
- `TWITTER_API_KEY`
- `TWITTER_API_SECRET`
- `TWITTER_ACCESS_TOKEN`
- `TWITTER_ACCESS_SECRET`

## How to Post (Agent runs this)
```bash
python3 ~/.openclaw/skills/x-post-facto/x_poster.py "Your tweet text here"
