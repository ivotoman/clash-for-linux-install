"""Main application window."""
import os
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio

from config_reader import ConfigReader
from clash_api import ClashAPI
from service_manager import ServiceManager
from quota_parser import QuotaParser, format_bytes

# Autostart desktop file location
AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_FILE = AUTOSTART_DIR / "clash-vpn-manager.desktop"
DESKTOP_FILE_PATH = "/usr/share/applications/clash-vpn-manager.desktop"


class MainWindow(Adw.ApplicationWindow):
    """Main application window."""

    def __init__(self, app):
        super().__init__(application=app, title="Clash VPN Manager")
        self.set_default_size(750, 500)

        # Initialize components
        self.config = ConfigReader()
        host, port, secret = self.config.get_api_settings()
        self.api = ClashAPI(host, port, secret)
        self.service = ServiceManager(
            self.config.get_kernel_path(),
            self.config.resources_dir
        )
        self.quota_parser = QuotaParser()

        # Current state
        self.current_proxy = None
        self.proxy_group = "🔰 节点选择"  # Default selector group

        # Traffic tracking for speed calculation
        self.last_download = 0
        self.last_upload = 0
        self.speed_timer_id = None

        # Build UI
        self._build_ui()

        # Start speed monitoring
        self._start_speed_monitor()

        # Initial refresh
        GLib.timeout_add(500, self._initial_refresh)

    def _build_ui(self):
        """Build the user interface with two-panel layout."""
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(main_box)

        # Header bar
        header = Adw.HeaderBar()
        main_box.append(header)

        # Menu button in header
        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("open-menu-symbolic")
        menu_btn.set_tooltip_text("Menu")
        header.pack_end(menu_btn)

        # Create menu
        menu = Gio.Menu()
        menu.append("Launch at Startup", "win.autostart")
        menu.append("About", "win.about")
        menu.append("Quit", "app.quit")
        menu_btn.set_menu_model(menu)

        # Autostart action (toggle)
        self.autostart_action = Gio.SimpleAction.new_stateful(
            "autostart", None, GLib.Variant.new_boolean(self._is_autostart_enabled())
        )
        self.autostart_action.connect("change-state", self._on_autostart_toggled)
        self.add_action(self.autostart_action)

        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

        # Refresh button in header
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh")
        refresh_btn.connect("clicked", lambda b: self._refresh_all())
        header.pack_end(refresh_btn)

        # Two-panel layout
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_vexpand(True)
        paned.set_shrink_start_child(False)
        paned.set_shrink_end_child(False)
        paned.set_position(280)
        main_box.append(paned)

        # Left panel - Server list
        left_panel = self._build_servers_panel()
        paned.set_start_child(left_panel)

        # Right panel - Status, Quota, Subscription
        right_panel = self._build_control_panel()
        paned.set_end_child(right_panel)

    def _build_servers_panel(self):
        """Build the left panel with server list."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_size_request(200, -1)

        # Header with title and test button
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.set_margin_top(12)
        header_box.set_margin_bottom(8)
        header_box.set_margin_start(12)
        header_box.set_margin_end(12)
        box.append(header_box)

        title = Gtk.Label(label="SERVERS")
        title.add_css_class("heading")
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        header_box.append(title)

        test_btn = Gtk.Button(icon_name="network-transmit-receive-symbolic")
        test_btn.set_tooltip_text("Test all servers")
        test_btn.connect("clicked", self._on_test_all_clicked)
        header_box.append(test_btn)

        # Server list
        list_scroll = Gtk.ScrolledWindow()
        list_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        list_scroll.set_vexpand(True)
        box.append(list_scroll)

        self.server_list = Gtk.ListBox()
        self.server_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.server_list.add_css_class("navigation-sidebar")
        self.server_list.connect("row-activated", self._on_server_selected)
        list_scroll.set_child(self.server_list)

        return box

    def _build_control_panel(self):
        """Build the right panel with status, quota, and subscription."""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        scrolled.set_child(content)

        # Status card
        self._build_status_card(content)

        # Quota card
        self._build_quota_card(content)

        # Subscription card
        self._build_subscription_card(content)

        return scrolled

    def _build_status_card(self, parent):
        """Build connection status card."""
        frame = Gtk.Frame()
        frame.add_css_class("card")
        parent.append(frame)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        frame.set_child(box)

        # Title
        title = Gtk.Label(label="CONNECTION STATUS")
        title.add_css_class("heading")
        title.set_halign(Gtk.Align.START)
        box.append(title)

        # Status row
        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.append(status_row)

        # Status indicator (colored circle)
        self.status_indicator = Gtk.Label(label="●")
        self.status_indicator.add_css_class("status-disconnected")
        status_row.append(self.status_indicator)

        # Status text
        status_text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        status_row.append(status_text_box)

        self.status_label = Gtk.Label(label="Disconnected")
        self.status_label.add_css_class("title-3")
        self.status_label.set_halign(Gtk.Align.START)
        status_text_box.append(self.status_label)

        self.server_label = Gtk.Label(label="No server selected")
        self.server_label.add_css_class("dim-label")
        self.server_label.set_halign(Gtk.Align.START)
        status_text_box.append(self.server_label)

        # Controls row
        controls_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        controls_row.set_halign(Gtk.Align.CENTER)
        controls_row.set_margin_top(12)
        box.append(controls_row)

        # Connect/Disconnect button
        self.connect_btn = Gtk.Button(label="Connect")
        self.connect_btn.add_css_class("suggested-action")
        self.connect_btn.add_css_class("pill")
        self.connect_btn.set_size_request(120, -1)
        self.connect_btn.connect("clicked", self._on_connect_clicked)
        controls_row.append(self.connect_btn)

        # TUN mode toggle
        tun_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        tun_box.set_valign(Gtk.Align.CENTER)
        controls_row.append(tun_box)

        tun_label = Gtk.Label(label="TUN")
        tun_label.add_css_class("dim-label")
        tun_box.append(tun_label)

        self.tun_switch = Gtk.Switch()
        self.tun_switch.set_valign(Gtk.Align.CENTER)
        self.tun_switch.connect("state-set", self._on_tun_toggled)
        tun_box.append(self.tun_switch)

        # Speed indicator
        speed_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        speed_box.set_halign(Gtk.Align.CENTER)
        speed_box.set_margin_top(8)
        box.append(speed_box)

        # Download speed
        down_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        down_icon = Gtk.Label(label="↓")
        down_icon.add_css_class("speed-down")
        down_box.append(down_icon)
        self.download_speed_label = Gtk.Label(label="0 KB/s")
        self.download_speed_label.set_width_chars(10)
        self.download_speed_label.set_xalign(0)
        down_box.append(self.download_speed_label)
        speed_box.append(down_box)

        # Upload speed
        up_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        up_icon = Gtk.Label(label="↑")
        up_icon.add_css_class("speed-up")
        up_box.append(up_icon)
        self.upload_speed_label = Gtk.Label(label="0 KB/s")
        self.upload_speed_label.set_width_chars(10)
        self.upload_speed_label.set_xalign(0)
        up_box.append(self.upload_speed_label)
        speed_box.append(up_box)

    def _build_quota_card(self, parent):
        """Build quota information card."""
        frame = Gtk.Frame()
        frame.add_css_class("card")
        parent.append(frame)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        frame.set_child(box)

        # Title
        title = Gtk.Label(label="QUOTA")
        title.add_css_class("heading")
        title.set_halign(Gtk.Align.START)
        box.append(title)

        # Quota text
        self.quota_label = Gtk.Label(label="Loading...")
        self.quota_label.set_halign(Gtk.Align.START)
        box.append(self.quota_label)

        # Progress bar
        self.quota_progress = Gtk.ProgressBar()
        self.quota_progress.set_show_text(False)
        box.append(self.quota_progress)

        # Expiry info
        self.expiry_label = Gtk.Label(label="")
        self.expiry_label.add_css_class("dim-label")
        self.expiry_label.set_halign(Gtk.Align.START)
        box.append(self.expiry_label)

    def _build_subscription_card(self, parent):
        """Build subscription management card."""
        frame = Gtk.Frame()
        frame.add_css_class("card")
        parent.append(frame)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        frame.set_child(box)

        # Title
        title = Gtk.Label(label="SUBSCRIPTION")
        title.add_css_class("heading")
        title.set_halign(Gtk.Align.START)
        box.append(title)

        # URL entry
        self.sub_entry = Gtk.Entry()
        self.sub_entry.set_placeholder_text("Enter subscription URL...")
        box.append(self.sub_entry)

        # Buttons row
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_row.set_halign(Gtk.Align.CENTER)
        box.append(btn_row)

        self.add_btn = Gtk.Button(label="Add")
        self.add_btn.connect("clicked", self._on_add_subscription)
        btn_row.append(self.add_btn)

        self.update_btn = Gtk.Button(label="Update")
        self.update_btn.connect("clicked", self._on_update_subscription)
        btn_row.append(self.update_btn)

    def _initial_refresh(self):
        """Initial refresh after window shown."""
        self._refresh_all()
        return False  # Don't repeat

    def _refresh_all(self):
        """Refresh all data."""
        self._refresh_status()
        self._refresh_quota()
        self._refresh_servers()

    def _refresh_status(self):
        """Refresh connection status."""
        is_running = self.service.is_running()
        is_tun = self.service.is_tun_enabled()

        # Update TUN switch without triggering callback
        self.tun_switch.handler_block_by_func(self._on_tun_toggled)
        self.tun_switch.set_active(is_tun)
        self.tun_switch.handler_unblock_by_func(self._on_tun_toggled)

        if is_running:
            self.status_indicator.set_label("●")
            self.status_indicator.remove_css_class("status-disconnected")
            self.status_indicator.add_css_class("status-connected")
            status_text = "Connected"
            if is_tun:
                status_text += " (TUN)"
            self.status_label.set_label(status_text)
            self.connect_btn.set_label("Disconnect")
            self.connect_btn.remove_css_class("suggested-action")
            self.connect_btn.add_css_class("destructive-action")

            # Get current proxy
            self._update_current_proxy()
        else:
            self.status_indicator.set_label("●")
            self.status_indicator.remove_css_class("status-connected")
            self.status_indicator.add_css_class("status-disconnected")
            self.status_label.set_label("Disconnected")
            self.server_label.set_label("No server selected")
            self.connect_btn.set_label("Connect")
            self.connect_btn.remove_css_class("destructive-action")
            self.connect_btn.add_css_class("suggested-action")

    def _update_current_proxy(self):
        """Update current proxy display."""
        try:
            proxies = self.api.get_proxies()
            if proxies and "proxies" in proxies:
                # Find the main selector group
                for name, info in proxies["proxies"].items():
                    if "节点选择" in name or "Node Selection" in name:
                        self.proxy_group = name
                        if "now" in info:
                            self.current_proxy = info["now"]
                            self.server_label.set_label(f"Server: {self.current_proxy}")
                        break
        except Exception as e:
            print(f"Error updating proxy: {e}")

    def _refresh_quota(self):
        """Refresh quota information."""
        try:
            proxies = self.config.get_proxies()
            quota = self.quota_parser.parse_proxy_names(proxies)

            if quota.remaining_gb is not None and quota.total_gb:
                remaining = format_bytes(quota.remaining_gb)
                total = format_bytes(quota.total_gb)
                self.quota_label.set_label(f"Remaining: {remaining} / {total}")

                # Update progress (show used, not remaining)
                used_percent = quota.usage_percent or 0
                self.quota_progress.set_fraction(used_percent / 100)
            else:
                self.quota_label.set_label("Quota info not available")
                self.quota_progress.set_fraction(0)

            # Expiry info
            if quota.expires_date:
                days = quota.days_left or 0
                self.expiry_label.set_label(f"Expires: {quota.expires_date} ({days} days)")
            elif quota.days_left:
                self.expiry_label.set_label(f"Expires in {quota.days_left} days")
            elif quota.reset_days:
                self.expiry_label.set_label(f"Resets in {quota.reset_days} days")
            else:
                self.expiry_label.set_label("")

        except Exception as e:
            self.quota_label.set_label(f"Error: {e}")

    def _refresh_servers(self):
        """Refresh server list."""
        # Clear existing
        while True:
            row = self.server_list.get_row_at_index(0)
            if row is None:
                break
            self.server_list.remove(row)

        try:
            # Get proxies from API if running, else from config
            if self.service.is_running():
                proxies_data = self.api.get_proxies()
                if proxies_data and "proxies" in proxies_data:
                    # Find selector group
                    for name, info in proxies_data["proxies"].items():
                        if "节点选择" in name or "Node Selection" in name:
                            self.proxy_group = name
                            current = info.get("now", "")
                            all_proxies = info.get("all", [])

                            for proxy_name in all_proxies:
                                # Skip special entries
                                if any(x in proxy_name.lower() for x in ["direct", "reject", "traffic", "expire", "剩余", "到期"]):
                                    continue

                                row = self._create_server_row(proxy_name, proxy_name == current)
                                self.server_list.append(row)
                            break
            else:
                # Fallback to config
                groups = self.config.get_proxy_groups()
                for group in groups:
                    if "节点选择" in group.get("name", "") or "Node Selection" in group.get("name", ""):
                        self.proxy_group = group["name"]
                        for proxy_name in group.get("proxies", []):
                            if any(x in proxy_name.lower() for x in ["direct", "reject", "traffic", "expire", "剩余", "到期"]):
                                continue
                            row = self._create_server_row(proxy_name, False)
                            self.server_list.append(row)
                        break

        except Exception as e:
            print(f"Error refreshing servers: {e}")

    def _create_server_row(self, name: str, selected: bool) -> Gtk.ListBoxRow:
        """Create a server list row."""
        row = Gtk.ListBoxRow()
        row.server_name = name

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(8)
        box.set_margin_end(8)
        row.set_child(box)

        # Selection indicator
        indicator = Gtk.Label(label="●" if selected else "○")
        if selected:
            indicator.add_css_class("accent")
        box.append(indicator)

        # Server name
        label = Gtk.Label(label=name)
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        label.set_max_width_chars(20)
        box.append(label)

        # Delay label
        row.delay_label = Gtk.Label(label="")
        row.delay_label.add_css_class("dim-label")
        row.delay_label.set_width_chars(6)
        row.delay_label.set_xalign(1)
        box.append(row.delay_label)

        return row

    def _on_connect_clicked(self, button):
        """Handle connect/disconnect button click."""
        button.set_sensitive(False)

        def do_action():
            if self.service.is_running():
                success, msg = self.service.stop()
            else:
                success, msg = self.service.start()
            GLib.idle_add(self._after_connect_action, button)

        import threading
        thread = threading.Thread(target=do_action)
        thread.daemon = True
        thread.start()

    def _after_connect_action(self, button):
        """Called after connect/disconnect completes."""
        button.set_sensitive(True)
        self._refresh_status()
        self._refresh_servers()

    def _on_tun_toggled(self, switch, state):
        """Handle TUN mode toggle."""
        switch.set_sensitive(False)

        def do_tun_action():
            if state:
                success, msg = self.service.enable_tun()
            else:
                success, msg = self.service.disable_tun()
            GLib.idle_add(self._after_tun_action, switch)

        import threading
        thread = threading.Thread(target=do_tun_action)
        thread.daemon = True
        thread.start()
        return True  # Prevent default handler

    def _after_tun_action(self, switch):
        """Called after TUN toggle completes."""
        switch.set_sensitive(True)
        self._refresh_status()

    def _on_server_selected(self, listbox, row):
        """Handle server selection."""
        if not row or not hasattr(row, 'server_name'):
            return

        proxy_name = row.server_name

        if self.service.is_running():
            success = self.api.select_proxy(self.proxy_group, proxy_name)
            if success:
                self.current_proxy = proxy_name
                self._refresh_servers()
                self._refresh_status()

    def _on_test_all_clicked(self, button):
        """Test delay for all servers."""
        if not self.service.is_running():
            return

        # Test each server in background
        def test_server(row):
            if hasattr(row, 'server_name'):
                delay = self.api.get_proxy_delay(row.server_name)
                if delay:
                    GLib.idle_add(lambda: row.delay_label.set_label(f"{delay}ms"))
                else:
                    GLib.idle_add(lambda: row.delay_label.set_label("--"))

        import threading
        for i in range(100):  # Max 100 servers
            row = self.server_list.get_row_at_index(i)
            if row is None:
                break
            thread = threading.Thread(target=test_server, args=(row,))
            thread.daemon = True
            thread.start()

    def _on_add_subscription(self, button):
        """Handle add subscription."""
        url = self.sub_entry.get_text().strip()
        if not url:
            return

        button.set_sensitive(False)

        def do_add():
            success, msg = self.service.add_subscription(url)
            GLib.idle_add(self._after_add_subscription, button, success)

        import threading
        thread = threading.Thread(target=do_add)
        thread.daemon = True
        thread.start()

    def _after_add_subscription(self, button, success):
        """Called after add subscription completes."""
        button.set_sensitive(True)
        if success:
            self.sub_entry.set_text("")
            self._refresh_all()

    def _on_update_subscription(self, button):
        """Handle update subscription."""
        button.set_sensitive(False)

        def do_update():
            success, msg = self.service.update_subscription()
            GLib.idle_add(self._after_update_subscription, button)

        import threading
        thread = threading.Thread(target=do_update)
        thread.daemon = True
        thread.start()

    def _after_update_subscription(self, button):
        """Called after update subscription completes."""
        button.set_sensitive(True)
        self._refresh_all()

    def _start_speed_monitor(self):
        """Start monitoring network speed."""
        if self.speed_timer_id:
            GLib.source_remove(self.speed_timer_id)
        self.speed_timer_id = GLib.timeout_add(1000, self._update_speed)

    def _stop_speed_monitor(self):
        """Stop monitoring network speed."""
        if self.speed_timer_id:
            GLib.source_remove(self.speed_timer_id)
            self.speed_timer_id = None

    def _update_speed(self):
        """Update speed display (called every second)."""
        if not self.service.is_running():
            self.download_speed_label.set_label("0 KB/s")
            self.upload_speed_label.set_label("0 KB/s")
            self.last_download = 0
            self.last_upload = 0
            return True  # Keep timer running

        try:
            conn_info = self.api.get_connections()
            current_download = conn_info.get("downloadTotal", 0)
            current_upload = conn_info.get("uploadTotal", 0)

            # Calculate speed (bytes per second)
            if self.last_download > 0:
                download_speed = current_download - self.last_download
                upload_speed = current_upload - self.last_upload

                self.download_speed_label.set_label(self._format_speed(download_speed))
                self.upload_speed_label.set_label(self._format_speed(upload_speed))

            self.last_download = current_download
            self.last_upload = current_upload

        except Exception as e:
            pass  # Silently ignore errors

        return True  # Keep timer running

    def _format_speed(self, bytes_per_sec: int) -> str:
        """Format speed in human readable format."""
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024):.2f} MB/s"

    def _is_autostart_enabled(self) -> bool:
        """Check if autostart is enabled."""
        return AUTOSTART_FILE.exists()

    def _on_autostart_toggled(self, action, value):
        """Handle autostart toggle."""
        enabled = value.get_boolean()
        if enabled:
            self._enable_autostart()
        else:
            self._disable_autostart()
        action.set_state(value)

    def _enable_autostart(self):
        """Enable autostart by creating desktop file in autostart directory."""
        try:
            AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)

            # Create autostart desktop entry
            desktop_content = """[Desktop Entry]
Name=Clash VPN Manager
Comment=Manage Clash/Mihomo VPN connections
Exec=/opt/clash-vpn-manager/clash-vpn-manager
Icon=clash-vpn-manager
Terminal=false
Type=Application
Categories=Network;System;
StartupWMClass=com.clashgui.ClashGUI
X-GNOME-Autostart-enabled=true
"""
            AUTOSTART_FILE.write_text(desktop_content)
        except Exception as e:
            print(f"Error enabling autostart: {e}")

    def _disable_autostart(self):
        """Disable autostart by removing desktop file from autostart directory."""
        try:
            if AUTOSTART_FILE.exists():
                AUTOSTART_FILE.unlink()
        except Exception as e:
            print(f"Error disabling autostart: {e}")

    def _on_about(self, action, param):
        """Show about dialog."""
        about = Adw.AboutWindow(
            transient_for=self,
            application_name="Clash VPN Manager",
            application_icon="clash-vpn-manager",
            version="1.0.0",
            developer_name="Clash Linux",
            website="https://github.com/clash-linux",
            comments="A GTK4 application to manage Clash/Mihomo VPN connections",
            license_type=Gtk.License.MIT_X11,
        )
        about.present()
