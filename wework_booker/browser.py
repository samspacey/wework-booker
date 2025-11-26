"""Browser automation for WeWork."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, Browser, Page, Playwright

from .config import Config

logger = logging.getLogger(__name__)


def get_bundled_browser_path() -> str | None:
    """Get path to bundled Chromium browser if running as packaged app.

    Returns:
        Path to Chromium executable if bundled, None otherwise.
    """
    if not getattr(sys, 'frozen', False):
        return None  # Not running as packaged app

    if sys.platform == 'darwin':
        # Mac .app bundle: look in Resources/chromium folder
        bundle_dir = Path(sys.executable).parent.parent / 'Resources'
        browser_path = bundle_dir / 'chromium' / 'Chromium.app' / 'Contents' / 'MacOS' / 'Chromium'
    elif sys.platform == 'win32':
        # Windows: look next to executable in chromium folder
        bundle_dir = Path(sys.executable).parent
        browser_path = bundle_dir / 'chromium' / 'chrome.exe'
    else:
        return None

    if browser_path.exists():
        logger.info(f"Found bundled Chromium at: {browser_path}")
        return str(browser_path)

    logger.debug(f"Bundled Chromium not found at: {browser_path}")
    return None

WEWORK_LOGIN_URL = "https://members.wework.com/workplaceone/content2/login"
WEWORK_BOOKING_URL = "https://members.wework.com/workplaceone/content2/bookings/desks"


class WeWorkBrowser:
    """Browser automation for WeWork member portal."""

    def __init__(self, config: Config):
        self.config = config
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    def __enter__(self) -> "WeWorkBrowser":
        """Start browser session."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close browser session."""
        self.close()

    def start(self) -> None:
        """Initialize and start the browser."""
        logger.info("Starting browser...")
        self._playwright = sync_playwright().start()

        # Check for bundled browser (when running as packaged app)
        launch_options = {"headless": self.config.headless}
        bundled_path = get_bundled_browser_path()
        if bundled_path:
            launch_options["executable_path"] = bundled_path

        self._browser = self._playwright.chromium.launch(**launch_options)
        # Set a proper viewport size for the page
        self._page = self._browser.new_page(
            viewport={"width": 1280, "height": 800}
        )
        logger.info("Browser started successfully")

    def close(self) -> None:
        """Close the browser and cleanup."""
        logger.info("Closing browser...")
        if self._page:
            self._page.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        logger.info("Browser closed")

    @property
    def page(self) -> Page:
        """Get the current page."""
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._page

    def login(self) -> bool:
        """Log in to WeWork member portal.

        Returns:
            True if login successful, False otherwise.
        """
        logger.info("Navigating to WeWork login page...")
        self.page.goto(WEWORK_LOGIN_URL, timeout=60000)

        # Wait for the page to fully load - WeWork is a JS-heavy SPA
        self.page.wait_for_load_state("load")

        try:
            # Log current URL and page state for debugging
            logger.debug(f"Current URL: {self.page.url}")

            # WeWork Angular app takes time to initialize - wait for main content
            logger.info("Waiting for page content to load...")

            # Sometimes the page needs user interaction to proceed
            # Try pressing Enter/clicking to dismiss any blocking elements
            self.page.wait_for_timeout(2000)
            try:
                self.page.keyboard.press("Enter")
                self.page.wait_for_timeout(1000)
                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(1000)
                # Click on the page body to ensure focus
                self.page.click("body", force=True)
            except Exception:
                pass

            try:
                # Wait for the splash/loading screen to disappear
                self.page.wait_for_selector(
                    '.splash-screen, #splash-logo, .loader',
                    state="hidden",
                    timeout=30000
                )
            except Exception:
                pass  # Splash screen may not exist

            # WeWork has a landing page - wait for and click "Member log in" button
            logger.info("Waiting for Member log in button...")
            try:
                member_login_btn = self.page.wait_for_selector(
                    'button:has-text("Member log in")',
                    timeout=30000,
                    state="visible"
                )
                if member_login_btn:
                    logger.info("Clicking Member log in button...")
                    if self.config.debug:
                        self.page.screenshot(path="debug_before_click.png")
                    member_login_btn.click()
                    self.page.wait_for_timeout(3000)  # Wait for login form to appear
            except Exception as e:
                logger.debug(f"Member log in button not found: {e}, may already be on login form")

            # Take screenshot for debugging
            if self.config.debug:
                self.page.screenshot(path="debug_login_page.png")
                logger.debug("Screenshot saved to debug_login_page.png")

            # Look for email input field
            logger.info("Looking for email input field...")

            email_input = None
            selectors = [
                'input[type="email"]', 'input[name="email"]', 'input[id="email"]',
                'input[placeholder*="email" i]', 'input[autocomplete="email"]',
                'input[name="username"]', 'input[id="username"]',
                'input[type="text"]', 'input'
            ]

            for selector in selectors:
                try:
                    email_input = self.page.wait_for_selector(selector, timeout=5000)
                    if email_input:
                        logger.debug(f"Found input with selector: {selector}")
                        break
                except Exception:
                    continue

            if not email_input:
                # Save page content for debugging
                html_content = self.page.content()
                with open("debug_page_content.html", "w") as f:
                    f.write(html_content)
                logger.debug("Page content saved to debug_page_content.html")
                raise Exception("Could not find email input field")
            if email_input:
                email_input.fill(self.config.email)

            # Look for a continue/next button after email
            continue_btn = self.page.query_selector(
                'button[type="submit"], button:has-text("Continue"), '
                'button:has-text("Next"), input[type="submit"]'
            )
            if continue_btn:
                continue_btn.click()
                self.page.wait_for_timeout(2000)  # Wait for page transition

            # Look for password input field
            logger.info("Entering password...")
            password_input = self.page.wait_for_selector(
                'input[type="password"], input[name="password"], input[id="password"]',
                timeout=10000
            )
            if password_input:
                password_input.fill(self.config.password)

            # Click login/submit button
            login_btn = self.page.query_selector(
                'button[type="submit"], button:has-text("Sign in"), '
                'button:has-text("Log in"), button:has-text("Login"), '
                'input[type="submit"]'
            )
            if login_btn:
                login_btn.click()

            # Wait for navigation after login
            self.page.wait_for_timeout(5000)  # Wait for login to process

            # Check if login was successful by looking for common post-login elements
            # or checking if we're no longer on the login page
            if "login" not in self.page.url.lower():
                logger.info("Login successful!")
                return True

            logger.warning("Login may have failed - still on login page")
            return False

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def navigate_to_desk_booking(self) -> bool:
        """Navigate to the desk booking page.

        Returns:
            True if navigation successful, False otherwise.
        """
        logger.info("Navigating to desk booking page...")
        try:
            self.page.goto(WEWORK_BOOKING_URL, timeout=60000)
            self.page.wait_for_load_state("domcontentloaded")
            self.page.wait_for_timeout(2000)  # Additional wait for dynamic content
            logger.info("On desk booking page")
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to desk booking: {e}")
            return False
