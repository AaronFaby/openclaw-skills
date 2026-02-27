#!/usr/bin/env python3
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

def percent_encode(s):
    return urllib.parse.quote(str(s), safe='~')

def create_oauth_signature(method, url, params, consumer_secret, token_secret):
    base_string = method.upper() + '&' + percent_encode(url) + '&' + percent_encode(
        '&'.join(sorted(f"{percent_encode(k)}={percent_encode(v)}" for k, v in params.items()))
    )
    signing_key = percent_encode(consumer_secret) + '&' + percent_encode(token_secret)
    signature = hmac.new(signing_key.encode('utf-8'), base_string.encode('utf-8'), hashlib.sha1).digest()
    return base64.b64encode(signature).decode('utf-8')

def post_to_x(texts):
    if not texts:
        print("Error: No text provided")
        sys.exit(1)

    consumer_key = os.getenv('TWITTER_API_KEY')
    consumer_secret = os.getenv('TWITTER_API_SECRET')
    access_token = os.getenv('TWITTER_ACCESS_TOKEN')
    access_secret = os.getenv('TWITTER_ACCESS_SECRET')

    if not all([consumer_key, consumer_secret, access_token, access_secret]):
        print("Error: Missing Twitter API environment variables")
        sys.exit(1)

    url = "https://api.twitter.com/2/tweets"
    last_tweet_id = None

    for i, text in enumerate(texts):
        if len(text) > 280:
            text = text[:277] + "..."

        oauth_params = {
            "oauth_consumer_key": consumer_key,
            "oauth_nonce": str(uuid.uuid4()).replace('-', ''),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": access_token,
            "oauth_version": "1.0"
        }

        payload = {"text": text}
        if last_tweet_id:
            payload["reply"] = {"in_reply_to_tweet_id": last_tweet_id}

        # Combine params for signature (OAuth + body)
        all_params = {**oauth_params, **payload} if isinstance(payload, dict) else oauth_params

        oauth_params["oauth_signature"] = create_oauth_signature("POST", url, all_params, consumer_secret, access_secret)

        # Build Authorization header
        auth_header = "OAuth " + ', '.join(
            f'{k}="{percent_encode(v)}"' for k, v in sorted(oauth_params.items())
        )

        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json"
        }

        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                last_tweet_id = result['data']['id']
                print(f"Posted part {i+1}/{len(texts)}: {text[:100]}... ID: {last_tweet_id}")
        except Exception as e:
            print("Error posting:", e)
            sys.exit(1)

    print("✅ All tweets posted successfully!")

if __name__ == "__main__":
    import os
    post_to_x(sys.argv[1:])
