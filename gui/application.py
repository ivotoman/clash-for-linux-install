"""GTK Application class."""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk

from window import MainWindow


class ClashGUIApplication(Adw.Application):
    """Main GTK Application."""

    def __init__(self):
        super().__init__(application_id="com.clashgui.ClashGUI")
        self.window = None

    def do_startup(self):
        """Called when application starts."""
        Adw.Application.do_startup(self)
        self._load_css()

    def do_activate(self):
        """Called when application is activated."""
        if not self.window:
            self.window = MainWindow(self)
        self.window.present()

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
        """

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
