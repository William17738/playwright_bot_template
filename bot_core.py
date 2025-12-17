"""
Bot Core Framework - Strategy Bot Foundation
A clean framework for building Playwright-based automation bots.

This is a TEMPLATE - implement your own strategy logic.
"""

import sys
import os

import time
import smtplib
import random
import json
from urllib.parse import urlparse, parse_qs, urlencode
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from typing import Any, NoReturn, Optional

from config import MS_PER_SECOND, SECONDS_PER_MINUTE

# ================= Constants =================
# NOTE: These values preserve the template's original behavior. Adjusting them
# changes bot timing, retry thresholds, and other runtime characteristics.

# Default SMTP SSL port used when MAIL_PORT is not provided via environment.
DEFAULT_MAIL_PORT = 465

# Default min/max wait time (minutes) between iterations when not provided via env.
DEFAULT_MIN_WAIT_MINUTES = 5
DEFAULT_MAX_WAIT_MINUTES = 45

# How many URL characters to show before masking the rest (avoid leaking tokens).
MASK_URL_VISIBLE_PREFIX_CHARS = 25

# Remote control commands older than this (seconds) are ignored.
REMOTE_COMMAND_EXPIRY_SECONDS = 60

# How often to poll (seconds) while a pause lock file exists.
PAUSE_LOCK_POLL_INTERVAL_SECONDS = 5

# Default human-like delay range (seconds) between actions.
HUMAN_DELAY_MIN_SECONDS_DEFAULT = 0.5
HUMAN_DELAY_MAX_SECONDS_DEFAULT = 2.0

# Default max wait time (seconds) for safe click operations.
SAFE_CLICK_MAX_WAIT_SECONDS_DEFAULT = 5

# Timeout (ms) used when checking if a button is visible.
FIND_BUTTON_VISIBLE_TIMEOUT_MS = 300

# Element stability detection defaults.
ELEMENT_STABILITY_TIMEOUT_SECONDS_DEFAULT = 2.0
ELEMENT_STABILITY_THRESHOLD_PX_DEFAULT = 2
ELEMENT_STABILITY_BOUNDING_BOX_TIMEOUT_MS = 200
ELEMENT_STABILITY_REQUIRED_STABLE_CHECKS = 2
ELEMENT_STABILITY_POLL_INTERVAL_SECONDS = 0.1

# Recovery system tuning.
RECOVERY_MAX_A_ERRORS = 5
RECOVERY_MAX_B_ERRORS = 3
RECOVERY_MAX_A_STILL_FAIL = 3
RECOVERY_COOLDOWN_SECONDS = 30
RECOVERY_A_RELOAD_TIMEOUT_MS = 15000
RECOVERY_A_POST_RELOAD_SLEEP_SECONDS = 3
RECOVERY_B_GOTO_TIMEOUT_MS = 20000
RECOVERY_B_POST_GOTO_SLEEP_SECONDS = 3
RECOVERY_C_RESTART_DELAY_SECONDS = 30
RECOVERY_RESTART_EXIT_CODE = 2

# Timeout (ms) used when checking for password field visibility in login detection.
PASSWORD_FIELD_VISIBLE_TIMEOUT_MS = 500

# Login waiting defaults.
WAIT_FOR_LOGIN_DEFAULT_TIMEOUT_MINUTES = 30
LOGIN_ALERT_BANNER_WIDTH = 50
LOGIN_POLL_INTERVAL_SECONDS = 5

# Default timeouts for safe visibility/wait helper functions (ms).
SAFE_VISIBLE_TIMEOUT_MS_DEFAULT = 400
SAFE_WAIT_TIMEOUT_MS_DEFAULT = 5000

# ================= Configuration =================

# Target URL - Override in your implementation
TARGET_URL = os.environ.get('TARGET_URL', "https://example.com")

