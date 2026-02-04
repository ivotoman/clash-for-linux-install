"""GTK Application class."""
import os
import subprocess
import signal

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, GLib, Gio

from window import MainWindow

# Tray helper script path
TRAY_HELPER_PATH = "/opt/clash-vpn-manager/tray_helper.py"


class ClashGUIApplication(Adw.Application):
    """Main GTK Application."""

    def __init__(self):
        super().__init__(
            application_id="com.clashgui.ClashGUI",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.window = None
        self.tray_process = None

    def do_startup(self):
        """Called when application starts."""
        Adw.Application.do_startup(self)
        self._load_css()
        self._setup_actions()
        self._start_tray_helper()
        # Hold the application so it doesn't quit when window closes
        self.hold()

    def _start_tray_helper(self):
        """Start the tray helper process if not already running."""
        try:
            # Check if tray helper is already running
            result = subprocess.run(
                ["pgrep", "-f", "tray_helper.py"],
                capture_output=True
            )
            if result.returncode == 0:
                return  # Already running

            # Start tray helper
            if os.path.exists(TRAY_HELPER_PATH):
                self.tray_process = subprocess.Popen(
                    ["python3", TRAY_HELPER_PATH],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
        except Exception as e:
            print(f"Could not start tray helper: {e}")

    def _stop_tray_helper(self):
        """Stop the tray helper process."""
        try:
            subprocess.run(["pkill", "-f", "tray_helper.py"], timeout=5)
        except Exception:
            pass
        if self.tray_process:
            try:
                self.tray_process.terminate()
            except Exception:
                pass

    def do_activate(self):
        """Called when application is activated (also when clicked again)."""
        if not self.window:
            self.window = MainWindow(self)
            # Connect close request to hide instead of destroy
            self.window.connect("close-request", self._on_window_close)
        self.window.present()

    def _on_window_close(self, window):
        """Hide window instead of closing when X is clicked."""
        window.hide()
        # Show notification that app is still running
        if not hasattr(self, '_notified_background'):
            self._notified_background = True
            notif = Gio.Notification.new("Clash VPN Manager")
            notif.set_body("Running in background. Click the app icon to open.")
            notif.set_priority(Gio.NotificationPriority.LOW)
            self.send_notification("background-notice", notif)
        return True  # Prevent default close behavior

    def _setup_actions(self):
        """Set up application actions."""
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self._on_quit)
        self.add_action(quit_action)

    def _on_quit(self, action, param):
        """Quit the application and stop VPN services."""
        if self.window:
            # Stop speed monitor
            self.window._stop_speed_monitor()
            # Stop VPN service
            if self.window.service.is_running():
                self.window.service.stop()
        # Stop tray helper
        self._stop_tray_helper()
        self.release()
        self.quit()

    def _load_css(self):
        """Load custom CSS styles."""
        css = b"""
        .status-connected {
            color: #2ec27e;
            font-size: 24px;
        }
        .status-disconnected {
            color: #c01c28;
            font-size: 24px;
        }
        .heading {
            font-weight: bold;
            font-size: 11px;
            letter-spacing: 1px;
            color: alpha(currentColor, 0.7);
        }
        .card {
            background: alpha(currentColor, 0.05);
            border-radius: 12px;
        }
        .speed-down {
            color: #2ec27e;
            font-weight: bold;
        }
        .speed-up {
            color: #3584e4;
            font-weight: bold;
        }
        """

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
