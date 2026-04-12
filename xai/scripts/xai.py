#!/usr/bin/env python3
"""
xai.py — xAI/Grok CLI for OpenClaw skill
Commands: chat, vision, search-x, search-web, models, stream
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

API_BASE = "https://api.x.ai/v1"
DEFAULT_TIMEOUT = 180


def _in_venv() -> bool:
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def _ensure_venv() -> None:
    if _in_venv():
        return
    venv_python = Path(__file__).resolve().parent / ".venv" / "bin" / "python"
    if venv_python.exists():
        os.execv(str(venv_python), [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]])


def _load_env() -> None:
    candidates = [
        Path(__file__).resolve().parent / ".env",
        Path.home() / ".openclaw" / ".env",
        Path.cwd() / ".env",
    ]
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def _die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _api_key() -> str:
    key = os.environ.get("XAI_API_KEY", "").strip()
    if not key:
        _die("XAI_API_KEY is not set. Add it to ~/.openclaw/.env or export it in shell.")
    return key


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, payload: dict[str, Any] | None = None, stream: bool = False):
    url = f"{API_BASE}{path}"
    try:
        r = requests.request(
            method,
            url,
            headers=_headers(),
            json=payload,
            timeout=DEFAULT_TIMEOUT,
            stream=stream,
        )
    except requests.RequestException as e:
        _die(f"Network error: {e}")

    if r.status_code >= 400:
        try:
            err = r.json()
        except Exception:
            err = {"error": r.text}
        _die(f"HTTP {r.status_code}: {json.dumps(err)}")
    return r


def _emit(obj: Any, fmt: str) -> None:
    if fmt == "raw":
        print(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))
    else:
        print(json.dumps(obj, indent=2, ensure_ascii=False))


def _extract_text(response_json: dict[str, Any]) -> str:
    output = response_json.get("output", [])
    chunks: list[str] = []
    for item in output:
        for c in item.get("content", []):
            if c.get("type") in {"output_text", "text"} and c.get("text"):
                chunks.append(c["text"])
    if chunks:
        return "\n".join(chunks).strip()                                                                                                                                          return response_json.get("output_text", "") or ""


def _models() -> list[dict[str, Any]]:
    r = _request("GET", "/models")
    data = r.json()
    models = data.get("data", [])
    return models if isinstance(models, list) else []


def _choose_latest_model(preferred: str | None = None, require_vision: bool = False) -> str:
    if preferred:
        return preferred

    items = _models()
    ids = [m.get("id", "") for m in items if isinstance(m, dict)]
    # Prefer latest grok-4/5 reasoning or fast reasoning families.
    rank_patterns = [
        r"^grok-5.*",
        r"^grok-4-1-fast-reasoning$",
        r"^grok-4-fast-reasoning$",
        r"^grok-4.*",
        r"^grok-3.*",
    ]

    for pat in rank_patterns:
        matches = sorted([m for m in ids if re.match(pat, m)])
        if matches:
            return matches[-1]

    if ids:
        return sorted(ids)[-1]
    _die("No models returned by /v1/models")
    return ""


def _image_part(image: str) -> dict[str, Any]:
    if image.startswith("http://") or image.startswith("https://"):
        return {"type": "image_url", "image_url": {"url": image, "detail": "high"}}

    p = Path(image).expanduser().resolve()
    if not p.exists() or not p.is_file():
        _die(f"Image path not found: {p}")

    mime, _ = mimetypes.guess_type(str(p))
    if mime not in {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}:
        mime = "image/png"
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"}}


def cmd_models(args: argparse.Namespace) -> None:
    data = _models()
    out = [{"id": m.get("id"), "owned_by": m.get("owned_by")} for m in data]
    _emit(out if args.format == "pretty" else {"data": out}, args.format)


def _responses_create(model: str, user_content: Any, tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "input": [{"role": "user", "content": user_content}],
    }
    if tools:
        payload["tools"] = tools
    r = _request("POST", "/responses", payload)
    return r.json()


def cmd_chat(args: argparse.Namespace) -> None:
    model = _choose_latest_model(args.model)
    resp = _responses_create(model=model, user_content=args.prompt)
    if args.format == "raw":
        _emit(resp, args.format)
    else:
        _emit({"model": model, "text": _extract_text(resp), "id": resp.get("id")}, args.format)


def cmd_vision(args: argparse.Namespace) -> None:
    model = _choose_latest_model(args.model, require_vision=True)
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": args.prompt},
                    _image_part(args.image),
                ],
            }
        ],
    }
    r = _request("POST", "/chat/completions", payload)
    resp = r.json()
    if args.format == "raw":
        _emit(resp, args.format)
    else:
        text = ""
        try:
            text = resp["choices"][0]["message"]["content"]
        except Exception:
            text = ""
        _emit({"model": model, "text": text, "id": resp.get("id")}, args.format)


def _parse_handles(handles_csv: str | None) -> list[str]:
    if not handles_csv:
        return []
    raw = [h.strip().lstrip("@") for h in handles_csv.split(",") if h.strip()]
    if len(raw) > 10:
        _die("--handles supports max 10 handles")
    return raw


def _date_range(days: int) -> tuple[str, str]:
    if days <= 0:
        _die("--days must be > 0")
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


def cmd_search_x(args: argparse.Namespace) -> None:
    model = _choose_latest_model(args.model)
    from_date, to_date = _date_range(args.days)
    handles = _parse_handles(args.handles)
    tool: dict[str, Any] = {"type": "x_search", "from_date": from_date, "to_date": to_date}
    if handles:
        tool["allowed_x_handles"] = handles
    resp = _responses_create(model=model, user_content=args.query, tools=[tool])
    if args.format == "raw":
        _emit(resp, args.format)
    else:
        _emit(
            {
                "model": model,
                "query": args.query,
                "range": {"from_date": from_date, "to_date": to_date},
                "handles": handles,
                "text": _extract_text(resp),
                "citations": resp.get("citations", []),
            },
            args.format,
        )


def cmd_search_web(args: argparse.Namespace) -> None:
    model = _choose_latest_model(args.model)
    resp = _responses_create(model=model, user_content=args.query, tools=[{"type": "web_search"}])
    if args.format == "raw":
        _emit(resp, args.format)
    else:
        _emit(
            {
                "model": model,
                "query": args.query,
                "text": _extract_text(resp),
                "citations": resp.get("citations", []),
            },
            args.format,
        )


def cmd_stream(args: argparse.Namespace) -> None:
    model = _choose_latest_model(args.model)
    payload = {
        "model": model,
        "stream": True,
        "input": [{"role": "user", "content": args.prompt}],
    }
    r = _request("POST", "/responses", payload, stream=True)

    if args.format == "raw":
        for line in r.iter_lines(decode_unicode=True):
            if line:
                print(line)
        return

    print(f"[model={model}]", file=sys.stderr)
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        data = line[len("data:") :].strip()
        if data == "[DONE]":
            print()
            break
        try:
            obj = json.loads(data)
        except Exception:
            continue
        t = obj.get("type", "")
        if t.endswith("output_text.delta"):
            delta = obj.get("delta", "")
            if delta:
                print(delta, end="", flush=True)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="xai.py", description="xAI/Grok CLI")
    p.add_argument("--format", choices=["raw", "pretty"], default="pretty")

    sub = p.add_subparsers(dest="command", required=True)

    p_models = sub.add_parser("models", help="List available xAI models")
    p_models.set_defaults(func=cmd_models)

    p_chat = sub.add_parser("chat", help="Text chat with Grok")
    p_chat.add_argument("--model", default=None)
    p_chat.add_argument("--prompt", required=True)
    p_chat.set_defaults(func=cmd_chat)

    p_vision = sub.add_parser("vision", help="Analyze image with prompt")
    p_vision.add_argument("--model", default=None)
    p_vision.add_argument("--image", required=True, help="Path or URL")
    p_vision.add_argument("--prompt", required=True)
    p_vision.set_defaults(func=cmd_vision)

    p_sx = sub.add_parser("search-x", help="Search X/Twitter via x_search tool")
    p_sx.add_argument("--model", default=None)
    p_sx.add_argument("--query", required=True)
    p_sx.add_argument("--days", type=int, default=7)
    p_sx.add_argument("--handles", default=None, help="Comma-separated allowlist handles")
    p_sx.set_defaults(func=cmd_search_x)

    p_sw = sub.add_parser("search-web", help="Search web via web_search tool")
    p_sw.add_argument("--model", default=None)
    p_sw.add_argument("--query", required=True)
    p_sw.set_defaults(func=cmd_search_web)

    p_stream = sub.add_parser("stream", help="Streaming chat response")
    p_stream.add_argument("--model", default=None)
    p_stream.add_argument("--prompt", required=True)
    p_stream.set_defaults(func=cmd_stream)

    return p


def main() -> None:
    _ensure_venv()
    _load_env()
    parser = build_parser()
    args, remaining = parser.parse_known_args()

    # Allow --format after subcommand for convenience.
    for i, token in enumerate(remaining):
        if token == "--format" and i + 1 < len(remaining):
            val = remaining[i + 1]
            if val in {"raw", "pretty"}:
                args.format = val

    args.func(args)


if __name__ == "__main__":
    main()
