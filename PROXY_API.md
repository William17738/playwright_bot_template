# Proxy API Contract

This document describes the RESTful API endpoints that `proxy_helper.py` expects from your proxy client.

## Supported Proxy Clients

- Clash / Clash Premium
- Clash Verge / Clash Verge Rev
- Clash Meta (mihomo)
- V2Ray (with API enabled)
- Any proxy with compatible RESTful API

## Configuration

```bash
# .env
PROXY_PORT=9090          # API port (Clash default: 9090)
PROXY_SECRET=your-secret # API secret (if configured)
PROXY_MIXED_PORT=7890    # SOCKS5/HTTP proxy port
```

## Required Endpoints

### 1. Get Proxies List

```
GET /proxies
Authorization: Bearer {secret}
```

**Response:**
```json
{
  "proxies": {
    "GLOBAL": {
      "name": "GLOBAL",
      "type": "Selector",
      "now": "proxy-node-1",
      "all": ["proxy-node-1", "proxy-node-2", "DIRECT"]
    },
    "proxy-node-1": {
      "name": "proxy-node-1",
      "type": "Vmess",
      "history": [
        {"delay": 150}
      ]
    }
  }
}
```

**Used by:** `get_all_proxies()`, node selection

---

### 2. Get Proxy Delay

```
GET /proxies/{name}/delay?timeout=5000&url=http://www.gstatic.com/generate_204
Authorization: Bearer {secret}
```

**Response (success):**
```json
{
  "delay": 185
}
```

**Response (timeout):**
```json
{
  "message": "timeout"
}
```

**Used by:** `check_health()`, latency testing

---

### 3. Switch Proxy Node

```
PUT /proxies/{group}/
Authorization: Bearer {secret}
Content-Type: application/json

{
  "name": "proxy-node-2"
}
```

**Response:** `204 No Content`

**Used by:** `switch_to_next_node()`, auto-failover

---

### 4. Reload Config (Optional)

```
PUT /configs?force=true
Authorization: Bearer {secret}
Content-Type: application/json

{
  "path": "/path/to/config.yaml"
}
```

**Response:** `204 No Content`

**Used by:** `update_subscription()`, config refresh

---

## Health Status Thresholds

| Status | Latency | Description |
|--------|---------|-------------|
| EXCELLENT | < 300ms | Optimal connection |
| HEALTHY | < 800ms | Normal operation |
| DEGRADED | < 1500ms | Usable but slow |
| UNHEALTHY | ≥ 1500ms or timeout | Needs attention |

## Request Headers

All requests require:

```http
Authorization: Bearer {PROXY_SECRET}
Content-Type: application/json
```

If `PROXY_SECRET` is empty, omit the Authorization header.

## Error Handling

| HTTP Code | Meaning | Action |
|-----------|---------|--------|
| 200/204 | Success | Continue |
| 401 | Unauthorized | Check PROXY_SECRET |
| 404 | Not found | Check endpoint/proxy name |
| 500 | Server error | Retry or restart proxy |

## Example: Clash Verge Configuration

Enable API in Clash Verge settings:

1. Settings → External Controller
2. Set port (default: 9090)
3. Set secret (optional but recommended)

```yaml
# clash config
external-controller: 127.0.0.1:9090
secret: "your-secret-here"
mixed-port: 7890
```

## Testing API Connection

```bash
# Test connection (no auth)
curl http://127.0.0.1:9090/proxies

# Test with auth
curl -H "Authorization: Bearer your-secret" http://127.0.0.1:9090/proxies

# Test delay
curl "http://127.0.0.1:9090/proxies/proxy-node-1/delay?timeout=5000&url=http://www.gstatic.com/generate_204"
```

## Code Example

```python
from proxy_helper import check_health, try_fix_network

# Check current status
status, latency, is_healthy = check_health()
print(f"Status: {status}, Latency: {latency}ms")

# Auto-fix if unhealthy
if not is_healthy:
    if try_fix_network():
        print("Network recovered")
    else:
        print("Manual intervention needed")
```
