"""
Demo Strategy - Minimal Working Example

This demo uses httpbin.org to demonstrate:
- State detection
- Action execution
- Recovery handling

Run: python demo_strategy.py
"""

import os
import sys
import time
import random
from enum import Enum
from playwright.sync_api import sync_playwright, Page
from typing import Optional

# Import from bot_core
from bot_core import (
    DualLogger,
    RecoveryManager,
    safe_click,
    wait_for_element_stable,
    human_delay,
)

# =============================================================================
# Configuration
# =============================================================================

TARGET_URL = "https://httpbin.org/"
LOG_FILE = "demo_log.txt"

# =============================================================================
# State Definition
# =============================================================================

class DemoState(Enum):
    """
    Define all possible states your bot can detect.
    Each state corresponds to a specific page or UI condition.
    """
    UNKNOWN = "unknown"         # Cannot determine state
    HOME = "home"               # On homepage
    FORMS_PAGE = "forms"        # On forms page
    RESPONSE_PAGE = "response"  # Viewing JSON response
    ERROR = "error"             # Error state


# =============================================================================
# State Detection
# =============================================================================

def detect_state(page: Page) -> DemoState:
    """
    Detect current page state by checking visible elements.

    This is the CORE of state machine pattern:
    - Check specific elements that indicate each state
    - Return UNKNOWN if cannot determine
    - Keep detection logic simple and fast
    """
    try:
        url = page.url

        # Check URL patterns first (fast path)
        if "httpbin.org/forms" in url:
            return DemoState.FORMS_PAGE

        if "httpbin.org/post" in url or "httpbin.org/get" in url:
            # Check if we see JSON response
            if page.locator("pre").is_visible(timeout=1000):
                return DemoState.RESPONSE_PAGE

        # Check homepage elements
        if page.locator("text=httpbin").first.is_visible(timeout=1000):
            # Look for the forms link to confirm we're on home
            if page.locator("a[href='/forms/post']").is_visible(timeout=500):
                return DemoState.HOME

        return DemoState.UNKNOWN

    except Exception as e:
        print(f"[State Detection Error] {e}")
        return DemoState.UNKNOWN


# =============================================================================
# Actions
# =============================================================================

def action_go_to_forms(page: Page, recovery_manager: Optional[RecoveryManager] = None) -> bool:
    """
    Action: Navigate from HOME to FORMS page.
    """
    print("[Action] Navigating to forms page...")

    try:
        # Find and click the forms link
        forms_link = page.locator("a[href='/forms/post']")

        if not forms_link.is_visible(timeout=3000):
            print("[Action] Forms link not found")
            return False

        # Use safe_click for reliable clicking
        if safe_click(page, forms_link, "Forms Link"):
            # Wait for navigation
            page.wait_for_load_state("networkidle", timeout=10000)
            human_delay(0.5, 1.0)
            return True

        return False

    except Exception as e:
        print(f"[Action Error] {e}")
        return False


def action_submit_form(page: Page, recovery_manager: Optional[RecoveryManager] = None) -> bool:
    """
    Action: Fill and submit the form on FORMS page.
    """
    print("[Action] Filling and submitting form...")

    try:
        # Fill form fields
        customer_input = page.locator("input[name='custname']")
        if customer_input.is_visible(timeout=2000):
            customer_input.fill(f"Demo User {random.randint(100, 999)}")
            human_delay(0.3, 0.6)

        # Select topping (checkbox)
        cheese_checkbox = page.locator("input[value='cheese']")
        if cheese_checkbox.is_visible(timeout=1000):
            if not cheese_checkbox.is_checked():
                cheese_checkbox.click()
                human_delay(0.2, 0.4)

        # Fill comments
        comments = page.locator("textarea[name='comments']")
        if comments.is_visible(timeout=1000):
            comments.fill("This is a demo submission from Strategy Bot Template")
            human_delay(0.3, 0.5)

        # Submit form
        submit_btn = page.locator("button[type='submit']")
        if safe_click(page, submit_btn, "Submit Button"):
            page.wait_for_load_state("networkidle", timeout=10000)
            human_delay(0.5, 1.0)
            return True

        return False

    except Exception as e:
        print(f"[Action Error] {e}")
        return False


def action_go_home(page: Page, recovery_manager: Optional[RecoveryManager] = None) -> bool:
    """
    Action: Return to homepage.
    """
    print("[Action] Returning to homepage...")

    try:
        page.goto(TARGET_URL, timeout=15000)
        page.wait_for_load_state("networkidle", timeout=10000)
        human_delay(0.5, 1.0)
        return True

    except Exception as e:
        print(f"[Action Error] {e}")
        return False


# =============================================================================
# Strategy Logic
# =============================================================================

def run_strategy(page: Page, recovery_manager: RecoveryManager, logger: DualLogger) -> bool:
    """
    Main strategy loop - the brain of your bot.

    Pattern:
    1. Detect current state
    2. Decide action based on state
    3. Execute action
    4. Verify result
    """

    # Step 1: Detect state
    state = detect_state(page)
    logger.log(f"[Strategy] Current state: {state.value}")

    # Step 2 & 3: State-based action
    if state == DemoState.HOME:
        # From home, go to forms
        logger.log("[Strategy] On homepage -> Going to forms")
        success = action_go_to_forms(page, recovery_manager)

    elif state == DemoState.FORMS_PAGE:
        # On forms page, submit form
        logger.log("[Strategy] On forms page -> Submitting form")
        success = action_submit_form(page, recovery_manager)

    elif state == DemoState.RESPONSE_PAGE:
        # Saw response, go back home
        logger.log("[Strategy] Saw response -> Returning home")
        success = action_go_home(page, recovery_manager)

    elif state == DemoState.UNKNOWN:
        # Unknown state, try to recover
        logger.log("[Strategy] Unknown state -> Attempting recovery")
        success = action_go_home(page, recovery_manager)

    else:
        logger.log(f"[Strategy] Unhandled state: {state.value}")
        success = False

    # Step 4: Verify & report
    if success:
        recovery_manager.reset_counters()
        logger.log("[Strategy] Action completed successfully")
    else:
        logger.log("[Strategy] Action failed")

    return success


# =============================================================================
# Main Entry Point
# =============================================================================

def main() -> None:
    """Demo entry point"""
    from dotenv import load_dotenv
    load_dotenv()

    print("=" * 60)
    print("Strategy Bot Template - Demo")
    print("Target: httpbin.org")
    print("=" * 60)

    # Initialize
    logger = DualLogger(LOG_FILE)
    recovery_manager = RecoveryManager()

    with sync_playwright() as p:
        # Launch browser (visible for demo)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()

        try:
            # Navigate to target
            logger.log(f"[Demo] Opening {TARGET_URL}")
            page.goto(TARGET_URL, timeout=30000)
            page.wait_for_load_state("networkidle")

            # Run demo cycles
            cycles = 3
            for i in range(cycles):
                print(f"\n{'='*40}")
                print(f"Cycle {i+1}/{cycles}")
                print(f"{'='*40}")

                run_strategy(page, recovery_manager, logger)

                # Wait between cycles
                wait_time = random.uniform(3, 8)
                logger.log(f"[Demo] Waiting {wait_time:.1f}s before next cycle...")
                time.sleep(wait_time)

            print("\n" + "=" * 60)
            print("Demo completed! Check demo_log.txt for logs.")
            print("=" * 60)

        except KeyboardInterrupt:
            logger.log("[Demo] Interrupted by user")
        except Exception as e:
            logger.log(f"[Demo] Error: {e}")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
