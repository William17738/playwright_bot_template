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

# ================= Configuration =================

# Target URL - Override in your implementation
TARGET_URL = os.environ.get('TARGET_URL', "https://example.com")

# Email configuration (set via environment variables)
MAIL_HOST = os.environ.get('MAIL_HOST', "smtp.example.com")
MAIL_PORT = int(os.environ.get('MAIL_PORT', 465))
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
MIN_WAIT = int(os.environ.get('MIN_WAIT', 5))
MAX_WAIT = int(os.environ.get('MAX_WAIT', 45))

# ================= Logging =================

class DualLogger:
    """Dual output logger - writes to both terminal and file"""
    def __init__(self, filepath):
        self.terminal = sys.stdout
        self.log = open(filepath, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

# ================= Core Utilities =================

def atomic_write(filepath, content):
    """Atomic file write - write to .tmp then rename, avoid partial reads"""
    tmp_path = filepath + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        f.write(content)
    os.replace(tmp_path, filepath)

def safe_read_json(filepath, default=None):
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

def mask_url(url):
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
    except:
        return url[:25] + "...***" if len(url) > 25 else url

def update_monitor(page):
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

def send_alert_email(subject, body, image_path=None):
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
        cmd = data.get('cmd', '')
        ts = data.get('ts', 0)
        # Ignore commands older than 60 seconds
        if ts and time.time() - ts > 60:
            print(f"    [Remote] Command expired ({int(time.time() - ts)}s ago), ignoring")
            return None, ts
        return cmd, ts
    except (json.JSONDecodeError, TypeError):
        # Backward compatible: plain text format
        return raw_content.strip(), 0

def check_remote_control(page=None):
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
            time.sleep(5)
        print("[Remote] Pause ended, resuming!")
        should_run_immediately = True

    return should_run_immediately

# ================= Timing Functions (Implement Your Own) =================

def get_wait_time():
    """
    Get wait time between operations.

    IMPLEMENT YOUR OWN TIMING LOGIC HERE.
    This is a simple placeholder implementation.
    """
    # Simple random wait - replace with your own logic
    return random.uniform(MIN_WAIT * 60, MAX_WAIT * 60)

def human_delay(min_sec=0.5, max_sec=2.0):
    """
    Human-like delay between actions.

    IMPLEMENT YOUR OWN DELAY LOGIC HERE.
    """
    time.sleep(random.uniform(min_sec, max_sec))

# ================= Page Operations =================

def safe_click(page, locator, description="element", max_wait=5):
    """Safe click with wait and error handling"""
    try:
        locator.wait_for(state="visible", timeout=max_wait*1000)
        locator.click(timeout=max_wait*1000)
        print(f"    [Action] Clicked: {description}")
        return True
    except Exception as e:
        print(f"    [Failed] Cannot click {description}: {e}")
        return False

def find_button(page, text):
    """Find button by text (fuzzy match)"""
    try:
        button = page.get_by_role("button").filter(has_text=text).first
        if button.is_visible(timeout=300):
            return button
    except:
        pass
    return None

def wait_for_element_stable(page, locator, timeout=2.0, threshold=2):
    """
    Wait for element position to stabilize (animation complete).
    Checks if bounding box remains stable for consecutive checks.
    """
    last_box = None
    stable_count = 0
    start = time.time()

    while time.time() - start < timeout:
        try:
            box = locator.bounding_box(timeout=200)
            if box:
                if last_box:
                    dx = abs(box['x'] - last_box['x'])
                    dy = abs(box['y'] - last_box['y'])
                    if dx < threshold and dy < threshold:
                        stable_count += 1
                        if stable_count >= 2:
                            print(f"       [Stable] Element position stabilized")
                            return True
                    else:
                        stable_count = 0
                last_box = box
        except:
            pass
        time.sleep(0.1)

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
        self.max_a_errors = 5
        self.max_b_errors = 3
        self.last_recovery_time = 0
        self.recovery_cooldown = 30

    def recover_level_a(self, page, context=""):
        """Level A: Page refresh"""
        print(f"    [Recovery-A] Page level: {context}")
        try:
            page.reload(timeout=15000)
            time.sleep(3)
            print("    [Recovery-A] Page refresh complete")
            return True
        except Exception as e:
            print(f"    [Recovery-A Failed] {e}")
            return False

    def recover_level_b(self, page, context=""):
        """Level B: Session rebuild"""
        print(f"    [Recovery-B] Session level: {context}")
        try:
            page.goto(TARGET_URL, timeout=20000, wait_until="domcontentloaded")
            time.sleep(3)
            print("    [Recovery-B] Session rebuild complete")
            return True
        except Exception as e:
            print(f"    [Recovery-B Failed] {e}")
            return False

    def trigger_level_c(self, reason="Error threshold reached"):
        """Level C: Trigger process restart"""
        print(f"    [Recovery-C] {reason}")
        send_alert_email(
            "[Bot] Level C Restart Triggered",
            f"Reason: {reason}\nSystem will restart in 30 seconds."
        )
        time.sleep(30)
        sys.exit(2)  # Exit code 2 = needs restart

    def handle_error(self, page, error_type, context=""):
        """Unified error handling entry point"""
        current_time = time.time()

        if current_time - self.last_recovery_time < self.recovery_cooldown:
            print("    [Recovery] Cooldown active, skipping")
            return False

        print(f"    [Recovery] Error type: {error_type}, Context: {context}")

        # Try Level A first
        if self.recover_level_a(page, context):
            self.error_count_a = 0
            self.last_recovery_time = current_time
            return True
        else:
            self.error_count_a += 1

        # If Level A fails too many times, try Level B
        if self.error_count_a >= self.max_a_errors:
            if self.recover_level_b(page, f"Level A failed {self.error_count_a} times"):
                self.error_count_a = 0
                self.error_count_b = 0
                self.last_recovery_time = current_time
                return True
            else:
                self.error_count_b += 1

        # If Level B also fails, trigger Level C
        if self.error_count_b >= self.max_b_errors:
            self.trigger_level_c(f"Level B failed {self.error_count_b} times")

        return False

    def reset_counters(self):
        """Reset error counters after successful operation"""
        self.error_count_a = 0
        self.error_count_b = 0

    def attempt_recovery(self, page, error_context=""):
        """Unified recovery interface"""
        return self.handle_error(page, "unknown", error_context)

# ================= Login Detection =================

def is_login_required(page):
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
        if page.locator("input[type='password']").is_visible(timeout=500):
            return True
    except:
        pass

    return False

def wait_for_login(page, timeout_minutes=30):
    """
    Wait for user to complete login.

    CUSTOMIZE FOR YOUR LOGIN FLOW.
    """
    print("\n" + "!" * 50)
    print("[Alert] Login required...")

    send_alert_email(
        "[Bot] Login Required",
        "Please complete login within 30 minutes.",
        QR_IMAGE
    )

    # Save screenshot
    try:
        page.screenshot(path=QR_IMAGE)
    except:
        pass

    start_wait = time.time()
    while time.time() - start_wait < timeout_minutes * 60:
        if not is_login_required(page):
            print("[Success] Login completed!")
            return True
        time.sleep(5)

    return False

# ================= Utility Functions =================

def safe_visible(locator, timeout=400):
    """Safely check if element is visible"""
    try:
        return locator.is_visible(timeout=timeout)
    except:
        return False

def safe_wait(locator, state="visible", timeout=5000):
    """Safely wait for element state"""
    try:
        locator.wait_for(state=state, timeout=timeout)
        return True
    except:
        return False
