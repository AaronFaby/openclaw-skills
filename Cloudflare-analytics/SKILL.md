---
name: cloudflare-analytics
description: Pull Cloudflare Zone analytics (requests, visitors, bandwidth, cache, TLS, threats, and breakdowns) via GraphQL API. Use when the user asks for website traffic stats, analytics data, or performance metrics for sites hosted on Cloudflare.
---

# Cloudflare Analytics

Pull website analytics from Cloudflare's GraphQL API for any zone you have access to.

## Quick Start

```bash
python3 scripts/get_analytics.py
```

Default behavior is now a **full report for the last 24 hours**.

## Configuration

Create `~/.openclaw/workspace/.secrets/cloudflare.env`:

```bash
CLOUDFLARE_API_KEY=your_api_token_here
CLOUDFLARE_ZONE_ID=your_zone_id_here
```

**Getting credentials:**
1. Log into Cloudflare Dashboard
2. Go to your domain → Overview → Zone ID (copy this)
3. Go to My Profile → API Tokens → Create Token
4. Use "Read Analytics" template or create custom token with `Analytics:Read` permission
5. Copy the token

## Usage

**Default full report (last 24h):**
```bash
python3 scripts/get_analytics.py
```

**Custom rolling window (hours):**
```bash
python3 scripts/get_analytics.py --hours 72
```

**Custom absolute window (ISO timestamps):**
```bash
python3 scripts/get_analytics.py --since 2026-03-01T00:00:00Z --until 2026-03-02T00:00:00Z
```

**Backwards-compatible day window:**
```bash
python3 scripts/get_analytics.py --days 7
```

**JSON output (raw sections + warnings):**
```bash
python3 scripts/get_analytics.py --format json
```

**CSV output (legacy hourly core metrics):**
```bash
python3 scripts/get_analytics.py --format csv
```

**Override credentials:**
```bash
python3 scripts/get_analytics.py --api-key TOKEN --zone-id ZONE
```

## Output Formats

**Human (default):**
- Discord-friendly bullet sections
- Overview totals
- Cache/TLS/threat metrics when available
- Top countries breakdown
- Status-code breakdown
- Peak-hour summary
- Notes section for unavailable fields/queries

**JSON:**
- Full structured report bundle:
  - window
  - sections
  - warnings

**CSV:**
- Legacy-compatible hourly export:
```
datetime_utc,visitors,pageviews,requests,bandwidth_mb,cached_kb
2026-03-02T14:00:00Z,12,15,122,3.4,210
```

## Metrics Provided

The script attempts to collect as many available zone metrics as your plan/API schema allows:

- **Traffic core:** requests, page views, unique visitors, bandwidth, cached bandwidth
- **Cache detail:** cached requests (when available)
- **TLS detail:** encrypted requests + encrypted bandwidth (when available)
- **Security detail:** threats (when available)
- **Breakdowns:** top countries, response status codes, peak traffic hour

Unavailable fields are handled gracefully and listed under **Notes**.

## Common Use Cases

**Daily briefing analytics (default 24h):**
```python
import subprocess
result = subprocess.run(
    ["python3", "scripts/get_analytics.py"],
    capture_output=True, text=True
)
print(result.stdout)
```

**Weekly summary:**
```bash
python3 scripts/get_analytics.py --days 7
```

**Export for analysis:**
```bash
python3 scripts/get_analytics.py --hours 168 --format csv > analytics.csv
```

## Troubleshooting

**"Authentication error":**
- Check API token has `Analytics:Read` permission
- Verify token is not expired
- Ensure zone ID is correct

**"No data available":**
- Zone might be too new (analytics can lag)
- Check time window is valid and not in the future
- Verify zone is active

**Some sections missing / warnings shown:**
- Certain fields and dimensions vary by Cloudflare plan, account features, or schema changes
- The script keeps the report running with partial data and records section-level warnings

**Import errors:**
```bash
pip3 install requests
```%     
