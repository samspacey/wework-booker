# WeWork Desk Booker

Automated desk booking for WeWork using browser automation.

## Features

- Automatically book desks at your preferred WeWork location
- Schedule bookings for specific days (e.g., every Wednesday and Thursday)
- Run as a one-time booking or as a scheduled daemon
- Configurable booking window (how many weeks ahead to book)

## Prerequisites

- Python 3.10+
- A WeWork membership with desk booking access

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/samspacey/wework-booker.git
   cd wework-booker
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```

5. Configure your credentials:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your WeWork credentials and preferences.

## Configuration

Edit the `.env` file with your settings:

```env
# WeWork Credentials
WEWORK_EMAIL=your-email@example.com
WEWORK_PASSWORD=your-password

# Booking Configuration
WEWORK_LOCATION=10 York Road
BOOKING_DAYS=wednesday,thursday

# Optional: Run in headless mode (set to false for debugging)
HEADLESS=true

# Optional: How many weeks ahead to book (default: 2)
WEEKS_AHEAD=2
```

## Usage

### Run a one-time booking

Book desks for all configured days in the upcoming weeks:

```bash
python main.py book
```

### Preview dates to book

See which dates would be booked without actually booking:

```bash
python main.py show-dates
```

### Test your login

Verify your credentials work (runs with visible browser):

```bash
python main.py test-login
```

### Run as a scheduled service

Start the scheduler to automatically book desks daily:

```bash
python main.py schedule --time 09:00
```

This will run the booking process every day at 9:00 AM.

### Debug mode

Add `--debug` for verbose logging:

```bash
python main.py --debug book
```

## Running as a System Service

### Using systemd (Linux)

1. Create a service file `/etc/systemd/system/wework-booker.service`:

   ```ini
   [Unit]
   Description=WeWork Desk Booker
   After=network.target

   [Service]
   Type=simple
   User=your-username
   WorkingDirectory=/path/to/wework-booker
   ExecStart=/path/to/wework-booker/venv/bin/python main.py schedule --time 09:00
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

2. Enable and start the service:
   ```bash
   sudo systemctl enable wework-booker
   sudo systemctl start wework-booker
   ```

### Using cron

Add to your crontab (`crontab -e`):

```cron
# Run desk booking every day at 9:00 AM
0 9 * * * cd /path/to/wework-booker && /path/to/venv/bin/python main.py book
```

## Troubleshooting

### Login issues

1. Run with `test-login` to see the browser:
   ```bash
   python main.py test-login
   ```

2. Set `HEADLESS=false` in `.env` to watch the automation

3. WeWork may use different login flows (SSO, MFA). You may need to adjust the login selectors in `wework_booker/browser.py`

### Booking failures

- Check the log file `wework_booker.log` for detailed error messages
- WeWork's UI may change; selectors in `wework_booker/booker.py` may need updating
- Ensure desks are actually available for your selected dates

### Browser issues

If Playwright has issues:
```bash
playwright install --force chromium
```

## Project Structure

```
wework-booker/
├── main.py                 # CLI entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Example configuration
├── .gitignore
├── README.md
└── wework_booker/
    ├── __init__.py
    ├── config.py          # Configuration management
    ├── browser.py         # Browser automation
    ├── booker.py          # Booking logic
    └── scheduler.py       # Scheduling logic
```

## Notes

- The selectors used for login and booking are based on common patterns and may need adjustment for your specific WeWork portal
- WeWork may have rate limiting or bot detection; use responsibly
- Always test with `test-login` and `show-dates` before running automated bookings

## License

MIT
