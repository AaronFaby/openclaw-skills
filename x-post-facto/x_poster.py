#!/usr/bin/env python3
"""
x_poster.py v2.0 — Bulletproof X/Twitter posting for subagentic.ai

MODES:
  Post tweets (stdin):
    printf "tweet text" | python3 x_poster.py
    printf "tweet1\n---\ntweet2" | python3 x_poster.py

  Delete all tweets:
    python3 x_poster.py --delete-all

SAFETY:
  - STDIN ONLY for tweet text (no shell args except --delete-all)
  - Rejects tweets shorter than 10 characters (shell bug protection)
  - Rejects more than 10 tweets in a single invocation (spam protection)
  - Rejects input that looks like character-per-line iteration
  - Truncates tweets over 280 chars with "..."
  - Pure Python stdlib — zero external dependencies

CREDENTIALS (env vars — load with `source ~/.openclaw/.env`):
  TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
"""
import sys
import os
import json
import time
import uuid
import hmac
import hashlib
import urllib.parse
import urllib.request
import base64

# ============================================================
# Constants
# ============================================================
TWEET_MAX_CHARS = 280
TWEET_MIN_CHARS = 10       # Reject tweets shorter than this
MAX_TWEETS_PER_CALL = 10   # Reject batches larger than this
TWEET_DELIMITER = "\n---\n" # Separator between tweets in stdin
API_BASE = "https://api.twitter.com/2"

# ============================================================
# OAuth 1.0a helpers (pure stdlib)
# ============================================================

def percent_encode(s):
    """RFC 5849 percent-encoding."""
    return urllib.parse.quote(str(s), safe='~')


def create_oauth_signature(method, url, params, consumer_secret, token_secret):
    """Create HMAC-SHA1 OAuth signature."""
    sorted_params = '&'.join(
        sorted(f"{percent_encode(k)}={percent_encode(v)}" for k, v in params.items())
    )
    base_string = f"{method.upper()}&{percent_encode(url)}&{percent_encode(sorted_params)}"
    signing_key = f"{percent_encode(consumer_secret)}&{percent_encode(token_secret)}"
    sig = hmac.new(
        signing_key.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha1
    ).digest()
    return base64.b64encode(sig).decode('utf-8')


def get_credentials():
    """Load and validate Twitter API credentials from environment."""
    creds = {
        'consumer_key':    os.getenv('TWITTER_API_KEY', ''),
        'consumer_secret': os.getenv('TWITTER_API_SECRET', ''),
        'access_token':    os.getenv('TWITTER_ACCESS_TOKEN', ''),
        'access_secret':   os.getenv('TWITTER_ACCESS_SECRET', ''),
    }
    missing = [k for k, v in creds.items() if not v]
    if missing:
        die(f"Missing environment variables: {', '.join(missing)}\n"
            "Load with: source ~/.openclaw/.env")
    return creds


def build_auth_header(method, url, query_params, creds):
    """Build OAuth Authorization header for a request."""
    oauth_params = {
        "oauth_consumer_key": creds['consumer_key'],
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": creds['access_token'],
        "oauth_version": "1.0"
    }
    # Include query params in signature base (but NOT JSON body)
    all_params = {**oauth_params, **query_params}
    oauth_params["oauth_signature"] = create_oauth_signature(
        method, url, all_params, creds['consumer_secret'], creds['access_secret']
    )
    return "OAuth " + ', '.join(
        f'{k}="{percent_encode(v)}"' for k, v in sorted(oauth_params.items())
    )


# ============================================================
# API request helpers
# ============================================================

def api_request(method, endpoint, creds, query_params=None, json_body=None):
    """
    Make an authenticated Twitter API v2 request.
    Returns parsed JSON response or raises on error.
    """
    query_params = query_params or {}
    url = f"{API_BASE}/{endpoint.lstrip('/')}"
    auth = build_auth_header(method, url, query_params, creds)

    full_url = url
    if query_params:
        full_url += '?' + urllib.parse.urlencode(query_params)

    data = json.dumps(json_body).encode('utf-8') if json_body else None
    headers = {"Authorization": auth}
    if json_body:
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(full_url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"HTTP {e.code}: {body}")


# ============================================================
# Core functions
# ============================================================

def die(msg):
    """Print error and exit."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def get_user_id(creds):
    """Get the authenticated user's ID."""
    result = api_request("GET", "/users/me", creds)
    return result['data']['id'], result['data'].get('username', 'unknown')


def post_tweets(texts, creds):
    """Post one or more tweets as a thread. Returns list of tweet IDs."""
    url_endpoint = "/tweets"
    last_tweet_id = None
    posted_ids = []

    for i, text in enumerate(texts):
        payload = {"text": text}
        if last_tweet_id:
            payload["reply"] = {"in_reply_to_tweet_id": last_tweet_id}

        try:
            result = api_request("POST", url_endpoint, creds, json_body=payload)
            last_tweet_id = result['data']['id']
            posted_ids.append(last_tweet_id)
            print(f"✓ Posted tweet {i+1}/{len(texts)}: ID {last_tweet_id}")
        except RuntimeError as e:
            die(f"Failed to post tweet {i+1}/{len(texts)}: {e}")

        if i < len(texts) - 1:
            time.sleep(1)  # Rate limit courtesy

    return posted_ids


