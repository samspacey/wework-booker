"""Scheduling for automated desk bookings."""

import logging
import schedule
import time
from datetime import datetime

from .browser import WeWorkBrowser
from .booker import DeskBooker
from .config import Config

logger = logging.getLogger(__name__)


def run_booking_job(config: Config) -> dict[str, bool]:
    """Execute a single booking job.

    Args:
        config: Application configuration

    Returns:
        Dictionary of booking results
    """
    logger.info(f"Starting booking job at {datetime.now()}")

    try:
        with WeWorkBrowser(config) as browser:
            # Login to WeWork
            if not browser.login():
                logger.error("Failed to login to WeWork")
                return {}

            # Navigate to booking page
            if not browser.navigate_to_desk_booking():
                logger.error("Failed to navigate to booking page")
                return {}

            # Create booker and run bookings
            booker = DeskBooker(browser.page, config)

            # Select location
            if not booker.select_location():
                logger.warning("Location selection may have failed")

            # Book all configured dates
            results = booker.book_all_configured_dates()

            # Log results
            for date_str, success in results.items():
                status = "SUCCESS" if success else "FAILED"
                logger.info(f"Booking for {date_str}: {status}")

            return results

    except Exception as e:
        logger.error(f"Booking job failed: {e}")
        return {}


def start_scheduler(config: Config, run_time: str = "09:00") -> None:
    """Start the booking scheduler.

    Args:
        config: Application configuration
        run_time: Time to run the daily booking job (24-hour format, e.g., "09:00")
    """
    logger.info(f"Starting scheduler - will run daily at {run_time}")

    # Schedule the job
    schedule.every().day.at(run_time).do(run_booking_job, config=config)

    # Also run on specific days if you want more control
    # schedule.every().monday.at(run_time).do(run_booking_job, config=config)

    logger.info("Scheduler started. Press Ctrl+C to stop.")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")


def run_once(config: Config) -> dict[str, bool]:
    """Run the booking job once immediately.

    Args:
        config: Application configuration

    Returns:
        Dictionary of booking results
    """
    return run_booking_job(config)
