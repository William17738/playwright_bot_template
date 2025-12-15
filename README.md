# Strategy Bot Template

A modular framework for building robust Playwright-based automation bots with network health management and multi-level recovery.

## Features

- **State Machine Pattern** - Clean separation of state detection and action execution
- **Multi-Level Recovery** - Automatic error handling at page, session, and process levels
- **Network Health Management** - Proxy health monitoring with automatic node failover
- **Remote Control** - File-based interface for pause/resume operations
- **Email Alerts** - Notifications for login requests and critical errors
- **Environment Configuration** - All sensitive data via environment variables

## Quick Start

### 1. Install Dependencies

```bash
pip install playwright
playwright install chromium
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Implement Your Logic

Edit `strategy_bot.py`:

```python
def detect_state(page):
    """Detect current state from page elements"""
    if page.locator("#online-indicator").is_visible(timeout=1000):
        return BotState.ONLINE
    if page.locator("#offline-indicator").is_visible(timeout=1000):
        return BotState.OFFLINE
    return BotState.UNKNOWN

def execute_action_a(page, recovery_manager=None):
    """Your primary action (e.g., go online)"""
    btn = page.locator("#action-button")
    if safe_click(page, btn, "Action Button"):
        return True
    return False
```

### 4. Run

```bash
python strategy_bot.py
```

## Project Structure

```
├── strategy_bot.py    # Main entry point - implement your logic here
├── bot_core.py        # Core framework utilities
├── proxy_helper.py    # Network health management
├── .env.example       # Environment variable template
├── requirements.txt   # Python dependencies
└── ARCHITECTURE.md    # Detailed architecture documentation
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `TARGET_URL` | Target website URL | `https://example.com` |
| `PROXY_PORT` | Proxy API port | `9090` |
| `PROXY_SECRET` | Proxy API secret | (empty) |
| `PROXY_MIXED_PORT` | Proxy SOCKS/HTTP port | `7890` |
| `MIN_WAIT` | Minimum wait between cycles (minutes) | `5` |
| `MAX_WAIT` | Maximum wait between cycles (minutes) | `45` |
| `MAIL_HOST` | SMTP server host | `smtp.example.com` |
| `MAIL_PORT` | SMTP server port | `465` |
| `MAIL_USER` | SMTP username | (empty) |
| `MAIL_PASS` | SMTP password | (empty) |
| `MAIL_RECEIVER` | Alert recipient email | (empty) |

## Recovery System

The framework implements automatic error recovery:

| Level | Trigger | Action |
|-------|---------|--------|
| **A** | Element not found, timeout | Page refresh |
| **B** | Level A exhausted, URL mismatch | Navigate to target URL |
| **C** | Level B exhausted, browser crash | Exit with restart signal |

## Network Health

`proxy_helper.py` monitors proxy health via RESTful API (compatible with Clash, Clash Verge, V2Ray, etc.):

- Multi-URL latency testing
- Health status classification (Excellent/Healthy/Degraded/Unhealthy)
- Automatic node switching on failure
- Optional subscription config updates

## Remote Control

Control the bot via files in the working directory:

| File | Effect |
|------|--------|
| `pause.lock` | Pause bot execution until file is removed |
| `command.txt` | Execute custom commands (implement in `check_remote_control()`) |

## Requirements

- Python 3.8+
- Playwright
- Compatible proxy client with RESTful API (optional)

## License

MIT License
