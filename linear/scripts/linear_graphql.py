#!/usr/bin/env python3
"""Safe local Linear GraphQL wrapper with ergonomic canned commands.

Reads LINEAR_API_KEY from environment or /home/netwatch/.openclaw/secrets/linear-api-key.
Never prints the key. Logs write operations to ~/.openclaw/logs/linear-actions.jsonl.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ENDPOINT = "https://api.linear.app/graphql"
SECRET_FILE = Path("/home/netwatch/.openclaw/secrets/linear-api-key")
AUDIT_LOG = Path("/home/netwatch/.openclaw/logs/linear-actions.jsonl")
USER_AGENT = "openclaw-linear-skill/1.1"

PRIORITY_MAP = {
    "none": 0,
    "urgent": 1,
    "high": 2,
    "medium": 3,
    "low": 4,
}
PRIORITY_LABELS = {value: key for key, value in PRIORITY_MAP.items()}

ISSUE_FIELDS = """
  id
  identifier
  title
  url
  priority
  state { id name type team { id key name } }
  team { id key name }
  project { id name url }
  assignee { id name email }
  updatedAt
"""

PROJECT_FIELDS = """
  id
  name
  url
  state
  teams { nodes { id key name } }
  updatedAt
"""


class LinearCliError(RuntimeError):
    """Expected command-line failure with a clean user-facing message."""


class LinearApiError(RuntimeError):
    """Linear returned GraphQL/API errors."""

    def __init__(self, response: dict[str, Any]):
        self.response = response
        messages = [str(err.get("message", err)) for err in response.get("errors", [])]
        super().__init__("; ".join(messages) or "Linear API returned an error")


def load_key() -> str:
    key = os.environ.get("LINEAR_API_KEY", "").strip()
    if not key and SECRET_FILE.exists():
        key = SECRET_FILE.read_text().strip()
    if not key:
        raise LinearCliError("LINEAR_API_KEY is not set and secret file is missing")
    return key


def parse_json(value: str, label: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise LinearCliError(f"{label} must be valid JSON: {exc}") from exc


def read_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.file:
        raw = Path(args.file).read_text()
    elif args.query:
        payload: dict[str, Any] = {"query": args.query}
        if args.variables:
            variables = parse_json(args.variables, "--variables")
            if not isinstance(variables, dict):
                raise LinearCliError("--variables must be a JSON object")
            payload["variables"] = variables
        return payload
    else:
        raw = sys.stdin.read()
    payload = parse_json(raw, "payload")
    if not isinstance(payload, dict) or "query" not in payload:
        raise LinearCliError("payload must be an object with a 'query' field")
    return payload


def operation_kind(query: str) -> str:
    stripped = " ".join(line.strip() for line in query.strip().splitlines() if not line.strip().startswith("#"))
    return "mutation" if stripped.lower().startswith("mutation") or " mutation " in f" {stripped.lower()} " else "query"


def operation_name(query: str) -> str | None:
    tokens = " ".join(query.replace("(", " ").split()).split()
    for idx, token in enumerate(tokens[:-1]):
        if token in {"query", "mutation", "subscription"}:
            candidate = tokens[idx + 1].strip("{")
            return candidate if candidate and candidate != "{" else None
    return None


def audit(
    payload: dict[str, Any],
    response: dict[str, Any] | None,
    http_status: int | None,
    ok: bool,
    *,
    command: str | None = None,
    source: str | None = None,
) -> None:
    query = str(payload.get("query", ""))
    kind = operation_kind(query)
    if kind != "mutation":
        return
    variables = payload.get("variables") if isinstance(payload.get("variables"), dict) else {}
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kind": kind,
        "operationName": operation_name(query),
        "command": command,
        "source": source,
        "operationPreview": query[:300],
        "variablesKeys": sorted(variables.keys()),
        "httpStatus": http_status,
        "ok": ok,
        "hasErrors": bool(response and response.get("errors")),
    }
    with AUDIT_LOG.open("a") as f:
        f.write(json.dumps(entry, separators=(",", ":")) + "\n")


def call_linear(
    payload: dict[str, Any],
    *,
    key: str | None = None,
    command: str | None = None,
    source: str | None = None,
    raise_on_error: bool = True,
) -> dict[str, Any]:
    api_key = key or load_key()
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": api_key,
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    response_obj: dict[str, Any] | None = None
    status: int | None = None
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read().decode("utf-8", errors="replace")
    except Exception as exc:
        audit(payload, None, status, False, command=command, source=source)
        raise LinearCliError(f"Linear request failed: {exc}") from exc

    try:
        response_obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        audit(payload, None, status, False, command=command, source=source)
        raise LinearCliError(f"Linear returned non-JSON response: {raw[:500]}") from exc

    ok = 200 <= (status or 0) < 300 and not response_obj.get("errors")
    audit(payload, response_obj, status, ok, command=command, source=source)
    if raise_on_error and not ok:
        raise LinearApiError(response_obj)
    return response_obj


def print_json(obj: Any, pretty: bool) -> None:
    print(json.dumps(obj, indent=2 if pretty else None, sort_keys=pretty))


def parse_priority(value: str | int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        if value in PRIORITY_LABELS:
            return value
        raise LinearCliError(f"priority integer must be 0-4, got {value}")
    text = str(value).strip().lower()
    if text in PRIORITY_MAP:
        return PRIORITY_MAP[text]
    if text.isdigit():
        number = int(text)
        if number in PRIORITY_LABELS:
            return number
    raise LinearCliError(f"priority must be one of {', '.join(PRIORITY_MAP)} or 0-4")


def add_audit_note(body: str, source: str | None) -> str:
    source_text = source or "openclaw-linear-skill"
    return f"{body.rstrip()}\n\n---\n_Source: {source_text}_"


def connection_nodes(response: dict[str, Any], *path: str) -> list[dict[str, Any]]:
    current: Any = response.get("data", {})
    for part in path:
        current = current.get(part, {}) if isinstance(current, dict) else {}
    nodes = current.get("nodes", []) if isinstance(current, dict) else []
    return nodes if isinstance(nodes, list) else []


def team_selector_args(parser: argparse.ArgumentParser, *, required: bool = False) -> None:
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument("--team-id", help="Linear team UUID")
    group.add_argument("--team-key", help="Linear team key, e.g. ENG")


def issue_selector_args(parser: argparse.ArgumentParser, *, required: bool = False) -> None:
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument("--issue-id", help="Linear issue UUID")
    group.add_argument("--identifier", help="Linear issue identifier, e.g. ENG-123")


def project_selector_args(parser: argparse.ArgumentParser, *, required: bool = False) -> None:
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument("--project-id", help="Linear project UUID")
    group.add_argument("--project-name", help="Linear project name")


def resolve_team_id(args: argparse.Namespace, key: str) -> str:
    if getattr(args, "team_id", None):
        return args.team_id
    if not getattr(args, "team_key", None):
        raise LinearCliError("provide --team-id or --team-key")
    payload = {
        "query": "query TeamByKey($key: String!) { teams(filter: { key: { eq: $key } }, first: 2) { nodes { id key name } } }",
        "variables": {"key": args.team_key},
    }
    nodes = connection_nodes(call_linear(payload, key=key, command="team lookup"), "teams")
    if not nodes:
        raise LinearCliError(f"team not found for key {args.team_key!r}")
    if len(nodes) > 1:
        raise LinearCliError(f"multiple teams matched key {args.team_key!r}; use --team-id")
    return str(nodes[0]["id"])


def resolve_issue_id(args: argparse.Namespace, key: str) -> str:
    if getattr(args, "issue_id", None):
        return args.issue_id
    if not getattr(args, "identifier", None):
        raise LinearCliError("provide --issue-id or --identifier")
    payload = {
        "query": f"query IssueByIdentifier($identifier: String!) {{ issue(id: $identifier) {{ {ISSUE_FIELDS} }} }}",
        "variables": {"identifier": args.identifier},
    }
    issue = call_linear(payload, key=key, command="issue lookup").get("data", {}).get("issue")
    if not issue:
        raise LinearCliError(f"issue not found for identifier {args.identifier!r}")
    return str(issue["id"])


def find_project_by_name(name: str, key: str) -> dict[str, Any] | None:
    payload = {
        "query": f"query ProjectByName($name: String!) {{ projects(filter: {{ name: {{ eq: $name }} }}, first: 2) {{ nodes {{ {PROJECT_FIELDS} }} }} }}",
        "variables": {"name": name},
    }
    nodes = connection_nodes(call_linear(payload, key=key, command="project lookup"), "projects")
    if not nodes:
        return None
    if len(nodes) > 1:
        raise LinearCliError(f"multiple projects matched name {name!r}; use --project-id")
    return nodes[0]


def resolve_project_id(args: argparse.Namespace, key: str) -> str | None:
    if getattr(args, "project_id", None):
        return args.project_id
    name = getattr(args, "project_name", None)
    if not name:
        return None
    project = find_project_by_name(name, key)
    if not project:
        raise LinearCliError(f"project not found for name {name!r}")
    return str(project["id"])


def handle_raw(args: argparse.Namespace) -> int:
    payload = read_payload(args)
    response = call_linear(payload, command="raw", source=args.source, raise_on_error=False)
    print_json(response, args.pretty)
    return 0 if not response.get("errors") else 1


def handle_viewer(args: argparse.Namespace) -> int:
    response = call_linear({"query": "query Me { viewer { id name email } }"}, command="viewer")
    print_json(response, args.pretty)
    return 0


def handle_team_list(args: argparse.Namespace) -> int:
    response = call_linear(
        {"query": "query Teams($first: Int!) { teams(first: $first) { nodes { id key name } } }", "variables": {"first": args.limit}},
        command="team list",
    )
    print_json(response, args.pretty)
    return 0


def handle_project_lookup(args: argparse.Namespace) -> int:
    key = load_key()
    if args.project_id:
        payload = {"query": f"query Project($id: String!) {{ project(id: $id) {{ {PROJECT_FIELDS} }} }}", "variables": {"id": args.project_id}}
        response = call_linear(payload, key=key, command="project lookup")
        print_json(response, args.pretty)
        return 0
    project = find_project_by_name(args.project_name, key)
    print_json({"data": {"project": project}}, args.pretty)
    return 0 if project else 1


def handle_project_create(args: argparse.Namespace) -> int:
    key = load_key()
    existing = find_project_by_name(args.name, key) if args.if_missing else None
    if existing:
        print_json({"data": {"projectCreate": {"success": True, "created": False, "project": existing}}}, args.pretty)
        return 0

    team_ids = []
    if args.team_id or args.team_key:
        team_ids = [resolve_team_id(args, key)]
    input_obj: dict[str, Any] = {"name": args.name}
    if args.description:
        input_obj["description"] = args.description
    if args.content:
        input_obj["content"] = args.content
    if team_ids:
        input_obj["teamIds"] = team_ids
    payload = {
        "query": f"mutation ProjectCreate($input: ProjectCreateInput!) {{ projectCreate(input: $input) {{ success project {{ {PROJECT_FIELDS} }} }} }}",
        "variables": {"input": input_obj},
    }
    response = call_linear(payload, key=key, command="project create", source=args.source)
    print_json(response, args.pretty)
    return 0


def handle_issue_lookup(args: argparse.Namespace) -> int:
    payload = {"query": f"query Issue($id: String!) {{ issue(id: $id) {{ {ISSUE_FIELDS} description }} }}", "variables": {"id": args.issue_id or args.identifier}}
    response = call_linear(payload, command="issue lookup")
    print_json(response, args.pretty)
    return 0


def handle_issue_list(args: argparse.Namespace) -> int:
    variables: dict[str, Any] = {"first": args.limit}
    filters: list[str] = []
    if args.team_key:
        filters.append("team: { key: { eq: $teamKey } }")
        variables["teamKey"] = args.team_key
    if args.project_name:
        filters.append("project: { name: { eq: $projectName } }")
        variables["projectName"] = args.project_name
    if args.state:
        filters.append("state: { name: { eq: $state } }")
        variables["state"] = args.state
    if args.query_text:
        filters.append("or: [{ title: { containsIgnoreCase: $queryText } }, { description: { containsIgnoreCase: $queryText } }]")
        variables["queryText"] = args.query_text
    filter_block = f", filter: {{ {', '.join(filters)} }}" if filters else ""
    variable_defs = ["$first: Int!"]
    if "teamKey" in variables:
        variable_defs.append("$teamKey: String!")
    if "projectName" in variables:
        variable_defs.append("$projectName: String!")
    if "state" in variables:
        variable_defs.append("$state: String!")
    if "queryText" in variables:
        variable_defs.append("$queryText: String!")
    payload = {
        "query": f"query IssueList({', '.join(variable_defs)}) {{ issues(first: $first, orderBy: updatedAt{filter_block}) {{ nodes {{ {ISSUE_FIELDS} }} }} }}",
        "variables": variables,
    }
    response = call_linear(payload, command="issue list")
    print_json(response, args.pretty)
    return 0


def find_existing_issue(args: argparse.Namespace, key: str, team_id: str, project_id: str | None) -> dict[str, Any] | None:
    if args.key_identifier:
        payload = {"query": f"query Issue($id: String!) {{ issue(id: $id) {{ {ISSUE_FIELDS} }} }}", "variables": {"id": args.key_identifier}}
        issue = call_linear(payload, key=key, command="issue lookup").get("data", {}).get("issue")
        return issue
    if not args.if_missing:
        return None
    variables: dict[str, Any] = {"title": args.title, "teamId": team_id}
    filters = ["title: { eq: $title }", "team: { id: { eq: $teamId } }"]
    variable_defs = ["$title: String!", "$teamId: ID!"]
    if project_id:
        filters.append("project: { id: { eq: $projectId } }")
        variables["projectId"] = project_id
        variable_defs.append("$projectId: ID!")
    payload = {
        "query": f"query ExistingIssue({', '.join(variable_defs)}) {{ issues(first: 2, filter: {{ {', '.join(filters)} }}) {{ nodes {{ {ISSUE_FIELDS} }} }} }}",
        "variables": variables,
    }
    nodes = connection_nodes(call_linear(payload, key=key, command="issue lookup"), "issues")
    if not nodes:
        return None
    if len(nodes) > 1:
        raise LinearCliError("multiple existing issues matched title/team/project; use --key-identifier for safe idempotency")
    return nodes[0]


def handle_issue_create(args: argparse.Namespace) -> int:
    key = load_key()
    team_id = resolve_team_id(args, key)
    project_id = resolve_project_id(args, key)
    existing = find_existing_issue(args, key, team_id, project_id)
    if existing:
        print_json({"data": {"issueCreate": {"success": True, "created": False, "issue": existing}}}, args.pretty)
        return 0

    input_obj: dict[str, Any] = {"teamId": team_id, "title": args.title}
    if args.description:
        input_obj["description"] = args.description
    if args.priority:
        input_obj["priority"] = parse_priority(args.priority)
    if project_id:
        input_obj["projectId"] = project_id
    if args.assignee_id:
        input_obj["assigneeId"] = args.assignee_id
    if args.label_id:
        input_obj["labelIds"] = args.label_id
    payload = {
        "query": f"mutation IssueCreate($input: IssueCreateInput!) {{ issueCreate(input: $input) {{ success issue {{ {ISSUE_FIELDS} }} }} }}",
        "variables": {"input": input_obj},
    }
    response = call_linear(payload, key=key, command="issue create", source=args.source)
    print_json(response, args.pretty)
    return 0


def handle_comment_add(args: argparse.Namespace) -> int:
    key = load_key()
    issue_id = resolve_issue_id(args, key)
    body = add_audit_note(args.body, args.source) if not args.no_source_footer else args.body
    payload = {
        "query": "mutation CommentCreate($input: CommentCreateInput!) { commentCreate(input: $input) { success comment { id url body createdAt issue { identifier title url } } } }",
        "variables": {"input": {"issueId": issue_id, "body": body}},
    }
    response = call_linear(payload, key=key, command="comment add", source=args.source)
    print_json(response, args.pretty)
    return 0


def handle_priority_set(args: argparse.Namespace) -> int:
    key = load_key()
    issue_id = resolve_issue_id(args, key)
    priority = parse_priority(args.priority)
    payload = {
        "query": f"mutation IssuePrioritySet($id: String!, $input: IssueUpdateInput!) {{ issueUpdate(id: $id, input: $input) {{ success issue {{ {ISSUE_FIELDS} }} }} }}",
        "variables": {"id": issue_id, "input": {"priority": priority}},
    }
    response = call_linear(payload, key=key, command="priority set", source=args.source)
    print_json(response, args.pretty)
    return 0


def load_bulk_updates(path: str) -> list[dict[str, Any]]:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text()
    data = parse_json(raw, "bulk priority input")
    updates = data.get("updates") if isinstance(data, dict) else data
    if not isinstance(updates, list) or not updates:
        raise LinearCliError("bulk priority input must be a non-empty list or {'updates': [...]} object")
    normalized = []
    for idx, item in enumerate(updates):
        if not isinstance(item, dict):
            raise LinearCliError(f"bulk update #{idx + 1} must be an object")
        selector_count = sum(1 for key_name in ("issueId", "identifier") if item.get(key_name))
        if selector_count != 1:
            raise LinearCliError(f"bulk update #{idx + 1} must include exactly one of issueId or identifier")
        if "priority" not in item:
            raise LinearCliError(f"bulk update #{idx + 1} missing priority")
        normalized.append(item)
    return normalized


def handle_bulk_priority(args: argparse.Namespace) -> int:
    updates = load_bulk_updates(args.input)
    if len(updates) > 5 and not args.confirm_bulk:
        raise LinearCliError("bulk priority updates affecting more than 5 issues requires --confirm-bulk")
    key = load_key()
    results = []
    for item in updates:
        tmp = argparse.Namespace(issue_id=item.get("issueId"), identifier=item.get("identifier"))
        issue_id = resolve_issue_id(tmp, key)
        priority = parse_priority(item.get("priority"))
        payload = {
            "query": f"mutation BulkIssuePrioritySet($id: String!, $input: IssueUpdateInput!) {{ issueUpdate(id: $id, input: $input) {{ success issue {{ {ISSUE_FIELDS} }} }} }}",
            "variables": {"id": issue_id, "input": {"priority": priority}},
        }
        response = call_linear(payload, key=key, command="priority bulk-set", source=args.source)
        results.append(response.get("data", {}).get("issueUpdate"))
    print_json({"data": {"bulkPrioritySet": {"success": True, "count": len(results), "results": results}}}, args.pretty)
    return 0


def require_confirmation(args: argparse.Namespace, action: str) -> None:
    if not args.confirm:
        raise LinearCliError(f"{action} is destructive and requires --confirm")


def handle_issue_archive(args: argparse.Namespace) -> int:
    require_confirmation(args, "issue archive")
    key = load_key()
    issue_id = resolve_issue_id(args, key)
    payload = {
        "query": "mutation IssueArchive($id: String!) { issueArchive(id: $id) { success entity { id identifier title url archivedAt } } }",
        "variables": {"id": issue_id},
    }
    response = call_linear(payload, key=key, command="issue archive", source=args.source)
    print_json(response, args.pretty)
    return 0


def handle_project_archive(args: argparse.Namespace) -> int:
    require_confirmation(args, "project archive")
    key = load_key()
    project_id = args.project_id or resolve_project_id(args, key)
    if not project_id:
        raise LinearCliError("provide --project-id or --project-name")
    payload = {
        "query": "mutation ProjectArchive($id: String!) { projectDelete(id: $id) { success entity { id name url archivedAt } } }",
        "variables": {"id": project_id},
    }
    response = call_linear(payload, key=key, command="project archive", source=args.source)
    print_json(response, args.pretty)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Call Linear GraphQL without exposing LINEAR_API_KEY")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON response")
    sub = parser.add_subparsers(dest="command")

    raw = sub.add_parser("raw", help="Run a raw GraphQL query/mutation")
    raw.add_argument("--query", help="GraphQL query/mutation string")
    raw.add_argument("--variables", help="JSON variables object for --query")
    raw.add_argument("--file", help="JSON payload file with query and optional variables")
    raw.add_argument("--source", help="Audit source context for mutations")
    raw.set_defaults(func=handle_raw)

    viewer = sub.add_parser("viewer", help="Show authenticated Linear viewer")
    viewer.set_defaults(func=handle_viewer)

    teams = sub.add_parser("team-list", help="List Linear teams")
    teams.add_argument("--limit", type=int, default=50)
    teams.set_defaults(func=handle_team_list)

    issue_list = sub.add_parser("issue-list", help="List/search issues")
    issue_list.add_argument("--limit", type=int, default=20)
    issue_list.add_argument("--team-key")
    issue_list.add_argument("--project-name")
    issue_list.add_argument("--state")
    issue_list.add_argument("--query-text", help="Case-insensitive title/description contains search")
    issue_list.set_defaults(func=handle_issue_list)

    issue_create = sub.add_parser("issue-create", help="Create an issue, optionally idempotently")
    team_selector_args(issue_create, required=True)
    issue_create.add_argument("--title", required=True)
    issue_create.add_argument("--description")
    issue_create.add_argument("--priority", choices=sorted(PRIORITY_MAP), help="Priority label")
    project_selector_args(issue_create)
    issue_create.add_argument("--assignee-id")
    issue_create.add_argument("--label-id", action="append", help="Issue label UUID; repeatable")
    issue_create.add_argument("--if-missing", action="store_true", help="Return existing issue when title/team/project matches")
    issue_create.add_argument("--key-identifier", help="Idempotency key: existing issue identifier to return instead of creating")
    issue_create.add_argument("--source", help="Audit source context")
    issue_create.set_defaults(func=handle_issue_create)

    issue_lookup = sub.add_parser("issue-lookup", help="Lookup issue by UUID or identifier")
    issue_selector_args(issue_lookup, required=True)
    issue_lookup.set_defaults(func=handle_issue_lookup)

    comment = sub.add_parser("comment-add", help="Add a comment to an issue")
    issue_selector_args(comment, required=True)
    comment.add_argument("--body", required=True)
    comment.add_argument("--source", help="Source context footer/audit entry")
    comment.add_argument("--no-source-footer", action="store_true", help="Do not append OpenClaw source footer to the comment")
    comment.set_defaults(func=handle_comment_add)

    priority = sub.add_parser("priority-set", help="Set issue priority by label")
    issue_selector_args(priority, required=True)
    priority.add_argument("--priority", required=True, choices=sorted(PRIORITY_MAP))
    priority.add_argument("--source", help="Audit source context")
    priority.set_defaults(func=handle_priority_set)

    bulk = sub.add_parser("bulk-priority-set", help="Set priorities from JSON input")
    bulk.add_argument("--input", required=True, help="JSON file path or '-' for stdin")
    bulk.add_argument("--confirm-bulk", action="store_true", help="Required when updating more than 5 issues")
    bulk.add_argument("--source", help="Audit source context")
    bulk.set_defaults(func=handle_bulk_priority)

    project_lookup = sub.add_parser("project-lookup", help="Lookup project by UUID or exact name")
    project_selector_args(project_lookup, required=True)
    project_lookup.set_defaults(func=handle_project_lookup)

    project_create = sub.add_parser("project-create", help="Create a project, optionally idempotently")
    project_create.add_argument("--name", required=True)
    project_create.add_argument("--description")
    project_create.add_argument("--content")
    team_selector_args(project_create)
    project_create.add_argument("--if-missing", action="store_true", help="Return existing exact-name project instead of creating")
    project_create.add_argument("--source", help="Audit source context")
    project_create.set_defaults(func=handle_project_create)

    issue_archive = sub.add_parser("issue-archive", help="Archive an issue; requires --confirm")
    issue_selector_args(issue_archive, required=True)
    issue_archive.add_argument("--confirm", action="store_true")
    issue_archive.add_argument("--source", help="Audit source context")
    issue_archive.set_defaults(func=handle_issue_archive)

    project_archive = sub.add_parser("project-archive", help="Archive a project; requires --confirm")
    project_selector_args(project_archive, required=True)
    project_archive.add_argument("--confirm", action="store_true")
    project_archive.add_argument("--source", help="Audit source context")
    project_archive.set_defaults(func=handle_project_archive)

    # Backward-compatible raw mode: old callers used top-level --query/--file flags.
    parser.add_argument("--query", help=argparse.SUPPRESS)
    parser.add_argument("--variables", help=argparse.SUPPRESS)
    parser.add_argument("--file", help=argparse.SUPPRESS)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command is None and (args.query or args.file):
            args.command = "raw"
            args.source = None
            return handle_raw(args)
        if args.command is None:
            parser.print_help(sys.stderr)
            return 2
        return args.func(args)
    except LinearApiError as exc:
        print_json(exc.response, getattr(args, "pretty", False))
        return 1
    except LinearCliError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