def delete_all_tweets(creds):
    """Fetch all tweets for the authenticated user and delete them."""
    user_id, username = get_user_id(creds)
    print(f"Authenticated as @{username} (ID: {user_id})")

    # Fetch all tweet IDs
    all_ids = []
    pagination_token = None
    page = 0

    while True:
        page += 1
        params = {"max_results": "100"}
        if pagination_token:
            params["pagination_token"] = pagination_token

        try:
            data = api_request("GET", f"/users/{user_id}/tweets", creds, query_params=params)
        except RuntimeError as e:
            print(f"Error fetching page {page}: {e}")
            break

        tweets = data.get('data', [])
        if not tweets:
            break

        for t in tweets:
            all_ids.append(t['id'])
            preview = t.get('text', '')[:50].replace('\n', ' ')
            print(f"  Found: {t['id']} — {preview}")

        pagination_token = data.get('meta', {}).get('next_token')
        if not pagination_token:
            break
        time.sleep(1)

    print(f"\nTotal tweets found: {len(all_ids)}")
    if not all_ids:
        print("Nothing to delete.")
        return 0

    # Delete each tweet
    deleted = 0
    for tid in all_ids:
        try:
            result = api_request("DELETE", f"/tweets/{tid}", creds)
            if result.get('data', {}).get('deleted'):
                deleted += 1
                print(f"  ✓ Deleted {tid} ({deleted}/{len(all_ids)})")
            else:
                print(f"  ✗ Delete returned unexpected result for {tid}: {result}")
        except RuntimeError as e:
            print(f"  ✗ Error deleting {tid}: {e}")
        time.sleep(0.5)

    print(f"\nDone. Deleted: {deleted}/{len(all_ids)}")
    return deleted


# ============================================================
# Input validation
# ============================================================

def validate_tweets(texts):
    """
    Validate tweet texts. Dies on any violation.
    This is the core safety layer that prevents misuse.
    """
    if not texts:
        die("No tweet text provided on stdin.")

    if len(texts) > MAX_TWEETS_PER_CALL:
        die(f"Too many tweets ({len(texts)}). Max {MAX_TWEETS_PER_CALL} per call. "
            "This limit prevents spam from iteration bugs.")

    for i, text in enumerate(texts):
        # Short tweet guard — catches character-by-character iteration bugs
        if len(text) < TWEET_MIN_CHARS:
            die(f"Tweet {i+1} is only {len(text)} chars: '{text}'\n"
                f"Minimum is {TWEET_MIN_CHARS} chars. "
                "This usually means a shell escaping or iteration bug.")

    # Heuristic: if ALL tweets are very short (< 20 chars), it's likely iteration
    if len(texts) > 2 and all(len(t) < 20 for t in texts):
        die(f"All {len(texts)} tweets are under 20 chars. "
            "This looks like character/word iteration. Aborting.")

    # Apply truncation for over-length tweets
    result = []
    for text in texts:
        if len(text) > TWEET_MAX_CHARS:
            text = text[:TWEET_MAX_CHARS - 3] + "..."
            print(f"Warning: Tweet truncated to {TWEET_MAX_CHARS} chars.")
        result.append(text)

    return result


# ============================================================
# Main entry point
# ============================================================

def main():
    # --delete-all mode: the ONLY allowed shell argument
    if len(sys.argv) == 2 and sys.argv[1] == '--delete-all':
        creds = get_credentials()
        delete_all_tweets(creds)
        return

    # Reject ALL other shell arguments
    if len(sys.argv) > 1:
        die("Shell arguments not accepted (tweet text must come from stdin).\n"
            "\n"
            "Usage:\n"
            "  Post:   printf 'tweet text' | python3 x_poster.py\n"
            "  Thread: printf 'tweet1\\n---\\ntweet2' | python3 x_poster.py\n"
            "  Delete: python3 x_poster.py --delete-all\n"
            "\n"
            "Shell args cause escaping bugs with emoji/bullets. STDIN ONLY.")

    # Read from stdin
    if sys.stdin.isatty():
        die("No input on stdin (and stdin is a TTY).\n"
            "Usage: printf 'tweet text' | python3 x_poster.py")

    raw_input = sys.stdin.read().strip()
    if not raw_input:
        die("Empty stdin. Provide tweet text.\n"
            "Usage: printf 'tweet text' | python3 x_poster.py")

    # Split on delimiter
    tweets = [t.strip() for t in raw_input.split(TWEET_DELIMITER) if t.strip()]

    # Validate (this is the bulletproof safety layer)
    tweets = validate_tweets(tweets)

    # Post
    creds = get_credentials()
    ids = post_tweets(tweets, creds)
    print(f"\n✓ All {len(ids)} tweet(s) posted successfully!")
    print(f"  IDs: {', '.join(ids)}")


if __name__ == "__main__":
    main()