# Email configuration (set via environment variables)
MAIL_HOST = os.environ.get('MAIL_HOST', "smtp.example.com")
MAIL_PORT = int(os.environ.get('MAIL_PORT', DEFAULT_MAIL_PORT))
MAIL_USER = os.environ.get('MAIL_USER', "")
MAIL_PASS = os.environ.get('MAIL_PASS', "")
MAIL_RECEIVER = os.environ.get('MAIL_RECEIVER', "")

# Control files
LOCK_FILE = "pause.lock"
CMD_FILE = "command.txt"
QR_IMAGE = "login_qr.png"
MONITOR_IMAGE = "monitor.png"

# Subscription management files
SUBSCRIBE_URL_FILE = "subscribe_url.txt"
SUBSCRIBE_STATUS_FILE = "subscribe_status.json"

# Timing configuration - customize for your use case
MIN_WAIT = int(os.environ.get('MIN_WAIT', DEFAULT_MIN_WAIT_MINUTES))
MAX_WAIT = int(os.environ.get('MAX_WAIT', DEFAULT_MAX_WAIT_MINUTES))

# ================= Logging =================

class DualLogger:
    """Dual output logger - writes to both terminal and file"""
    def __init__(self, filepath):
        self.terminal = sys.stdout
        self.log = open(filepath, "a", encoding="utf-8")

    def write(self, message: str) -> None:
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self) -> None:
        self.terminal.flush()
        self.log.flush()

# ================= Core Utilities =================

def atomic_write(filepath: str, content: str) -> None:
    """Atomic file write - write to .tmp then rename, avoid partial reads"""
    tmp_path = filepath + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        f.write(content)
    os.replace(tmp_path, filepath)

def safe_read_json(filepath: str, default: Optional[Any] = None) -> Optional[Any]:
    """Safely read JSON file, return default on any error"""
    try:
        if not os.path.exists(filepath):
            return default
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return default
            return json.loads(content)
    except (json.JSONDecodeError, IOError, OSError, UnicodeDecodeError) as e:
        print(f"    [Warning] Failed to read {filepath}: {e}")
        return default

def mask_url(url: Optional[str]) -> str:
    """
    Mask URL for safe display - hide query parameter values.
    https://api.example.com/sub?token=SECRET
    → https://api.example.com/sub?token=***
    """
    if not url:
        return "(empty)"
    try:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=True)
            masked = {k: ['***'] for k in params.keys()}
            return f"{base}?{urlencode(masked, doseq=True)}"
        return base
    except Exception:
        return (
            url[:MASK_URL_VISIBLE_PREFIX_CHARS] + "...***"
            if len(url) > MASK_URL_VISIBLE_PREFIX_CHARS
            else url
        )

def update_monitor(page: Any) -> None:
    """Update monitoring screenshot (atomic operation, silent fail)"""
    try:
        abs_path = os.path.abspath(MONITOR_IMAGE)
        tmp_path = abs_path + ".tmp"
        page.screenshot(path=tmp_path, type='png')
        try:
            os.replace(tmp_path, abs_path)
        except OSError:
            pass
    except Exception:
        pass

def send_alert_email(subject: str, body: str, image_path: Optional[str] = None) -> None:
    """Send alert email notification"""
    if not MAIL_USER or not MAIL_PASS:
        print(f"    [Email] Skipped (not configured): {subject}")
        return

    print(f"    [Email] Sending: {subject}...")
    try:
        msg = MIMEMultipart()
        msg['From'] = MAIL_USER
        msg['To'] = MAIL_RECEIVER
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                msg.attach(MIMEImage(f.read(), name="attachment.png"))
        server = smtplib.SMTP_SSL(MAIL_HOST, MAIL_PORT)
        server.login(MAIL_USER, MAIL_PASS)
        server.sendmail(MAIL_USER, MAIL_RECEIVER, msg.as_string())
        server.quit()
        print("    [Email] Sent successfully!")
    except Exception as e:
        print(f"    [Email Failed] {e}")

