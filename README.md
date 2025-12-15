# Playwright Bot Template

> A production-grade framework for building **long-running** Playwright automation bots that need to stay alive under flaky pages and unstable networks.

## Why This Project?

| Problem | Solution |
|---------|----------|
| Bot gets stuck but doesn't crash | Multi-tier recovery (page → session → process) |
| Network becomes unstable | Proxy health monitoring + auto-switching |
| Need to pause/resume remotely | File-based control interface |
| Hard to debug failures | Structured logging + email alerts |
| Starting from scratch every time | Reusable framework with clear extension points |

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                        Your Strategy                          │
│       ┌──────────────┐           ┌────────────────┐           │
│       │ detect_state │ ────────► │ execute_action │           │
│       └──────────────┘           └────────────────┘           │
└─────────────────────────────┬─────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────┐
│                     Bot Core Framework                        │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐         │
│   │  Recovery   │   │  Safe Ops   │   │   Logging   │         │
│   │  Manager    │   │  & Waits    │   │  & Alerts   │         │
│   │ (A → B → C) │   │             │   │             │         │
│   └─────────────┘   └─────────────┘   └─────────────┘         │
└─────────────────────────────┬─────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────┐
│                   Infrastructure Layer                        │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐         │
│   │   Proxy     │   │  Control    │   │    Email    │         │
│   │   Health    │   │   Files     │   │    SMTP     │         │
│   │  (API call) │   │  pause/cmd  │   │             │         │
│   └─────────────┘   └─────────────┘   └─────────────┘         │
└───────────────────────────────────────────────────────────────┘
```

## Quick Start

**Requirements:** Python 3.8+ (tested on 3.10, 3.11)

```bash
# 1. Clone and install
git clone https://github.com/William17738/playwright_bot_template.git
cd playwright_bot_template
pip install -r requirements.txt
playwright install chromium

# 2. Run the demo (see it work in 3 minutes)
python demo_strategy.py

# 3. Configure your environment
cp .env.example .env
# Edit .env with your settings

# 4. Implement your logic in strategy_bot.py, then run
python strategy_bot.py
```

## Project Structure

```
├── strategy_bot.py    # Main entry - implement your logic here
├── demo_strategy.py   # Working demo using httpbin.org
├── bot_core.py        # Core framework (recovery, logging, utils)
├── proxy_helper.py    # Network health management
├── .env.example       # Environment variables template
├── ARCHITECTURE.md    # Detailed architecture documentation
└── PROXY_API.md       # Proxy API contract documentation
```

## Implementation Checklist

### Required (must implement)

- [ ] `BotState` enum - Define your states (ONLINE, OFFLINE, etc.)
- [ ] `detect_state(page)` - Return current state from page elements
- [ ] `execute_action_*(page)` - At least one action function

### Recommended

- [ ] `run_strategy(page, recovery_manager)` - Main decision logic
- [ ] `get_wait_time()` / `human_delay()` - Custom timing (or use defaults)

### Optional hooks

- [ ] `on_recovery(level, error)` - Called after recovery attempt
- [ ] `on_state_change(old, new)` - Called on state transitions

## Recovery System

The framework automatically handles failures at three levels:

| Level | Trigger | Action | Max Retries |
|-------|---------|--------|-------------|
| **A** (Page) | Element not found, timeout | Refresh page | 5 |
| **B** (Session) | Level A exhausted, URL mismatch | Navigate to target | 3 |
| **C** (Process) | Level B exhausted, crash | Exit code 2 (restart signal) | - |

**Cooldown:** 30 seconds between recovery attempts to prevent loops.

## Network Health Management

`proxy_helper.py` monitors your proxy via RESTful API:

| Status | Latency | Action |
|--------|---------|--------|
| EXCELLENT | < 300ms | Continue |
| HEALTHY | < 800ms | Continue |
| DEGRADED | < 1500ms | Log warning |
| UNHEALTHY | ≥ 1500ms / timeout | Auto-switch node |

See [PROXY_API.md](PROXY_API.md) for supported proxy clients and API contract.

## Remote Control

Control the bot without SSH/restart:

```bash
# Pause the bot
touch pause.lock
# Bot logs: "[Paused] Waiting for pause.lock removal..."

# Resume
rm pause.lock
# Bot continues from where it stopped

# Send command (implement your handler in check_remote_control)
echo "force_refresh" > command.txt
```

## Design Trade-offs

| Decision | Why |
|----------|-----|
| **File-based control** vs WebSocket | Simpler deployment, no extra port, works across restarts |
| **Three-tier recovery** vs single retry | Matches real failure modes (transient → page issue → system issue) |
| **No built-in CI/tests** | Template flexibility - add what your project needs |
| **Proxy API abstraction** | Works with Clash/V2Ray/any RESTful proxy, not locked to one |
| **Environment variables** | Secrets never in code, easy Docker/cloud deployment |

### Limitations

- **Not an anti-detection tool** - This framework focuses on reliability, not bypassing security measures
- **Best for internal automation** - Designed for monitoring, testing, and workflow automation on systems you own or have permission to access
- **Single browser instance** - Not designed for parallel/distributed scraping at scale

## Troubleshooting

### Proxy API connection refused
```bash
# Check if proxy is running and API is enabled
curl http://127.0.0.1:9090/proxies

# If using Clash Verge, enable External Controller in settings
# Default port: 9090, check your config for actual port
```

### Playwright browser not found
```bash
# Install browser binaries
playwright install chromium

# Or install all browsers
playwright install
```

### Bot stuck in recovery loop
```bash
# Check logs for repeated errors
tail -f bot_log.txt

# Force pause and investigate
touch pause.lock

# Check current state manually
python -c "from bot_core import *; print('Core loaded OK')"
```

### Email alerts not working
```bash
# Test SMTP connection
python -c "
import smtplib
from bot_core import MAIL_HOST, MAIL_PORT
print(f'Connecting to {MAIL_HOST}:{MAIL_PORT}...')
s = smtplib.SMTP_SSL(MAIL_HOST, MAIL_PORT)
print('OK')
"
```

## Use Cases

This framework is suitable for:

- **Monitoring dashboards** - Periodic login and status checks
- **Form automation** - Reliable form filling with recovery
- **Data collection** - Scheduled extraction from authenticated pages
- **Availability testing** - Long-running uptime verification

## Configuration Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `TARGET_URL` | Target website URL | `https://example.com` |
| `PROXY_PORT` | Proxy API port | `9090` |
| `PROXY_SECRET` | Proxy API secret | (empty) |
| `PROXY_MIXED_PORT` | Proxy SOCKS/HTTP port | `7890` |
| `MIN_WAIT` | Min wait between cycles (min) | `5` |
| `MAX_WAIT` | Max wait between cycles (min) | `45` |
| `MAIL_HOST` | SMTP server | `smtp.example.com` |
| `MAIL_PORT` | SMTP port | `465` |
| `MAIL_USER` | SMTP username | (empty) |
| `MAIL_PASS` | SMTP password | (empty) |
| `MAIL_RECEIVER` | Alert recipient | (empty) |

## License

MIT License - see [LICENSE](LICENSE) file.

## Contributing

Issues and PRs welcome. Please include:
- Python version and OS
- Relevant log output
- Steps to reproduce (if bug)
