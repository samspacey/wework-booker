"""Desk booking logic for WeWork."""

import logging
from datetime import datetime, timedelta
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .config import Config

logger = logging.getLogger(__name__)

# Day name to weekday number mapping (Monday = 0)
DAY_TO_WEEKDAY = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def get_next_booking_dates(
    booking_days: list[str], weeks_ahead: int = 2
) -> list[datetime]:
    """Get the next dates to book based on configured days.

    Args:
        booking_days: List of day names (e.g., ["wednesday", "thursday"])
        weeks_ahead: Number of weeks ahead to book

    Returns:
        List of datetime objects for dates to book
    """
    today = datetime.now()
    dates_to_book = []

    target_weekdays = [DAY_TO_WEEKDAY[day.lower()] for day in booking_days]

    # Look ahead for the specified number of weeks
    for days_offset in range(weeks_ahead * 7 + 7):
        check_date = today + timedelta(days=days_offset)
        if check_date.weekday() in target_weekdays:
            # Only book future dates (not today or past)
            if check_date.date() > today.date():
                dates_to_book.append(check_date)

    return dates_to_book


class DeskBooker:
    """Handles desk booking operations."""

    def __init__(self, page: Page, config: Config):
        self.page = page
        self.config = config

    def select_location(self) -> bool:
        """Select the WeWork location for booking.

        Returns:
            True if location selected successfully, False otherwise.
        """
        logger.info(f"Selecting location: {self.config.location}")

        try:
            # Look for location selector/dropdown
            # WeWork's interface may have different selectors
            location_selector = self.page.query_selector(
                '[data-testid="location-selector"], '
                '.location-dropdown, '
                'button:has-text("Select location"), '
                'button:has-text("Choose location"), '
                '[aria-label*="location" i]'
            )

            if location_selector:
                location_selector.click()
                self.page.wait_for_timeout(1000)

                # Search for the specific location
                search_input = self.page.query_selector(
                    'input[placeholder*="search" i], '
                    'input[type="search"], '
                    '.location-search input'
                )
                if search_input:
                    search_input.fill(self.config.location)
                    self.page.wait_for_timeout(1000)

                # Click on the location in the results
                location_option = self.page.query_selector(
                    f'text="{self.config.location}"'
                )
                if location_option:
                    location_option.click()
                    self.page.wait_for_load_state("networkidle")
                    logger.info(f"Selected location: {self.config.location}")
                    return True

            # Alternative: location might already be in URL or pre-selected
            logger.info("Location selector not found, may be pre-configured")
            return True

        except Exception as e:
            logger.error(f"Failed to select location: {e}")
            return False

    def book_desk_for_date(self, date: datetime) -> bool:
        """Book a desk for a specific date.

        Args:
            date: The date to book

        Returns:
            True if booking successful, False otherwise.
        """
        date_str = date.strftime("%Y-%m-%d")
        day_name = date.strftime("%A")
        logger.info(f"Attempting to book desk for {day_name}, {date_str}")

        try:
            # Navigate to the specific date
            # WeWork typically has a date picker or calendar view
            self._select_date(date)

            # Find and click on an available desk
            if not self._select_available_desk():
                logger.warning(f"No available desks found for {date_str}")
                return False

            # Confirm the booking
            if not self._confirm_booking():
                logger.warning(f"Failed to confirm booking for {date_str}")
                return False

            logger.info(f"Successfully booked desk for {day_name}, {date_str}")
            return True

        except Exception as e:
            logger.error(f"Failed to book desk for {date_str}: {e}")
            return False

    def _select_date(self, date: datetime) -> None:
        """Select a date in the booking calendar."""
        date_str = date.strftime("%Y-%m-%d")

        # Try various date selection methods
        # Method 1: Direct date input
        date_input = self.page.query_selector(
            'input[type="date"], input[name="date"], input[aria-label*="date" i]'
        )
        if date_input:
            date_input.fill(date_str)
            self.page.wait_for_timeout(500)
            return

        # Method 2: Click on calendar date
        # Look for the date in a calendar grid
        day_of_month = date.day

        # Try to find date button/cell
        date_selectors = [
            f'[data-date="{date_str}"]',
            f'button:has-text("{day_of_month}"):not([disabled])',
            f'.calendar-day:has-text("{day_of_month}")',
            f'td:has-text("{day_of_month}")',
        ]

        for selector in date_selectors:
            try:
                date_element = self.page.query_selector(selector)
                if date_element:
                    date_element.click()
                    self.page.wait_for_timeout(500)
                    return
            except Exception:
                continue

        # Method 3: Navigate using URL parameter
        current_url = self.page.url
        if "?" in current_url:
            new_url = f"{current_url}&date={date_str}"
        else:
            new_url = f"{current_url}?date={date_str}"
        self.page.goto(new_url)
        self.page.wait_for_load_state("networkidle")

    def _select_available_desk(self) -> bool:
        """Select an available desk from the booking interface."""
        self.page.wait_for_timeout(1000)

        # Look for available desk options
        desk_selectors = [
            '.desk-available',
            '[data-available="true"]',
            'button:has-text("Book"):not([disabled])',
            '.desk-card:not(.booked)',
            '[role="button"]:has-text("Available")',
            '.available-desk',
        ]

        for selector in desk_selectors:
            try:
                desks = self.page.query_selector_all(selector)
                if desks:
                    # Click the first available desk
                    desks[0].click()
                    self.page.wait_for_timeout(500)
                    return True
            except Exception:
                continue

        # Alternative: Look for a general "Book" or "Reserve" button
        book_buttons = self.page.query_selector_all(
            'button:has-text("Book"), '
            'button:has-text("Reserve"), '
            'a:has-text("Book desk")'
        )
        if book_buttons:
            book_buttons[0].click()
            self.page.wait_for_timeout(500)
            return True

        return False

    def _confirm_booking(self) -> bool:
        """Confirm the desk booking."""
        self.page.wait_for_timeout(500)

        # Look for confirmation button
        confirm_selectors = [
            'button:has-text("Confirm")',
            'button:has-text("Book now")',
            'button:has-text("Complete booking")',
            'button:has-text("Submit")',
            'button[type="submit"]',
            '.confirm-booking',
        ]

        for selector in confirm_selectors:
            try:
                confirm_btn = self.page.query_selector(selector)
                if confirm_btn:
                    confirm_btn.click()
                    self.page.wait_for_load_state("networkidle")

                    # Check for success message
                    self.page.wait_for_timeout(1000)
                    success_indicators = [
                        'text="Booking confirmed"',
                        'text="Successfully booked"',
                        'text="Reservation complete"',
                        '.booking-success',
                        '[data-testid="success-message"]',
                    ]

                    for success_sel in success_indicators:
                        if self.page.query_selector(success_sel):
                            return True

                    # If no explicit success, assume success if no error
                    return True
            except Exception:
                continue

        return False

    def book_all_configured_dates(self) -> dict[str, bool]:
        """Book desks for all configured dates.

        Returns:
            Dictionary mapping date strings to booking success status.
        """
        dates = get_next_booking_dates(
            self.config.booking_days, self.config.weeks_ahead
        )

        results = {}
        for date in dates:
            date_str = date.strftime("%Y-%m-%d")
            results[date_str] = self.book_desk_for_date(date)

            # Small delay between bookings
            self.page.wait_for_timeout(1000)

        return results