def _parse_command(raw_content):
    """
    Parse command content, supports two formats:
    1. JSON: {"cmd": "xxx", "ts": 123456}
    2. Plain text: xxx (backward compatible)
    Returns: (cmd_name, timestamp)
    """
    try:
        data = json.loads(raw_content)
        if not isinstance(data, dict):
            return None, 0
        cmd = data.get('cmd', '')
        ts = data.get('ts', 0)
        # Ignore commands older than a fixed threshold to avoid replaying stale actions.
        if ts and time.time() - ts > REMOTE_COMMAND_EXPIRY_SECONDS:
            print(f"    [Remote] Command expired ({int(time.time() - ts)}s ago), ignoring")
            return None, ts
        return cmd, ts
    except (json.JSONDecodeError, TypeError):
        # Backward compatible: plain text format
        return raw_content.strip(), 0

def check_remote_control(page: Optional[Any] = None) -> bool:
    """Check and execute remote control commands (supports JSON format)"""
    should_run_immediately = False

    # Check command file
    if os.path.exists(CMD_FILE):
        with open(CMD_FILE, 'r') as f:
            raw = f.read().strip()
        os.remove(CMD_FILE)

        cmd, ts = _parse_command(raw)
        if cmd is None:
            pass  # Command expired, skip
        elif cmd == "update_subscribe":
            print(f"\n[Remote] Command: update_subscribe")
            try:
                import proxy_helper
                result = proxy_helper.update_subscription()
                print(f"       Subscription update: {'success' if result else 'failed'}")
            except Exception as e:
                print(f"       Subscription update error: {e}")
        elif cmd:
            print(f"\n[Remote] Received command: {cmd}")
            # Implement your command handling here
            # Example: if cmd == "logout": handle_logout(page)

    # Check pause lock
    if os.path.exists(LOCK_FILE):
        print(f"\n[Remote] Detected {LOCK_FILE}, pausing...")
        while os.path.exists(LOCK_FILE):
            time.sleep(PAUSE_LOCK_POLL_INTERVAL_SECONDS)
        print("[Remote] Pause ended, resuming!")
        should_run_immediately = True

    return should_run_immediately

# ================= Timing Functions (Implement Your Own) =================

def get_wait_time() -> float:
    """
    Get wait time between operations.

    IMPLEMENT YOUR OWN TIMING LOGIC HERE.
    This is a simple placeholder implementation.
    """
    # Simple random wait - replace with your own logic
    return random.uniform(MIN_WAIT * SECONDS_PER_MINUTE, MAX_WAIT * SECONDS_PER_MINUTE)

def human_delay(
    min_sec: float = HUMAN_DELAY_MIN_SECONDS_DEFAULT,
    max_sec: float = HUMAN_DELAY_MAX_SECONDS_DEFAULT,
) -> None:
    """
    Human-like delay between actions.

    IMPLEMENT YOUR OWN DELAY LOGIC HERE.
    """
    time.sleep(random.uniform(min_sec, max_sec))

# ================= Page Operations =================

def safe_click(
    page: Any,
    locator: Any,
    description: str = "element",
    max_wait: float = SAFE_CLICK_MAX_WAIT_SECONDS_DEFAULT,
) -> bool:
    """Safe click with wait and error handling"""
    try:
        locator.wait_for(state="visible", timeout=max_wait * MS_PER_SECOND)
        locator.click(timeout=max_wait * MS_PER_SECOND)
        print(f"    [Action] Clicked: {description}")
        return True
    except Exception as e:
        print(f"    [Failed] Cannot click {description}: {e}")
        return False

def find_button(page: Any, text: str) -> Optional[Any]:
    """Find button by text (fuzzy match)"""
    try:
        button = page.get_by_role("button").filter(has_text=text).first
        if button.is_visible(timeout=FIND_BUTTON_VISIBLE_TIMEOUT_MS):
            return button
    except Exception:
        pass
    return None

