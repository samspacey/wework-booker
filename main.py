#!/usr/bin/env python3
"""WeWork Desk Booking Automation - Main Entry Point."""

import logging
import sys
import click

from wework_booker.config import Config
from wework_booker.scheduler import run_once, start_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("wework_booker.log"),
    ],
)

logger = logging.getLogger(__name__)


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging and save screenshots")
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    """WeWork Desk Booking Automation Tool."""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)


@cli.command()
@click.pass_context
def book(ctx: click.Context) -> None:
    """Run the booking process once immediately."""
    logger.info("Running one-time booking...")

    try:
        config = Config.from_env()
        config.debug = ctx.obj.get("debug", False)
        logger.info(f"Location: {config.location}")
        logger.info(f"Booking days: {', '.join(config.booking_days)}")
        logger.info(f"Weeks ahead: {config.weeks_ahead}")

        results = run_once(config)

        if results:
            success_count = sum(1 for v in results.values() if v)
            total_count = len(results)
            logger.info(f"Booking complete: {success_count}/{total_count} successful")

            for date_str, success in results.items():
                status = "OK" if success else "FAILED"
                click.echo(f"  {date_str}: {status}")
        else:
            logger.warning("No bookings were made")
            sys.exit(1)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        click.echo(f"Error: {e}", err=True)
        click.echo("Make sure to copy .env.example to .env and fill in your credentials", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Booking failed: {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--time",
    "run_time",
    default="09:00",
    help="Time to run daily booking (24-hour format, e.g., 09:00)",
)
def schedule(run_time: str) -> None:
    """Start the scheduler for automated daily bookings."""
    logger.info("Starting scheduler mode...")

    try:
        config = Config.from_env()
        logger.info(f"Location: {config.location}")
        logger.info(f"Booking days: {', '.join(config.booking_days)}")
        logger.info(f"Scheduled run time: {run_time}")

        start_scheduler(config, run_time)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Scheduler failed: {e}")
        sys.exit(1)


@cli.command()
def test_login() -> None:
    """Test the WeWork login process (runs in visible browser)."""
    logger.info("Testing login (browser will be visible)...")

    try:
        config = Config.from_env()
        # Override headless for testing
        config.headless = False

        from wework_booker.browser import WeWorkBrowser

        with WeWorkBrowser(config) as browser:
            if browser.login():
                click.echo("Login successful!")
                click.echo("Browser will stay open for 10 seconds for verification...")
                browser.page.wait_for_timeout(10000)
            else:
                click.echo("Login failed!", err=True)
                sys.exit(1)

    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)


@cli.command()
def show_dates() -> None:
    """Show the dates that would be booked based on current configuration."""
    try:
        config = Config.from_env()

        from wework_booker.booker import get_next_booking_dates

        dates = get_next_booking_dates(config.booking_days, config.weeks_ahead)

        click.echo(f"Location: {config.location}")
        click.echo(f"Booking days: {', '.join(config.booking_days)}")
        click.echo(f"Weeks ahead: {config.weeks_ahead}")
        click.echo()
        click.echo("Dates to book:")
        for date in dates:
            click.echo(f"  {date.strftime('%A, %Y-%m-%d')}")

    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)


@cli.command()
def gui() -> None:
    """Launch the graphical user interface."""
    from wework_booker.gui import BookingApp
    from wework_booker.gui.app import run

    logger.info("Launching GUI...")
    run()


if __name__ == "__main__":
    cli()
