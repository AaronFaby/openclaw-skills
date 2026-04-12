#!/usr/bin/env python3
"""Normalized JSON wrapper for common discrawl queries."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any

FALLBACK_BINARY = "/home/linuxbrew/.linuxbrew/bin/discrawl"
TABLE_SPLIT_RE = re.compile(r"\s{2,}")


class DiscrawlError(RuntimeError):
    pass


def resolve_binary(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    discovered = shutil.which("discrawl")
    if discovered:
        return discovered
    if os.path.exists(FALLBACK_BINARY):
        return FALLBACK_BINARY
    raise DiscrawlError("discrawl binary not found on PATH and fallback path is missing")


def run_discrawl(binary: str, args: list[str], *, json_output: bool = False) -> subprocess.CompletedProcess[str]:
    cmd = [binary]
    if json_output:
        cmd.append("--json")
    cmd.extend(args)
    return subprocess.run(cmd, capture_output=True, text=True)


def require_success(result: subprocess.CompletedProcess[str], cmd: list[str]) -> None:
    if result.returncode != 0:
        raise DiscrawlError(result.stderr.strip() or result.stdout.strip() or f"discrawl failed: {' '.join(cmd)}")


def parse_json_output(result: subprocess.CompletedProcess[str]) -> Any:
    text = (result.stdout or "").strip()
    if not text:
        return None
    return json.loads(text)


def parse_key_value_lines(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for line in text.splitlines():
        if not line.strip() or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def parse_table(text: str) -> list[dict[str, str]]:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return []
    headers = TABLE_SPLIT_RE.split(lines[0].strip())
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        parts = TABLE_SPLIT_RE.split(line.strip())
        if not parts:
            continue
        if len(parts) < len(headers):
            parts.extend([""] * (len(headers) - len(parts)))
        if len(parts) > len(headers):
            head = parts[: len(headers) - 1]
            tail = " ".join(parts[len(headers) - 1 :])
            parts = head + [tail]
        rows.append({headers[i].lower(): parts[i] for i in range(len(headers))})
    return rows


def parse_member_show(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    header_lines: list[str] = []
    recent_messages: list[dict[str, str]] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line.strip() == "Recent messages:":
            idx += 1
            break
        header_lines.append(line)
        idx += 1
    data = parse_key_value_lines("\n".join(header_lines))
    while idx < len(lines):
        line = lines[idx].strip()
        if not line:
            idx += 1
            continue
        match = re.match(r"^\[(?P<channel>[^\]]+)\]\s+(?P<created_at>\S+)$", line)
        if match and idx + 1 < len(lines):
            recent_messages.append(
                {
                    "channel": match.group("channel"),
                    "created_at": match.group("created_at"),
                    "content": lines[idx + 1].rstrip(),
                }
            )
            idx += 2
            continue
        idx += 1
    data["recent_messages"] = recent_messages
    return data


def add_common_search_filters(parser: argparse.ArgumentParser, *, include_query: bool = False, include_channel: bool = True, include_target: bool = False) -> None:
    if include_query:
        parser.add_argument("query")
    if include_channel:
        parser.add_argument("--channel")
    parser.add_argument("--guild")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--author")
    parser.add_argument("--since")
    parser.add_argument("--days", type=int)
    parser.add_argument("--hours", type=int)
    parser.add_argument("--include-empty", action="store_true")
    parser.add_argument("--sync", action="store_true")
    if include_target:
        parser.add_argument("--target")
        parser.add_argument("--type", choices=["user", "role"])


def maybe_add(cmd: list[str], flag: str, value: Any) -> None:
    if value is None or value is False:
        return
    if value is True:
        cmd.append(flag)
    else:
        cmd.extend([flag, str(value)])


def handle_doctor(args: argparse.Namespace) -> dict[str, Any]:
    result = run_discrawl(args.binary, ["doctor"])
    require_success(result, ["doctor"])
    parsed = parse_key_value_lines(result.stdout)
    return {
        "ok": True,
        "operation": "doctor",
        "result": parsed,
        "raw_text": result.stdout.strip(),
    }


def handle_status(args: argparse.Namespace) -> dict[str, Any]:
    result = run_discrawl(args.binary, ["status"])
    require_success(result, ["status"])
    parsed = parse_key_value_lines(result.stdout)
    return {
        "ok": True,
        "operation": "status",
        "result": parsed,
        "raw_text": result.stdout.strip(),
    }


def handle_search(args: argparse.Namespace) -> dict[str, Any]:
    cmd = ["search"]
    maybe_add(cmd, "--guild", args.guild)
    maybe_add(cmd, "--channel", args.channel)
    maybe_add(cmd, "--author", args.author)
    maybe_add(cmd, "--limit", args.limit)
    maybe_add(cmd, "--include-empty", args.include_empty)
    cmd.append(args.query)
    result = run_discrawl(args.binary, cmd, json_output=True)
    require_success(result, cmd)
    items = parse_json_output(result) or []
    return {"ok": True, "operation": "search", "count": len(items), "items": items, "command": cmd}


def handle_messages(args: argparse.Namespace) -> dict[str, Any]:
    cmd = ["messages"]
    maybe_add(cmd, "--channel", args.channel)
    maybe_add(cmd, "--author", args.author)
    maybe_add(cmd, "--since", args.since)
    maybe_add(cmd, "--days", args.days)
    maybe_add(cmd, "--hours", args.hours)
    maybe_add(cmd, "--last", args.last)
    maybe_add(cmd, "--limit", args.limit)
    maybe_add(cmd, "--all", args.all)
    maybe_add(cmd, "--sync", args.sync)
    maybe_add(cmd, "--include-empty", args.include_empty)
    result = run_discrawl(args.binary, cmd, json_output=True)
    require_success(result, cmd)
    items = parse_json_output(result) or []
    return {"ok": True, "operation": "messages", "count": len(items), "items": items, "command": cmd}


def handle_mentions(args: argparse.Namespace) -> dict[str, Any]:
    cmd = ["mentions"]
    maybe_add(cmd, "--target", args.target)
    maybe_add(cmd, "--type", args.type)
    maybe_add(cmd, "--channel", args.channel)
    maybe_add(cmd, "--guild", args.guild)
    maybe_add(cmd, "--since", args.since)
    maybe_add(cmd, "--days", args.days)
    maybe_add(cmd, "--hours", args.hours)
    maybe_add(cmd, "--limit", args.limit)
    result = run_discrawl(args.binary, cmd, json_output=True)
    require_success(result, cmd)
    items = parse_json_output(result) or []
    return {"ok": True, "operation": "mentions", "count": len(items), "items": items, "command": cmd}


def handle_members_list(args: argparse.Namespace) -> dict[str, Any]:
    cmd = ["members", "list"]
    result = run_discrawl(args.binary, cmd, json_output=True)
    require_success(result, cmd)
    items = parse_json_output(result) or []
    return {"ok": True, "operation": "members-list", "count": len(items), "items": items, "command": cmd}


def handle_member_search(args: argparse.Namespace) -> dict[str, Any]:
    cmd = ["members", "search", args.query]
    result = run_discrawl(args.binary, cmd)
    require_success(result, cmd)
    items = parse_table(result.stdout)
    return {
        "ok": True,
        "operation": "member-search",
        "count": len(items),
        "items": items,
        "command": cmd,
        "raw_text": result.stdout.strip(),
    }


def handle_member_show(args: argparse.Namespace) -> dict[str, Any]:
    cmd = ["members", "show"]
    maybe_add(cmd, "--messages", args.messages)
    cmd.append(args.query)
    result = run_discrawl(args.binary, cmd)
    require_success(result, cmd)
    item = parse_member_show(result.stdout)
    return {
        "ok": True,
        "operation": "member-show",
        "item": item,
        "command": cmd,
        "raw_text": result.stdout.strip(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalized wrapper for common discrawl queries")
    parser.add_argument("--binary", help="Path to discrawl binary")
    subparsers = parser.add_subparsers(dest="operation", required=True)

    doctor = subparsers.add_parser("doctor")
    doctor.set_defaults(func=handle_doctor)

    status = subparsers.add_parser("status")
    status.set_defaults(func=handle_status)

    search = subparsers.add_parser("search")
    add_common_search_filters(search, include_query=True)
    search.set_defaults(func=handle_search)

    messages = subparsers.add_parser("messages")
    messages.add_argument("--channel")
    messages.add_argument("--author")
    messages.add_argument("--since")
    messages.add_argument("--days", type=int)
    messages.add_argument("--hours", type=int)
    messages.add_argument("--last", type=int)
    messages.add_argument("--limit", type=int)
    messages.add_argument("--all", action="store_true")
    messages.add_argument("--sync", action="store_true")
    messages.add_argument("--include-empty", action="store_true")
    messages.set_defaults(func=handle_messages)

    mentions = subparsers.add_parser("mentions")
    mentions.add_argument("--target")
    mentions.add_argument("--type", choices=["user", "role"])
    mentions.add_argument("--channel")
    mentions.add_argument("--guild")
    mentions.add_argument("--since")
    mentions.add_argument("--days", type=int)
    mentions.add_argument("--hours", type=int)
    mentions.add_argument("--limit", type=int)
    mentions.set_defaults(func=handle_mentions)

    members_list = subparsers.add_parser("members-list")
    members_list.set_defaults(func=handle_members_list)

    member_search = subparsers.add_parser("member-search")
    member_search.add_argument("query")
    member_search.set_defaults(func=handle_member_search)

    member_show = subparsers.add_parser("member-show")
    member_show.add_argument("query")
    member_show.add_argument("--messages", type=int)
    member_show.set_defaults(func=handle_member_show)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.binary = resolve_binary(args.binary)
        payload = args.func(args)
    except DiscrawlError as exc:
        json.dump({"ok": False, "error": str(exc)}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 1
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