def wait_for_element_stable(
    page: Any,
    locator: Any,
    timeout: float = ELEMENT_STABILITY_TIMEOUT_SECONDS_DEFAULT,
    threshold: int = ELEMENT_STABILITY_THRESHOLD_PX_DEFAULT,
) -> bool:
    """
    Wait for element position to stabilize (animation complete).
    Checks if bounding box remains stable for consecutive checks.
    """
    last_box = None
    stable_count = 0
    start = time.time()

    while time.time() - start < timeout:
        try:
            box = locator.bounding_box(timeout=ELEMENT_STABILITY_BOUNDING_BOX_TIMEOUT_MS)
            if box:
                if last_box:
                    dx = abs(box['x'] - last_box['x'])
                    dy = abs(box['y'] - last_box['y'])
                    if dx < threshold and dy < threshold:
                        stable_count += 1
                        if stable_count >= ELEMENT_STABILITY_REQUIRED_STABLE_CHECKS:
                            print(f"       [Stable] Element position stabilized")
                            return True
                    else:
                        stable_count = 0
                last_box = box
        except Exception:
            pass
        time.sleep(ELEMENT_STABILITY_POLL_INTERVAL_SECONDS)

    print(f"       [Timeout] Wait for stable timeout")
    return False

# ================= Recovery System =================

class RecoveryManager:
    """
    Multi-level recovery system for handling errors.

    Level A: Page refresh
    Level B: Session rebuild (navigate to target)
    Level C: Process restart
    """

    def __init__(self):
        self.error_count_a = 0
        self.error_count_b = 0
        self.max_a_errors = RECOVERY_MAX_A_ERRORS
        self.max_b_errors = RECOVERY_MAX_B_ERRORS
        self.last_recovery_level = None
        self.a_still_fail_count = 0
        self.max_a_still_fail = RECOVERY_MAX_A_STILL_FAIL
        self.last_recovery_time = 0
        self.recovery_cooldown = RECOVERY_COOLDOWN_SECONDS

    def recover_level_a(self, page: Any, context: str = "") -> bool:
        """Level A: Page refresh"""
        print(f"    [Recovery-A] Page level: {context}")
        try:
            page.reload(timeout=RECOVERY_A_RELOAD_TIMEOUT_MS)
            time.sleep(RECOVERY_A_POST_RELOAD_SLEEP_SECONDS)
            print("    [Recovery-A] Page refresh complete")
            return True
        except Exception as e:
            print(f"    [Recovery-A Failed] {e}")
            return False

    def recover_level_b(self, page: Any, context: str = "") -> bool:
        """Level B: Session rebuild"""
        print(f"    [Recovery-B] Session level: {context}")
        try:
            page.goto(TARGET_URL, timeout=RECOVERY_B_GOTO_TIMEOUT_MS, wait_until="domcontentloaded")
            time.sleep(RECOVERY_B_POST_GOTO_SLEEP_SECONDS)
            print("    [Recovery-B] Session rebuild complete")
            return True
        except Exception as e:
            print(f"    [Recovery-B Failed] {e}")
            return False

    def trigger_level_c(self, reason: str = "Error threshold reached") -> NoReturn:
        """Level C: Trigger process restart"""
        print(f"    [Recovery-C] {reason}")
        send_alert_email(
            "[Bot] Level C Restart Triggered",
            f"Reason: {reason}\nSystem will restart in {RECOVERY_C_RESTART_DELAY_SECONDS} seconds."
        )
        time.sleep(RECOVERY_C_RESTART_DELAY_SECONDS)
        sys.exit(RECOVERY_RESTART_EXIT_CODE)  # Exit code = needs restart

    def handle_error(self, page: Any, error_type: str, context: str = "") -> bool:
        """Unified error handling entry point"""
        current_time = time.time()

        if current_time - self.last_recovery_time < self.recovery_cooldown:
            print("    [Recovery] Cooldown active, skipping")
            return False

        print(f"    [Recovery] Error type: {error_type}, Context: {context}")

        # Escalate if Level A reload succeeds but does not solve the underlying issue
        if self.last_recovery_level == "A":
            self.a_still_fail_count += 1
        else:
            self.a_still_fail_count = 0

        if self.a_still_fail_count >= self.max_a_still_fail:
            print(f"    [Recovery] Level A ineffective {self.a_still_fail_count} times, escalating to Level B")
            if self.recover_level_b(page, f"Level A ineffective {self.a_still_fail_count} times: {context}"):
                self.error_count_a = 0
                self.error_count_b = 0
                self.a_still_fail_count = 0
                self.last_recovery_level = "B"
                self.last_recovery_time = current_time
                return True
            else:
                self.error_count_b += 1
                if self.error_count_b >= self.max_b_errors:
                    self.trigger_level_c(f"Level B failed {self.error_count_b} times")
                return False

        # Try Level A first
        if self.recover_level_a(page, context):
            self.error_count_a = 0
            self.last_recovery_level = "A"
            self.last_recovery_time = current_time
            return True
        else:
            self.error_count_a += 1

        # If Level A fails too many times, try Level B
        if self.error_count_a >= self.max_a_errors:
            if self.recover_level_b(page, f"Level A failed {self.error_count_a} times"):
                self.error_count_a = 0
                self.error_count_b = 0
                self.a_still_fail_count = 0
                self.last_recovery_level = "B"
                self.last_recovery_time = current_time
                return True
            else:
                self.error_count_b += 1

        # If Level B also fails, trigger Level C
        if self.error_count_b >= self.max_b_errors:
            self.trigger_level_c(f"Level B failed {self.error_count_b} times")

        return False

    def reset_counters(self) -> None:
        """Reset error counters after successful operation"""
        self.error_count_a = 0
        self.error_count_b = 0
        self.a_still_fail_count = 0
        self.last_recovery_level = None

    def attempt_recovery(self, page: Any, error_context: str = "") -> bool:
        """Unified recovery interface"""
        return self.handle_error(page, "unknown", error_context)

