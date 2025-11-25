"""Desk booking logic for WeWork."""

from __future__ import annotations

import logging
import re
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

        # Save debug output only if debug mode is enabled
        if self.config.debug:
            self.page.screenshot(path=f"debug_booking_{date_str}.png")
            logger.debug(f"Screenshot saved to debug_booking_{date_str}.png")
            html_content = self.page.content()
            with open(f"debug_booking_{date_str}.html", "w") as f:
                f.write(html_content)
            logger.debug(f"HTML saved to debug_booking_{date_str}.html")

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
        target_day = date.day
        target_month_short = date.strftime("%b")  # Short month name like "Nov"
        target_month_full = date.strftime("%B")   # Full month name like "November"
        target_year = date.year

        logger.debug(f"Selecting date: {target_day} {target_month_full} {target_year}")

        # Click on the date fieldset to open calendar
        # The UI shows: Date fieldset containing "Nov 25, 2025", "Today" button, and calendar icon
        try:
            # Try multiple selectors for the date picker
            date_selectors = [
                'fieldset:has-text("Date")',
                '[class*="date-picker"]',
                '[class*="datepicker"]',
                'button:has-text("Today")',  # The "Today" button is inside the date area
                '[aria-label*="date" i]',
                'input[type="date"]',
            ]

            date_field = None
            for selector in date_selectors:
                try:
                    date_field = self.page.locator(selector).first
                    if date_field and date_field.is_visible():
                        logger.debug(f"Found date field with selector: {selector}")
                        date_field.click()
                        self.page.wait_for_timeout(1000)
                        logger.debug("Clicked on date field")
                        break
                except Exception:
                    continue

            # If no date picker found, try clicking on the calendar icon
            if not date_field:
                calendar_icon = self.page.locator('svg, [class*="calendar-icon"], [class*="icon-calendar"]').first
                if calendar_icon:
                    calendar_icon.click()
                    self.page.wait_for_timeout(400)
                    logger.debug("Clicked on calendar icon")

        except Exception as e:
            logger.debug(f"Could not click date field: {e}")

        # Take screenshot to see calendar state
        if self.config.debug:
            self.page.screenshot(path="debug_calendar.png")

        # Check if a calendar popup appeared
        self.page.wait_for_timeout(200)

        # Navigate to correct month if needed
        for _ in range(6):  # Max 6 months ahead
            try:
                # Check if we're on the right month by looking at calendar header
                page_text = self.page.content()
                # If we see our target month in a calendar context, we're good
                if (target_month_full in page_text or target_month_short in page_text) and str(target_year) in page_text:
                    logger.debug(f"Found target month {target_month_full} {target_year} in page")
                    break

                # Try to find and click next month button
                next_selectors = [
                    '[aria-label*="next" i]',
                    '[aria-label*="forward" i]',
                    'button:has-text(">")',
                    'button:has-text("→")',
                    '[class*="next"]',
                    '[class*="forward"]',
                ]
                clicked = False
                for sel in next_selectors:
                    try:
                        next_btn = self.page.locator(sel).first
                        if next_btn and next_btn.is_visible():
                            next_btn.click()
                            self.page.wait_for_timeout(200)
                            clicked = True
                            break
                    except Exception:
                        continue

                if not clicked:
                    break

            except Exception:
                break

        # Click on the day number
        try:
            # Format the day we're looking for
            # The calendar shows days as numbers

            # Try to find the exact day button
            # Use XPath to find a button/element with exact text matching the day number
            day_locator = self.page.locator(f'[role="gridcell"]:has-text("{target_day}"), button:has-text("{target_day}")')

            # Get all matching elements and click the one that's just the number
            day_elements = day_locator.all()
            for elem in day_elements:
                try:
                    text = elem.inner_text().strip()
                    # Make sure it's exactly the day number (not "25 desks" etc)
                    if text == str(target_day):
                        elem.click()
                        self.page.wait_for_timeout(400)
                        logger.info(f"Selected date: {target_day} {target_month_full}")
                        return
                except Exception:
                    continue

            # Alternative: look for aria-label with the date
            date_formatted = date.strftime("%B %d, %Y")  # e.g., "November 26, 2025"
            date_btn = self.page.locator(f'[aria-label*="{target_day}"], [aria-label*="{date_formatted}"]').first
            if date_btn:
                date_btn.click()
                self.page.wait_for_timeout(400)
                logger.info(f"Selected date via aria-label: {target_day} {target_month_full}")
                return

        except Exception as e:
            logger.debug(f"Error finding day button: {e}")

        logger.warning(f"Could not select date {date_str} in calendar")

    def _select_available_desk(self) -> bool:
        """Select an available desk from the booking interface."""
        location = self.config.location
        logger.debug(f"Looking for location: {location}")

        # Wait for location cards to load using smart wait
        logger.debug("Waiting for location cards to load...")
        try:
            # Wait for our specific location to appear in a card title
            self.page.locator(f'.card-title:has-text("{location}")').wait_for(
                state="visible", timeout=15000
            )
            logger.debug(f"Found location card for: {location}")
        except Exception:
            # Fallback: wait for any location card to appear
            try:
                self.page.locator('.location-card .card-title').first.wait_for(
                    state="visible", timeout=10000
                )
            except Exception:
                logger.debug("Location cards not found, proceeding anyway")

        # Take a screenshot to see current state
        if self.config.debug:
            self.page.screenshot(path="debug_location_search.png")

        try:
            # The "Book a desk" button in WeWork only appears on hover (CSS: .desk-card:hover .book-desk-button)
            # So we need to: 1) Find the location card, 2) Hover to reveal button, 3) Click button

            # Find the location card that contains our location
            logger.debug("Looking for location card...")

            # Find the card with our location name - it's a .location-card with .card-title containing location
            location_cards = self.page.locator('.location-card').all()
            logger.debug(f"Found {len(location_cards)} .location-card elements")

            for card in location_cards:
                try:
                    card_text = card.inner_text()
                    if location in card_text:
                        logger.info(f"Found location card for: {location}")

                        # Hover over the card to reveal the "Book a desk" button
                        card.hover()
                        self.page.wait_for_timeout(200)  # Wait for hover effect
                        logger.debug("Hovered over location card")

                        # Now find and click the book button within this card
                        book_btn = card.locator('.book-desk-button').first
                        if book_btn:
                            # Check if visible after hover
                            self.page.wait_for_timeout(100)
                            book_btn.click()
                            # Wait for confirmation dialog to appear
                            try:
                                self.page.locator('button:has-text("Book for")').wait_for(state="visible", timeout=5000)
                            except Exception:
                                self.page.wait_for_timeout(500)  # Fallback
                            if self.config.debug:
                                self.page.screenshot(path="debug_after_book_click.png")
                            logger.info("Clicked 'Book a desk' button")
                            return True

                        # Try alternative: role=button with "Book a desk"
                        role_btn = card.locator('[role="button"]:has-text("Book a desk")').first
                        if role_btn:
                            role_btn.click()
                            try:
                                self.page.locator('button:has-text("Book for")').wait_for(state="visible", timeout=5000)
                            except Exception:
                                self.page.wait_for_timeout(500)
                            if self.config.debug:
                                self.page.screenshot(path="debug_after_book_click.png")
                            logger.info("Clicked 'Book a desk' button via role selector")
                            return True

                        # Try clicking on the card itself as fallback
                        logger.debug("Book button not found in card, clicking card...")
                        card.click()
                        try:
                            self.page.locator('button:has-text("Book for")').wait_for(state="visible", timeout=5000)
                        except Exception:
                            self.page.wait_for_timeout(500)
                        if self.config.debug:
                            self.page.screenshot(path="debug_after_book_click.png")
                        logger.info("Clicked on location card directly")
                        return True

                except Exception as e:
                    logger.debug(f"Error processing card: {e}")
                    continue

            # Strategy 2: Try finding cards by text content directly
            logger.debug("Strategy 2: Finding card by text content...")
            loc_elem = self.page.locator(f'.card-title:has-text("{location}")').first

            if loc_elem and loc_elem.is_visible():
                # Get the parent card
                # Navigate up to find the .location-card parent
                logger.debug("Found location title, looking for parent card...")

                # Use JavaScript to find and click the parent card, then the button
                self.page.evaluate(f'''
                    () => {{
                        const titles = document.querySelectorAll('.card-title');
                        for (const title of titles) {{
                            if (title.textContent.includes("{location}")) {{
                                let card = title.closest('.location-card');
                                if (card) {{
                                    // Trigger hover
                                    card.dispatchEvent(new MouseEvent('mouseenter', {{bubbles: true}}));
                                    // Click after short delay
                                    setTimeout(() => {{
                                        const btn = card.querySelector('.book-desk-button');
                                        if (btn) btn.click();
                                        else card.click();
                                    }}, 300);
                                    return true;
                                }}
                            }}
                        }}
                        return false;
                    }}
                ''')
                self.page.wait_for_timeout(800)
                if self.config.debug:
                    self.page.screenshot(path="debug_after_book_click.png")
                logger.info("Clicked via JavaScript")
                return True

        except Exception as e:
            logger.error(f"Error finding location: {e}")

        logger.warning(f"Could not find location: {location}")
        return False

    def _confirm_booking(self) -> bool:
        """Confirm the desk booking.

        Only confirms if the booking costs 0 credits.
        If it costs more than 0 credits, it means a desk is already booked.
        """
        self.page.wait_for_timeout(500)

        # Take screenshot of confirmation dialog
        if self.config.debug:
            self.page.screenshot(path="debug_confirm_dialog.png")

        try:
            # Look for the "Book for X credit" button in the confirmation dialog
            # The button text is like "Book for 0 credit" or "Book for 1 credit"
            book_btn = self.page.locator('button:has-text("Book for")').first

            if book_btn and book_btn.is_visible():
                btn_text = book_btn.inner_text()
                logger.debug(f"Found confirmation button: {btn_text}")

                # Extract the number of credits from button text
                # Expected format: "Book for X credit" or "Book for X credits"
                credit_match = re.search(r'Book for (\d+)', btn_text)

                if credit_match:
                    credits = int(credit_match.group(1))
                    logger.info(f"Booking would cost {credits} credits")

                    if credits == 0:
                        # Free booking - proceed
                        logger.info("Booking is free (0 credits), confirming...")
                        book_btn.click()

                        # Wait for confirmation popup to appear
                        logger.debug("Waiting for confirmation popup...")
                        self.page.wait_for_timeout(1500)

                        # Check for success
                        if self.config.debug:
                            self.page.screenshot(path="debug_after_confirm.png")

                        # Look for "Done" button to close the success popup
                        # Try multiple selectors for the Done button
                        done_selectors = [
                            'button:has-text("Done")',
                            '[role="button"]:has-text("Done")',
                            'span:has-text("Done")',
                            '.btn:has-text("Done")',
                        ]

                        done_clicked = False
                        for sel in done_selectors:
                            try:
                                done_btn = self.page.locator(sel).first
                                if done_btn:
                                    # Wait up to 5 seconds for button to become visible
                                    try:
                                        done_btn.wait_for(state="visible", timeout=5000)
                                        logger.debug(f"Found 'Done' button with selector: {sel}")
                                        done_btn.click()
                                        self.page.wait_for_timeout(1000)
                                        logger.info("Clicked 'Done' button, booking confirmed!")
                                        done_clicked = True
                                        break
                                    except Exception:
                                        continue
                            except Exception:
                                continue

                        if done_clicked:
                            return True

                        # Fallback: Look for success indicators
                        logger.debug("Done button not found, checking for success indicators...")
                        success_indicators = [
                            'text="Booking confirmed"',
                            'text="Successfully booked"',
                            'text="Reservation complete"',
                            '.booking-success',
                        ]

                        for success_sel in success_indicators:
                            if self.page.locator(success_sel).count() > 0:
                                logger.info("Booking confirmed (success indicator found)!")
                                return True

                        # If dialog closed, assume success
                        if self.page.locator('.pageslide-backdrop.open').count() == 0:
                            logger.info("Booking dialog closed - assuming success")
                            return True

                        return True
                    else:
                        # Costs credits - desk already booked for this date
                        logger.info(f"Booking costs {credits} credits - desk already booked for this date, skipping")
                        # Click Cancel to close dialog
                        cancel_btn = self.page.locator('button:has-text("Cancel")').first
                        if cancel_btn and cancel_btn.is_visible():
                            cancel_btn.click()
                            self.page.wait_for_timeout(400)
                        return False

            # Fallback: look for any confirm-like button
            logger.debug("Looking for fallback confirm button...")
            confirm_selectors = [
                'button:has-text("Confirm")',
                'button:has-text("Book now")',
                'button:has-text("Complete")',
            ]

            for selector in confirm_selectors:
                try:
                    confirm_btn = self.page.locator(selector).first
                    if confirm_btn and confirm_btn.is_visible():
                        confirm_btn.click()
                        self.page.wait_for_timeout(2000)
                        return True
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Error in confirmation: {e}")

        # Close any open dialog before returning
        try:
            cancel_btn = self.page.locator('button:has-text("Cancel")').first
            if cancel_btn and cancel_btn.is_visible():
                cancel_btn.click()
                self.page.wait_for_timeout(500)
        except Exception:
            pass

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
            self.page.wait_for_timeout(500)

        return results
