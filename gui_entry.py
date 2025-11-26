#!/usr/bin/env python3
"""GUI entry point for packaged application."""

import sys
import os


def main():
    """Launch the WeWork Booker GUI."""
    # Ensure proper working directory for packaged app
    if getattr(sys, 'frozen', False):
        # Running as packaged app - set working directory to app location
        app_dir = os.path.dirname(sys.executable)
        if sys.platform == 'darwin':
            # On Mac, go up from MacOS folder to Resources
            app_dir = os.path.dirname(app_dir)
        os.chdir(app_dir)

    from wework_booker.gui.app import run
    run()


if __name__ == '__main__':
    main()
