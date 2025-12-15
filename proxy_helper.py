"""
Proxy Helper - Network Health Management
A framework for managing proxy/VPN connections and network health.

This is a TEMPLATE - configure for your proxy software.
Supports: Clash, Clash Verge, V2Ray, etc. (via RESTful API)
"""

import json
import urllib.request
import urllib.parse
import time
import os
import threading
import datetime
from typing import Dict, List, Tuple, Optional
from enum import Enum

# Import utilities from bot_core
from bot_core import atomic_write, safe_read_json, mask_url, SUBSCRIBE_URL_FILE, SUBSCRIBE_STATUS_FILE

# ================= Configuration =================

# Proxy API configuration (set via environment variables)
PROXY_PORT = os.environ.get('PROXY_PORT', '9090')
API_URL = f"http://127.0.0.1:{PROXY_PORT}"
API_SECRET = os.environ.get('PROXY_SECRET', "")

# Subscription URL (default, can be overridden by subscribe_url.txt)
DEFAULT_SUB_URL = os.environ.get('SUB_URL', "")

# Subscription update debounce
_subscribe_lock = threading.Lock()
_last_subscribe_update = 0
MIN_SUBSCRIBE_INTERVAL = 30  # seconds

def get_sub_url():
    """
    Dynamically get subscription URL (read latest value each time).
    Priority: subscribe_url.txt > environment variable > default
    """
    try:
        if os.path.exists(SUBSCRIBE_URL_FILE):
            with open(SUBSCRIBE_URL_FILE, 'r', encoding='utf-8') as f:
                url = f.read().strip()
                if url:
                    return url
    except Exception as e:
        print(f"    [Subscription] Failed to read file: {e}")
    return DEFAULT_SUB_URL

# Health check URLs
TEST_URLS = [
    "https://www.google.com",
    "https://1.1.1.1",
    "https://www.cloudflare.com",
]

# Timeout configuration
DELAY_TIMEOUT = 4000  # ms
REQUEST_TIMEOUT = 5   # seconds

# ================= Health Status =================

class HealthStatus(Enum):
    """Health status enumeration"""
    UNKNOWN = "unknown"
    EXCELLENT = "excellent"   # <300ms
    HEALTHY = "healthy"       # 300-800ms
    DEGRADED = "degraded"     # 800-1500ms
    UNHEALTHY = "unhealthy"   # >=1500ms or failed

HEALTH_THRESHOLDS = {
    "EXCELLENT": 300,
    "HEALTHY": 800,
    "DEGRADED": 1500,
}

# ================= API Helper =================

