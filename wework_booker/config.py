"""Configuration management for WeWork Booker."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration."""

    email: str
    password: str
    location: str
    booking_days: list[str]
    headless: bool
    weeks_ahead: int
    debug: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        load_dotenv(override=True)

        email = os.getenv("WEWORK_EMAIL")
        password = os.getenv("WEWORK_PASSWORD")

        if not email or not password:
            raise ValueError(
                "WEWORK_EMAIL and WEWORK_PASSWORD must be set in .env file"
            )

        location = os.getenv("WEWORK_LOCATION", "10 York Road")

        days_str = os.getenv("BOOKING_DAYS", "wednesday,thursday")
        booking_days = [day.strip().lower() for day in days_str.split(",")]

        headless = os.getenv("HEADLESS", "true").lower() == "true"
        weeks_ahead = int(os.getenv("WEEKS_AHEAD", "2"))

        return cls(
            email=email,
            password=password,
            location=location,
            booking_days=booking_days,
            headless=headless,
            weeks_ahead=weeks_ahead,
        )
