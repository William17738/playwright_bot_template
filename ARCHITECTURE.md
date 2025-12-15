# Strategy Bot Architecture

A modular framework for building Playwright-based automation bots with network health management and multi-level recovery.

## Overview

This project provides a template for creating robust browser automation bots. It includes:

- **State Machine Pattern**: Clean state detection and action execution
- **Multi-Level Recovery**: Page, session, and process level error handling
- **Network Health Management**: Proxy health monitoring and automatic failover
- **Remote Control**: File-based control interface for pause/resume operations

## Components

| File | Purpose |
|------|---------|
| `strategy_bot.py` | Main entry point - implements your business logic |
| `bot_core.py` | Core framework - utilities, recovery, logging |
| `proxy_helper.py` | Network management - health checks, node switching |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     strategy_bot.py                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ State       │  │ Actions     │  │ Main Loop           │  │
│  │ Detection   │──│ (A, B, ...) │──│ - Network check     │  │
│  │             │  │             │  │ - Strategy run      │  │
│  └─────────────┘  └─────────────┘  │ - Wait cycle        │  │
│                                     └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       bot_core.py                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Recovery    │  │ Page Ops    │  │ Utilities           │  │
│  │ Manager     │  │ - safe_click│  │ - Logging           │  │
│  │ - Level A   │  │ - find_btn  │  │ - Email alerts      │  │
│  │ - Level B   │  │ - wait      │  │ - Remote control    │  │
│  │ - Level C   │  │             │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     proxy_helper.py                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Health      │  │ Node        │  │ Subscription        │  │
│  │ Check       │  │ Switching   │  │ Update              │  │
│  │ - Multi-URL │  │ - Auto      │  │ - Config reload     │  │
│  │ - Latency   │  │   failover  │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Recovery System

The framework implements a three-level recovery system:

### Level A - Page Recovery
- **Trigger**: Element not found, timeout, minor errors
- **Action**: Page refresh, wait for stability
- **Max retries**: 5

### Level B - Session Recovery
- **Trigger**: Level A exhausted, URL mismatch, page crash
- **Action**: Navigate to target URL, check login state
- **Max retries**: 3

### Level C - Process Recovery
- **Trigger**: Level B exhausted, browser crash
- **Action**: Send alert email, exit with code 2 (restart signal)

## State Machine Pattern

Implement your state detection in `strategy_bot.py`:

```python
class BotState:
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"
    PENDING = "pending"
    ERROR = "error"

def detect_state(page):
    # Check visible elements to determine state
    if page.locator("#online-indicator").is_visible():
        return BotState.ONLINE
    # ... more detection logic
    return BotState.UNKNOWN
```

## Network Health Management

`proxy_helper.py` provides:

1. **Multi-point testing**: Tests against multiple URLs for reliability
2. **Health status levels**: EXCELLENT (<300ms), HEALTHY (<800ms), DEGRADED (<1500ms), UNHEALTHY
3. **Auto-failover**: Automatically switches to healthy nodes when current fails
4. **Subscription update**: Optional config refresh from subscription URL

## Configuration

All sensitive configuration via environment variables:

```bash
# Target site
TARGET_URL=https://example.com

# Email alerts
MAIL_HOST=smtp.example.com
MAIL_PORT=465
MAIL_USER=your_email
MAIL_PASS=your_password
MAIL_RECEIVER=alert_recipient

# Proxy API
PROXY_PORT=9090
PROXY_SECRET=your_api_secret
PROXY_MIXED_PORT=7890

# Timing
MIN_WAIT=5
MAX_WAIT=45
```

## Usage

1. Copy `.env.example` to `.env` and configure
2. Implement your state detection in `detect_state()`
3. Implement your actions in `execute_action_a()`, `execute_action_b()`
4. Customize `run_strategy()` with your business logic
5. Run: `python strategy_bot.py`

## Remote Control

The bot supports file-based remote control:

- **pause.lock**: Create this file to pause the bot
- **command.txt**: Write commands to this file for execution

## Requirements

- Python 3.8+
- Playwright
- A compatible proxy client (Clash, Clash Verge, V2Ray, etc.) with RESTful API

## License

MIT License - See LICENSE file for details.
