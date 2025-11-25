"""Browser automation for WeWork."""

import logging
from playwright.sync_api import sync_playwright, Browser, Page, Playwright

from .config import Config

logger = logging.getLogger(__name__)

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
        self._browser = self._playwright.chromium.launch(
            headless=self.config.headless
        )
        self._page = self._browser.new_page()
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
        self.page.goto(WEWORK_LOGIN_URL)

        # Wait for the page to load
        self.page.wait_for_load_state("networkidle")

        try:
            # WeWork uses various SSO providers, the exact flow may vary
            # This handles the common email/password flow

            # Look for email input field
            logger.info("Entering email...")
            email_input = self.page.wait_for_selector(
                'input[type="email"], input[name="email"], input[id="email"], '
                'input[placeholder*="email" i], input[autocomplete="email"]',
                timeout=10000
            )
            if email_input:
                email_input.fill(self.config.email)

            # Look for a continue/next button after email
            continue_btn = self.page.query_selector(
                'button[type="submit"], button:has-text("Continue"), '
                'button:has-text("Next"), input[type="submit"]'
            )
            if continue_btn:
                continue_btn.click()
                self.page.wait_for_load_state("networkidle")

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
            self.page.wait_for_load_state("networkidle")

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
            self.page.goto(WEWORK_BOOKING_URL)
            self.page.wait_for_load_state("networkidle")
            logger.info("On desk booking page")
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to desk booking: {e}")
            return False
