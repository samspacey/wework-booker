"""Background thread for booking operations."""

import logging
from PyQt6.QtCore import QThread, pyqtSignal

from ..browser import WeWorkBrowser
from ..booker import DeskBooker, get_next_booking_dates
from ..config import Config

logger = logging.getLogger(__name__)


class BookingThread(QThread):
    """Thread for running booking operations without blocking the UI."""

    status_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    booking_result = pyqtSignal(str, bool)
    finished_booking = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, config: Config):
        super().__init__()
        self.config = config

    def run(self):
        """Execute the booking process."""
        results = {}

        try:
            # Calculate dates to book
            dates = get_next_booking_dates(
                self.config.booking_days, self.config.weeks_ahead
            )

            if not dates:
                self.error_occurred.emit("No dates to book based on configuration")
                self.finished_booking.emit({})
                return

            total_dates = len(dates)
            self.status_update.emit(f"Found {total_dates} dates to book")

            # Start browser
            self.status_update.emit("Starting browser...")

            with WeWorkBrowser(self.config) as browser:
                # Login
                self.status_update.emit("Logging in to WeWork...")
                if not browser.login():
                    self.error_occurred.emit("Failed to login to WeWork")
                    self.finished_booking.emit({})
                    return

                self.status_update.emit("Login successful")

                # Navigate to booking page
                self.status_update.emit("Navigating to booking page...")
                if not browser.navigate_to_desk_booking():
                    self.error_occurred.emit("Failed to navigate to booking page")
                    self.finished_booking.emit({})
                    return

                # Create booker
                booker = DeskBooker(browser.page, self.config)

                # Select location
                self.status_update.emit(f"Selecting location: {self.config.location}")
                booker.select_location()

                # Book each date
                for i, date in enumerate(dates):
                    date_str = date.strftime("%Y-%m-%d")
                    self.status_update.emit(f"Booking {date_str}...")

                    success = booker.book_desk_for_date(date)
                    results[date_str] = success

                    self.booking_result.emit(date_str, success)

                    # Update progress
                    progress = int(((i + 1) / total_dates) * 100)
                    self.progress_update.emit(progress)

                    # Small delay between bookings
                    browser.page.wait_for_timeout(500)

            self.status_update.emit("Booking complete")
            self.finished_booking.emit(results)

        except Exception as e:
            logger.error(f"Booking thread error: {e}")
            self.error_occurred.emit(str(e))
            self.finished_booking.emit(results)
