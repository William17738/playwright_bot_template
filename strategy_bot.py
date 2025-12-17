"""
Strategy Bot - Main Entry Point
A template for building Playwright-based automation strategies.

This is a TEMPLATE - implement your own business logic.
"""

import sys
import time
import random
import os
from playwright.sync_api import sync_playwright
from typing import TYPE_CHECKING, Optional, Tuple

from config import DEFAULT_TIMEOUT, SECONDS_PER_MINUTE, VIEWPORT_HEIGHT, VIEWPORT_WIDTH

if TYPE_CHECKING:
    from playwright.sync_api import Page
    from bot_core import RecoveryManager

# ================= Constants =================

# Width of divider lines used in console logging.
STRATEGY_LOG_DIVIDER_WIDTH = 50
STARTUP_LOG_DIVIDER_WIDTH = 60

# Delay range (seconds) used when the bot is in a PENDING state.
PENDING_STATE_DELAY_MIN_SECONDS = 2
PENDING_STATE_DELAY_MAX_SECONDS = 5

# Latency sentinel (ms) returned when a network health check fails.
UNKNOWN_LATENCY_MS = -1

# Sleep (seconds) after initial navigation to allow the page to settle.
POST_NAVIGATION_SLEEP_SECONDS = 3

# Backoff (seconds) when network is unhealthy or an unhandled error occurs.
NETWORK_UNHEALTHY_RETRY_SLEEP_SECONDS = 30
UNHANDLED_ERROR_RETRY_SLEEP_SECONDS = 30

# Note: bot_core/proxy_helper imports are intentionally done inside main()
# after loading .env to keep imports side-effect free for test isolation.

# ================= State Machine =================

class BotState:
    """Bot state enumeration"""
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"
    PENDING = "pending"
    ERROR = "error"

def detect_state(page: "Page") -> str:
    """
    Detect current bot state from page.

    IMPLEMENT YOUR OWN STATE DETECTION LOGIC.
    Example: Check for specific elements that indicate state.
    """
    try:
        # Example state detection - customize for your use case
        # if page.locator("#online-indicator").is_visible(timeout=1000):
        #     return BotState.ONLINE
        # if page.locator("#offline-indicator").is_visible(timeout=1000):
        #     return BotState.OFFLINE

        return BotState.UNKNOWN

    except Exception as e:
        print(f"    [State Detection Error] {e}")
        return BotState.ERROR

# ================= Core Actions =================

def execute_action_a(page: "Page", recovery_manager: Optional["RecoveryManager"] = None) -> bool:
    """
    Execute primary action (e.g., go online).

    IMPLEMENT YOUR OWN ACTION LOGIC.
    """
    print("    [Action] Executing action A...")

    try:
        # Example: Find and click a button
        # btn = page.locator("#action-a-button")
        # if btn.is_visible():
        #     safe_click(page, btn, "Action A Button")
        #     human_delay(0.5, 1.5)
        #     return True

        # Placeholder - implement your logic
        print("    [Action A] Not implemented - add your logic here")
        return True

    except Exception as e:
        print(f"    [Action A Error] {e}")
        if recovery_manager:
            recovery_manager.attempt_recovery(page, str(e))
        return False

def execute_action_b(page: "Page", recovery_manager: Optional["RecoveryManager"] = None) -> bool:
    """
    Execute secondary action (e.g., go offline).

    IMPLEMENT YOUR OWN ACTION LOGIC.
    """
    print("    [Action] Executing action B...")

    try:
        # Placeholder - implement your logic
        print("    [Action B] Not implemented - add your logic here")
        return True

    except Exception as e:
        print(f"    [Action B Error] {e}")
        if recovery_manager:
            recovery_manager.attempt_recovery(page, str(e))
        return False

# ================= Strategy Logic =================