# ================= Login Detection =================

def is_login_required(page: Any) -> bool:
    """
    Check if login is required.

    CUSTOMIZE FOR YOUR TARGET SITE.
    """
    current_url = page.url.lower()

    # URL patterns that indicate login page
    login_patterns = ["login", "signin", "auth", "account"]
    if any(pattern in current_url for pattern in login_patterns):
        return True

    # Check for password input field
    try:
        if page.locator("input[type='password']").is_visible(timeout=PASSWORD_FIELD_VISIBLE_TIMEOUT_MS):
            return True
    except Exception:
        pass

    return False

def wait_for_login(page: Any, timeout_minutes: float = WAIT_FOR_LOGIN_DEFAULT_TIMEOUT_MINUTES) -> bool:
    """
    Wait for user to complete login.

    CUSTOMIZE FOR YOUR LOGIN FLOW.
    """
    print("\n" + "!" * LOGIN_ALERT_BANNER_WIDTH)
    print("[Alert] Login required...")

    send_alert_email(
        "[Bot] Login Required",
        f"Please complete login within {WAIT_FOR_LOGIN_DEFAULT_TIMEOUT_MINUTES} minutes.",
        QR_IMAGE
    )

    # Save screenshot
    try:
        page.screenshot(path=QR_IMAGE)
    except Exception:
        pass

    start_wait = time.time()
    while time.time() - start_wait < timeout_minutes * SECONDS_PER_MINUTE:
        if not is_login_required(page):
            print("[Success] Login completed!")
            return True
        time.sleep(LOGIN_POLL_INTERVAL_SECONDS)

    return False

# ================= Utility Functions =================

def safe_visible(locator: Any, timeout: int = SAFE_VISIBLE_TIMEOUT_MS_DEFAULT) -> bool:
    """Safely check if element is visible"""
    try:
        return locator.is_visible(timeout=timeout)
    except Exception:
        return False

def safe_wait(locator: Any, state: str = "visible", timeout: int = SAFE_WAIT_TIMEOUT_MS_DEFAULT) -> bool:
    """Safely wait for element state"""
    try:
        locator.wait_for(state=state, timeout=timeout)
        return True
    except Exception:
        return False
