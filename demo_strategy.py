"""
Demo Strategy - Minimal Working Example
演示如何使用状态机模式构建自动化机器人

This demo uses httpbin.org to demonstrate:
- State detection (检测页面状态)
- Action execution (执行操作)
- Recovery handling (错误恢复)

Run: python demo_strategy.py
"""

import os
import sys
import time
import random
from enum import Enum
from playwright.sync_api import sync_playwright, Page

# Import from bot_core
from bot_core import (
    DualLogger,
    RecoveryManager,
    safe_click,
    wait_for_element_stable,
    get_wait_time,
    human_delay,
)

# =============================================================================
# Configuration
# =============================================================================

TARGET_URL = "https://httpbin.org/"
LOG_FILE = "demo_log.txt"

# =============================================================================
# State Definition (状态定义)
# =============================================================================

class DemoState(Enum):
    """
    Define all possible states your bot can detect.
    根据页面元素定义所有可能的状态
    """
    UNKNOWN = "unknown"       # Cannot determine state (无法判断)
    HOME = "home"             # On homepage (在首页)
    FORMS_PAGE = "forms"      # On forms page (在表单页)
    RESPONSE_PAGE = "response"  # Viewing response (查看响应)
    ERROR = "error"           # Error state (错误状态)


# =============================================================================
# State Detection (状态检测)
# =============================================================================

def detect_state(page: Page) -> DemoState:
    """
    Detect current page state by checking visible elements.
    通过检查可见元素判断当前页面状态

    This is the CORE of state machine pattern:
    - Check specific elements that indicate each state
    - Return UNKNOWN if cannot determine
    - Keep detection logic simple and fast
    """
    try:
        url = page.url

        # Check URL patterns first (快速判断)
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
# Actions (操作执行)
# =============================================================================

def action_go_to_forms(page: Page, recovery_manager: RecoveryManager = None) -> bool:
    """
    Action: Navigate from HOME to FORMS page
    操作：从首页进入表单页
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
        if recovery_manager:
            recovery_manager.record_error("ACTION_ERROR")
        return False


def action_submit_form(page: Page, recovery_manager: RecoveryManager = None) -> bool:
    """
    Action: Fill and submit the form on FORMS page
    操作：填写并提交表单
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
        if recovery_manager:
            recovery_manager.record_error("ACTION_ERROR")
        return False


def action_go_home(page: Page, recovery_manager: RecoveryManager = None) -> bool:
    """
    Action: Return to homepage
    操作：返回首页
    """
    print("[Action] Returning to homepage...")

    try:
        page.goto(TARGET_URL, timeout=15000)
        page.wait_for_load_state("networkidle", timeout=10000)
        human_delay(0.5, 1.0)
        return True

    except Exception as e:
        print(f"[Action Error] {e}")
        if recovery_manager:
            recovery_manager.record_error("ACTION_ERROR")
        return False


# =============================================================================
# Strategy Logic (策略逻辑)
# =============================================================================

def run_strategy(page: Page, recovery_manager: RecoveryManager, logger: DualLogger) -> bool:
    """
    Main strategy loop - the brain of your bot.
    主策略循环 - 机器人的核心逻辑

    Pattern:
    1. Detect current state (检测状态)
    2. Decide action based on state (根据状态决定操作)
    3. Execute action (执行操作)
    4. Verify result (验证结果)
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
        recovery_manager.reset_errors()
        logger.log("[Strategy] Action completed successfully")
    else:
        logger.log("[Strategy] Action failed")

    return success


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Demo entry point"""

    print("=" * 60)
    print("Strategy Bot Template - Demo")
    print("Target: httpbin.org")
    print("=" * 60)

    # Initialize
    logger = DualLogger(LOG_FILE)
    recovery_manager = RecoveryManager(logger)

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
                wait_time = get_wait_time(min_wait=3, max_wait=8)
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
