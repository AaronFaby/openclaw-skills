import os
import sys
import requests
from datetime import datetime
from pathlib import Path
import argparse

def generate_image(prompt: str, n: int = 1):
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        print("❌ XAI_API_KEY not found in environment!")
        return None

    url = "https://api.x.ai/v1/images/generations"
    payload = {
        "model": "grok-imagine-image",
        "prompt": prompt,
        "n": n,
        "response_format": "url"
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ API error: {response.status_code} - {response.text}")
        return None

    data = response.json()
    saved_paths = []

    images_dir = Path.home() / ".openclaw" / "media" / "outbound"
    images_dir.mkdir(parents=True, exist_ok=True)

    for i, item in enumerate(data.get("data", [])):
        img_url = item.get("url")
        if img_url:
            img_data = requests.get(img_url).content
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"grok_imagine_{timestamp}_{i+1}.jpg"
            filepath = images_dir / filename
            
            filepath.write_bytes(img_data)
            saved_paths.append(str(filepath))
            print(f"✅ Saved: {filepath}")

    return saved_paths

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", nargs="+")
    parser.add_argument("--n", type=int, default=1)
    args = parser.parse_args()
    
    prompt_text = " ".join(args.prompt)
    paths = generate_image(prompt_text, args.n)
    
    if paths:
        print(f"Success! Generated {len(paths)} image(s)")
    else:
        print("Generation failed.")
