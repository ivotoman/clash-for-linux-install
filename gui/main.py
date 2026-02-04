#!/usr/bin/env python3
"""Clash VPN Manager - GTK4 Desktop Application."""
import sys
import os

# Add the gui directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from application import ClashGUIApplication


def main():
    """Entry point."""
    app = ClashGUIApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
