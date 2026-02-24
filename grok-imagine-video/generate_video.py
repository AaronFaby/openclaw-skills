import os
import sys
import requests
import time
import argparse
from datetime import datetime
from pathlib import Path

def generate_video(prompt: str, duration: int = 8, aspect_ratio: str = "16:9", resolution: str = "720p"):
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        print("❌ XAI_API_KEY not found in environment!")
        return None

    url = "https://api.x.ai/v1/videos/generations"
    payload = {
        "model": "grok-imagine-video",
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    print("🚀 Submitting video generation request...")
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        print(f"❌ API error: {response.status_code} - {response.text}")
        return None

    request_id = response.json()["request_id"]
    print(f"✅ Request submitted (ID: {request_id})")
    print("⏳ Generating video... this usually takes 30–180 seconds")

    poll_url = f"https://api.x.ai/v1/videos/{request_id}"

    max_wait = 300  # 5 minutes timeout
    start_time = time.time()

    while time.time() - start_time < max_wait:
        time.sleep(8)
        poll_resp = requests.get(poll_url, headers=headers)
        
        if poll_resp.status_code not in (200, 202):
            print(f"❌ Polling error: {poll_resp.status_code} - {poll_resp.text}")
            return None
        if poll_resp.status_code == 202:
            print(f"   Still queued... ({int(time.time() - start_time)}s elapsed)")
            continue

        data = poll_resp.json()
        
        if data.get("status") == "done" or "video" in data:
            video_url = data.get("video", {}).get("url")
            if not video_url:
                video_url = data.get("url")  # fallback
            break
        elif data.get("status") == "expired":
            print("❌ Request expired")
            return None
        else:
            print(f"   Still processing... ({int(time.time() - start_time)}s elapsed)")

    if not video_url:
        print("❌ Video never completed")
        return None

    # Download
    print("📥 Downloading video...")
    video_data = requests.get(video_url).content

    videos_dir = Path.home() / ".openclaw" / "media" / "outbound"
    videos_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"grok_imagine_video_{timestamp}.mp4"
    filepath = videos_dir / filename

    filepath.write_bytes(video_data)
    print(f"✅ Saved: {filepath}")
    print(f"🎬 Duration: {data.get('video', {}).get('duration', duration)}s")

    return str(filepath)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", nargs="+")
    parser.add_argument("--duration", type=int, default=8, help="Duration in seconds (1-15)")
    parser.add_argument("--aspect", default="16:9", help="Aspect ratio e.g. 16:9, 9:16, 1:1")
    parser.add_argument("--resolution", default="720p", choices=["480p", "720p"])
    args = parser.parse_args()
    
    prompt_text = " ".join(args.prompt)
    path = generate_video(prompt_text, args.duration, args.aspect, args.resolution)
    
    if path:
        print(f"\nSuccess! Video ready: {path}")
    else:
        print("Generation failed.")
