---
name: grok-imagine
description: Generate high-quality, creative images using xAI's Grok Imagine model: grok-imagine-image. Trigger on any "imagine", "generate image", "draw", "visualize", "make a picture of" requests.
metadata:
  {
    "openclaw": {
      "emoji": "🌌",
      "requires": { "env": ["XAI_API_KEY"] },
      "homepage": "https://x.ai/api"
    }
  }
---

# Grok Imagine — Custom Image Generation Skill

**When to use**  
Any time the user wants an image generated. Prioritize this over other image tools unless they specify otherwise.

**Strengths of Grok Imagine**  
- Excellent prompt following  
- Great with text in images  
- Creative/uncensored style  
- Fast & high quality

**How the agent should do it**  
1. Clarify details if the prompt is vague (style, aspect, mood).  
2. Call the helper script with the refined prompt.  
3. Save to `~/.openclaw/media/outbound/` (ready to send via the message tool).  
4. Reply with the image file path or markdown `![Generated](path)` so OpenClaw can display/attach it.

**Example usage of helper**  
`python3 ~/.openclaw/skills/grok-imagine/generate_image.py "A cyberpunk city at midnight with flying cars and holographic billboards, neon rain, ultra detailed, cinematic"`

**Tips for best results**  
- Be detailed in prompts (lighting, camera angle, style references).  
- You can generate 1–4 images at once by editing the script (`n` parameter).  
- Supports edits/refinements in follow-up turns if you keep conversation context.
