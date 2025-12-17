"""
Shared configuration constants for the Playwright bot template.

This module centralizes "magic numbers" (timeouts, viewport sizes, etc.) so they
can be tuned in one place without changing bot behavior.
"""

# Default Chrome/Chromium remote debugging port for CDP connections.
DEFAULT_PORT = 9222

# Default browser viewport size (in pixels) for Playwright contexts.
VIEWPORT_WIDTH = 1280
VIEWPORT_HEIGHT = 720

# Default Playwright timeout (in milliseconds) for navigation/actions.
DEFAULT_TIMEOUT = 30000

# JPEG screenshot quality (1-100) when using `page.screenshot(type="jpeg")`.
SCREENSHOT_QUALITY = 80

# Time conversion helpers.
MS_PER_SECOND = 1000
SECONDS_PER_MINUTE = 60
