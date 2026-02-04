#!/usr/bin/env python3
"""System tray helper for Clash VPN Manager (GTK3-based)."""
import os
import sys
import signal
import subprocess

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, GLib, AyatanaAppIndicator3 as AppIndicator

# Path to the main app
APP_PATH = "/opt/clash-vpn-manager/clash-vpn-manager"
# Path to check if VPN is running
SERVICE_NAME = "mihomo"


class TrayIcon:
    """System tray icon for Clash VPN Manager."""

    def __init__(self):
        self.indicator = AppIndicator.Indicator.new(
            "clash-vpn-manager-tray",
            "clash-vpn-manager",
            AppIndicator.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self.indicator.set_title("Clash VPN Manager")

        self.build_menu()

        # Update menu every 2 seconds to reflect VPN status
        GLib.timeout_add_seconds(2, self.update_menu_status)

    def build_menu(self):
        """Build the tray menu."""
        self.menu = Gtk.Menu()

        # Show window
        show_item = Gtk.MenuItem(label="Show Window")
        show_item.connect("activate", self.on_show)
        self.menu.append(show_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        # Connect/Disconnect
        self.connect_item = Gtk.MenuItem(label="Connect VPN")
        self.connect_item.connect("activate", self.on_toggle_vpn)
        self.menu.append(self.connect_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        # Quit
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self.on_quit)
        self.menu.append(quit_item)

        self.menu.show_all()
        self.indicator.set_menu(self.menu)

    def is_vpn_running(self):
        """Check if VPN service is running."""
        try:
            result = subprocess.run(
                ["pgrep", "-x", SERVICE_NAME],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except Exception:
            return False

    def update_menu_status(self):
        """Update menu item labels based on VPN status."""
        if self.is_vpn_running():
            self.connect_item.set_label("Disconnect VPN")
            self.indicator.set_icon_full("clash-vpn-manager", "Connected")
        else:
            self.connect_item.set_label("Connect VPN")
            self.indicator.set_icon_full("clash-vpn-manager", "Disconnected")
        return True  # Keep timer running

    def on_show(self, item):
        """Show the main window."""
        try:
            subprocess.Popen([APP_PATH], start_new_session=True)
        except Exception as e:
            print(f"Error showing window: {e}")

    def on_toggle_vpn(self, item):
        """Toggle VPN connection."""
        try:
            if self.is_vpn_running():
                subprocess.run(["clashoff"], timeout=10)
            else:
                subprocess.run(["clashon"], timeout=10)
            # Update menu after a short delay
            GLib.timeout_add(500, self.update_menu_status)
        except Exception as e:
            print(f"Error toggling VPN: {e}")

    def on_quit(self, item):
        """Quit the tray and the main application."""
        try:
            # Stop VPN if running
            if self.is_vpn_running():
                subprocess.run(["clashoff"], timeout=10)
            # Kill the main app if running
            subprocess.run(["pkill", "-f", "clash-vpn-manager"], timeout=5)
        except Exception:
            pass
        Gtk.main_quit()


def main():
    # Handle SIGTERM gracefully
    signal.signal(signal.SIGTERM, lambda s, f: Gtk.main_quit())
    signal.signal(signal.SIGINT, lambda s, f: Gtk.main_quit())

    tray = TrayIcon()
    Gtk.main()


if __name__ == "__main__":
    main()
