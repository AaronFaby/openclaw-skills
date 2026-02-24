---
name: grok-imagine-video
description: "Generate short high-quality videos with native audio using xAI's Grok Imagine Video (model: grok-imagine-video). Trigger on \"generate video\", \"make a video of\", \"animate\", \"create a video\", \"video of\", \"turn this into a video\", \"grok video\"."
metadata: {"openclaw":{"emoji":"🎥","requires":{"env":["XAI_API_KEY"]},"homepage":"https://docs.x.ai/developers/model-capabilities/video/generation"}}
---

# Grok Imagine Video — xAI Grok Imagine Video Generation Skill

**When to use**
Any time the user wants a short video generated or animated. Prioritize this over other video tools unless they specify otherwise.

**Strengths of Grok Imagine Video (Feb 2026)**
- Cinematic prompt adherence (camera moves, lighting, physics)
- Native audio: sound effects, music, voice, ambient
- Photorealistic OR stylized (cyberpunk, anime, oil painting, etc.)
- Image-to-video & video-to-video editing supported in follow-ups
- 1–15 seconds, 480p/720p, multiple aspect ratios

**How the agent should do it**
1. Clarify vague prompts (duration, aspect, style, camera movement).
2. Call the helper script.
3. Tell user: "Generating video with Grok Imagine Video… usually 30–180 seconds."
4. Save to `~/.openclaw/media/outbound/` and reply with the .mp4 path (OpenClaw auto-plays it).

**Example usage of helper**
`python3 ~/.openclaw/skills/grok-imagine-video/generate_video.py "Cyberpunk hacker in East La Mirada at night, neon rain, flying cars, holographic billboards" --duration 10 --aspect 16:9 --resolution 720p`

**Tips for best results**
- Use cinematic language: "slow dolly zoom in", "drone tracking shot", "epic crane shot", "POV running through neon streets"
- Default = 8 seconds, 16:9, 720p
- Vertical Reels/TikTok: `--aspect 9:16`
- Longer videos = higher cost & slightly longer wait
- Video URLs expire fast — script auto-downloads immediately
- Edge case: If prompt is too complex, Grok may shorten it slightly — just regenerate with more specific instructions