def run_strategy(page: "Page", recovery_manager: "RecoveryManager") -> None:
    """
    Main strategy logic - decides what action to take based on state.

    IMPLEMENT YOUR OWN STRATEGY HERE.
    """
    print("\n" + "=" * STRATEGY_LOG_DIVIDER_WIDTH)
    print(f"[Strategy] Running at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Check remote control
    if check_remote_control(page):
        print("[Strategy] Remote control triggered immediate run")

    # Detect current state
    state = detect_state(page)
    print(f"[Strategy] Current state: {state}")

    # Execute strategy based on state
    if state == BotState.ONLINE:
        print("[Strategy] Already online, monitoring...")
        # Add your monitoring logic here

    elif state == BotState.OFFLINE:
        print("[Strategy] Offline, attempting to go online...")
        if execute_action_a(page, recovery_manager):
            recovery_manager.reset_counters()

    elif state == BotState.PENDING:
        print("[Strategy] Pending state, waiting...")
        human_delay(PENDING_STATE_DELAY_MIN_SECONDS, PENDING_STATE_DELAY_MAX_SECONDS)

    elif state == BotState.ERROR:
        print("[Strategy] Error state, attempting recovery...")
        recovery_manager.attempt_recovery(page, "Error state detected")

    else:
        print("[Strategy] Unknown state, skipping...")

    # Update monitor screenshot
    update_monitor(page)

# ================= Network Health Check =================

def check_network_health() -> Tuple[bool, int]:
    """
    Check network connectivity using proxy helper.
    Returns: (is_healthy, latency_ms)
    """
    try:
        node_name, latency, is_healthy = proxy_helper.check_health()
        print(f"[Network] Node: {node_name}, Latency: {latency}ms, Healthy: {is_healthy}")
        return is_healthy, latency
    except Exception as e:
        print(f"[Network] Health check failed: {e}")
        return False, UNKNOWN_LATENCY_MS

def ensure_network_health() -> bool:
    """Ensure network is healthy, attempt fix if not"""
    is_healthy, latency = check_network_health()

    if not is_healthy:
        print("[Network] Unhealthy, attempting to fix...")
        try:
            if proxy_helper.try_fix_network():
                print("[Network] Fixed successfully")
                return True
            else:
                print("[Network] Fix failed")
                return False
        except Exception as e:
            print(f"[Network] Fix error: {e}")
            return False

    return True

# ================= Main Loop =================

def main() -> None:
    """Main entry point"""
    from dotenv import load_dotenv
    load_dotenv()

    global DualLogger
    global RecoveryManager
    global TARGET_URL
    global check_remote_control
    global get_wait_time
    global human_delay
    global is_login_required
    global update_monitor
    global wait_for_login
    global proxy_helper

    # Import core utilities after environment is loaded
    from bot_core import (
        DualLogger,
        RecoveryManager,
        TARGET_URL,
        check_remote_control,
        get_wait_time,
        human_delay,
        is_login_required,
        update_monitor,
        wait_for_login,
    )
    import proxy_helper

    # Setup logging
    sys.stdout = DualLogger("bot_log.txt")
    sys.stderr = sys.stdout

    print("=" * STARTUP_LOG_DIVIDER_WIDTH)
    print("Strategy Bot - Starting")
    print("=" * STARTUP_LOG_DIVIDER_WIDTH)

    # Initialize recovery manager
    recovery_manager = RecoveryManager()

    with sync_playwright() as p:
        # Browser configuration
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
            ]
        )

        # Create context with persistent state
        context = browser.new_context(
            viewport={'width': VIEWPORT_WIDTH, 'height': VIEWPORT_HEIGHT},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        page = context.new_page()

        try:
            # Navigate to target
            print(f"[Init] Navigating to {TARGET_URL}")
            page.goto(TARGET_URL, timeout=DEFAULT_TIMEOUT)
            time.sleep(POST_NAVIGATION_SLEEP_SECONDS)

            # Check if login required
            if is_login_required(page):
                if not wait_for_login(page):
                    print("[Error] Login timeout")
                    return

            # Main loop
            while True:
                try:
                    # Check network health periodically
                    if not ensure_network_health():
                        print("[Warning] Network unhealthy, waiting...")
                        time.sleep(NETWORK_UNHEALTHY_RETRY_SLEEP_SECONDS)
                        continue

                    # Run strategy
                    run_strategy(page, recovery_manager)

                    # Wait before next iteration
                    wait_seconds = get_wait_time()
                    print(f"\n[Sleep] Waiting {wait_seconds/SECONDS_PER_MINUTE:.1f} minutes...")
                    time.sleep(wait_seconds)

                except KeyboardInterrupt:
                    print("\n[Exit] User interrupted")
                    break
                except Exception as e:
                    print(f"\n[Error] {e}")
                    recovery_manager.attempt_recovery(page, str(e))
                    time.sleep(UNHANDLED_ERROR_RETRY_SLEEP_SECONDS)

        finally:
            browser.close()

if __name__ == "__main__":
    main()