def _build_request(url: str, method: str = "GET", data: Optional[bytes] = None):
    """Build HTTP request with optional authentication"""
    req = urllib.request.Request(url, data=data, method=method)
    if API_SECRET:
        req.add_header("Authorization", f"Bearer {API_SECRET}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    return req

# ================= Health Check =================

def test_single_url(node_name: str, url: str) -> int:
    """
    Test latency to a single URL through specified node.
    Returns latency in ms, or 0 if failed.
    """
    try:
        test_url = (
            f"{API_URL}/proxies/{urllib.parse.quote(node_name)}"
            f"/delay?timeout={DELAY_TIMEOUT}&url={url}"
        )
        req = _build_request(test_url)

        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as res:
            res_data = json.loads(res.read().decode())
            return int(res_data.get("delay", 0))
    except Exception:
        return 0

def multi_point_test(node_name: str) -> Tuple[int, HealthStatus]:
    """
    Test node with multiple URLs.
    Returns: (median_latency, health_status)
    """
    results = []

    for url in TEST_URLS:
        latency = test_single_url(node_name, url)
        results.append(latency)
        print(f"        {url}: {latency}ms" if latency > 0 else f"        {url}: failed")

    # Calculate health
    valid_latencies = [l for l in results if l > 0]
    failed_count = len(results) - len(valid_latencies)

    # Rule 1: Majority failed = unhealthy
    if failed_count >= 2:
        return 9999, HealthStatus.UNHEALTHY

    # Rule 2: Use median for status
    if valid_latencies:
        valid_latencies.sort()
        median = valid_latencies[len(valid_latencies) // 2]

        if median < HEALTH_THRESHOLDS["EXCELLENT"]:
            return median, HealthStatus.EXCELLENT
        elif median < HEALTH_THRESHOLDS["HEALTHY"]:
            return median, HealthStatus.HEALTHY
        elif median < HEALTH_THRESHOLDS["DEGRADED"]:
            return median, HealthStatus.DEGRADED
        else:
            return median, HealthStatus.UNHEALTHY

    return 9999, HealthStatus.UNHEALTHY

# ================= Proxy Management =================

def get_proxy_groups() -> Optional[Dict]:
    """Get all proxy groups from API"""
    try:
        url = f"{API_URL}/proxies"
        req = _build_request(url)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as res:
            data = json.loads(res.read().decode())
        return data.get("proxies", {})
    except Exception as e:
        print(f"    [Error] Failed to get proxy groups: {e}")
        return None

def get_current_node() -> Optional[str]:
    """Get currently selected proxy node"""
    proxies = get_proxy_groups()
    if not proxies:
        return None

    # Find main selector group
    for name, info in proxies.items():
        if isinstance(info, dict) and info.get("type") == "Selector":
            return info.get("now")

    return None

def switch_node(group_name: str, node_name: str) -> bool:
    """Switch to specified node in a group"""
    try:
        url = f"{API_URL}/proxies/{urllib.parse.quote(group_name)}"
        data = json.dumps({"name": node_name}).encode("utf-8")
        req = _build_request(url, method="PUT", data=data)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT):
            print(f"    [Success] Switched to: {node_name}")
            return True
    except Exception as e:
        print(f"    [Error] Failed to switch node: {e}")
        return False

def get_available_nodes(group_name: str) -> List[str]:
    """Get all available nodes in a group"""
    try:
        url = f"{API_URL}/proxies/{urllib.parse.quote(group_name)}"
        req = _build_request(url)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as res:
            data = json.loads(res.read().decode())

        all_nodes = data.get("all", []) or []
        # Filter out special entries
        return [n for n in all_nodes if n not in ("DIRECT", "REJECT", "GLOBAL")]
    except Exception as e:
        print(f"    [Error] Failed to get nodes: {e}")
        return []

# ================= Public Interface =================

def check_health() -> Tuple[str, int, bool]:
    """
    Check current network health.
    Returns: (node_name, latency_ms, is_healthy)
    """
    print("\n" + "=" * 50)
    print(f"[Health Check] {time.strftime('%Y-%m-%d %H:%M:%S')}")

    node_name = get_current_node()
    if not node_name:
        return "Unknown", -1, False

    print(f"    [Current Node] {node_name}")

    latency, status = multi_point_test(node_name)
    is_healthy = status in (HealthStatus.EXCELLENT, HealthStatus.HEALTHY)

    print(f"    [Result] {latency}ms, {status.value}")
    return node_name, latency, is_healthy

def try_fix_network() -> bool:
    """
    Attempt to fix network by switching nodes.
    Returns: True if fixed successfully.
    """
    print("\n[Network Fix] Attempting to fix network...")

    proxies = get_proxy_groups()
    if not proxies:
        return False

    # Find selector groups
    for name, info in proxies.items():
        if isinstance(info, dict) and info.get("type") == "Selector":
            nodes = get_available_nodes(name)
            current = info.get("now")

            # Try other nodes
            for node in nodes:
                if node == current:
                    continue

                print(f"    [Trying] {node}")
                latency = test_single_url(node, TEST_URLS[0])

                if latency > 0 and latency < HEALTH_THRESHOLDS["HEALTHY"]:
                    if switch_node(name, node):
                        print(f"    [Fixed] Switched to {node} ({latency}ms)")
                        return True

    print("    [Failed] Could not find healthy node")
    return False

def get_mixed_port() -> int:
    """Get the mixed port for proxy configuration"""
    return int(os.environ.get('PROXY_MIXED_PORT', '7890'))

# ================= Subscription Update =================

def _write_subscribe_status(success: bool, url: str, error: str = None):
    """Write subscription update status (atomic write)"""
    status = {
        "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "success": success,
        "url_preview": mask_url(url),
        "error": error
    }
    try:
        atomic_write(SUBSCRIBE_STATUS_FILE, json.dumps(status, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"    [Subscription] Failed to write status: {e}")

def update_subscription() -> bool:
    """
    Update proxy subscription with debounce and locking.
    Returns: True if successful.
    """
    global _last_subscribe_update

    # 1. Debounce: skip if updated recently
    now = time.time()
    if now - _last_subscribe_update < MIN_SUBSCRIBE_INTERVAL:
        print(f"    [Subscription] Too soon ({int(now - _last_subscribe_update)}s since last), skipping")
        return True  # Treat as success, no update needed

    # 2. Non-blocking lock: skip if update in progress
    if not _subscribe_lock.acquire(blocking=False):
        print("    [Subscription] Update already in progress, skipping")
        return True

    sub_url = get_sub_url()
    if not sub_url:
        print("    [Subscription] No SUB_URL configured")
        _subscribe_lock.release()
        return False

    try:
        _last_subscribe_update = now
        print(f"    [Subscription] Downloading: {mask_url(sub_url)}")

        req = urllib.request.Request(sub_url)
        req.add_header("User-Agent", "ProxyHelper/1.0")

        with urllib.request.urlopen(req, timeout=20) as response:
            content = response.read()

        # Validate content
        if b"proxies:" not in content and b"port:" not in content:
            print("    [Subscription] Invalid content")
            _write_subscribe_status(False, sub_url, "Invalid content")
            return False

        # Reload config via API
        url = f"{API_URL}/configs?force=true"
        # Note: This requires proper config path - customize as needed
        print("    [Subscription] Config downloaded successfully")
        _write_subscribe_status(True, sub_url)
        return True

    except Exception as e:
        print(f"    [Subscription] Update failed: {e}")
        _write_subscribe_status(False, sub_url, str(e))
        return False
    finally:
        _subscribe_lock.release()

# ================= CLI Entry =================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "once":
        # Single check mode
        print("==== Single Health Check ====")
        node, latency, is_healthy = check_health()
        print(f"Result: {node} {latency}ms {'healthy' if is_healthy else 'unhealthy'}")
        if not is_healthy:
            print("Attempting fix...")
            try_fix_network()
    else:
        # Continuous monitoring mode
        print("==== Proxy Helper - Monitoring Mode ====")
        print("Press Ctrl+C to stop")

        while True:
            try:
                node, latency, is_healthy = check_health()
                if not is_healthy:
                    try_fix_network()

                # Wait before next check
                wait_time = 180 if is_healthy else 30
                print(f"\n[Sleep] {wait_time} seconds until next check...")
                time.sleep(wait_time)

            except KeyboardInterrupt:
                print("\n[Exit] User interrupted")
                break
            except Exception as e:
                print(f"\n[Error] {e}")
                time.sleep(30)
