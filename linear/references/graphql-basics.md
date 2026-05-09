# Linear GraphQL basics

Use this reference only when the canned CLI commands in `SKILL.md` do not cover the requested operation.

Endpoint: `https://api.linear.app/graphql`

Authentication for personal API keys: `Authorization: <LINEAR_API_KEY>`; do not use `Bearer` for personal keys. Prefer the wrapper so the key never enters context:

```bash
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py --pretty raw \
  --query 'query Me { viewer { id name email } }'
```

Backward-compatible top-level raw mode also works:

```bash
/home/netwatch/.openclaw/skills/linear/scripts/linear_graphql.py --pretty \
  --query 'query Me { viewer { id name email } }'
```

Useful queries:

```graphql
query Me { viewer { id name email } }
```

```graphql
query Teams { teams { nodes { id key name } } }
```

```graphql
query RecentIssues($first: Int!) {
  issues(first: $first, orderBy: updatedAt) {
    nodes { id identifier title url state { name } assignee { name } updatedAt }
  }
}
```

Create issue:

```graphql
mutation IssueCreate($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success
    issue { id identifier title url }
  }
}
```

Update issue:

```graphql
mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) {
    success
    issue { id identifier title url state { name } assignee { name } }
  }
}
```

Create comment:

```graphql
mutation CommentCreate($input: CommentCreateInput!) {
  commentCreate(input: $input) {
    success
    comment { id url body }
  }
}
```

Project create:

```graphql
mutation ProjectCreate($input: ProjectCreateInput!) {
  projectCreate(input: $input) {
    success
    project { id name url state teams { nodes { id key name } } }
  }
}
```

Always check `errors`. GraphQL can return HTTP 200 with partial failure.

## Wrapper guardrails still apply

- Prefer canned commands before raw GraphQL.
- Include non-secret source context in writes when practical.
- Ask Aaron before destructive/bulk/high-blast-radius operations.
- Never print authorization headers or secret file contents.
