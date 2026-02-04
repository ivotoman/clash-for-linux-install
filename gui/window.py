"""Main application window."""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio

from config_reader import ConfigReader
from clash_api import ClashAPI
from service_manager import ServiceManager
from quota_parser import QuotaParser, format_bytes


class MainWindow(Adw.ApplicationWindow):
    """Main application window."""

    def __init__(self, app):
        super().__init__(application=app, title="Clash VPN Manager")
        self.set_default_size(450, 650)

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

        # Build UI
        self._build_ui()

        # Initial refresh
        GLib.timeout_add(500, self._initial_refresh)

    def _build_ui(self):
        """Build the user interface."""
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(main_box)

        # Header bar
        header = Adw.HeaderBar()
        main_box.append(header)

        # Refresh button in header
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.connect("clicked", lambda b: self._refresh_all())
        header.pack_end(refresh_btn)

        # Scrollable content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        main_box.append(scrolled)

        # Content box with margins
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

        # Servers card
        self._build_servers_card(content)

        # Subscription card
        self._build_subscription_card(content)

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

        # Connect/Disconnect button
        self.connect_btn = Gtk.Button(label="Connect")
        self.connect_btn.add_css_class("suggested-action")
        self.connect_btn.set_halign(Gtk.Align.CENTER)
        self.connect_btn.set_margin_top(8)
        self.connect_btn.connect("clicked", self._on_connect_clicked)
        box.append(self.connect_btn)

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

    def _build_servers_card(self, parent):
        """Build server selection card."""
        frame = Gtk.Frame()
        frame.add_css_class("card")
        frame.set_vexpand(True)
        parent.append(frame)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        frame.set_child(box)

        # Title row
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.append(title_row)

        title = Gtk.Label(label="SERVERS")
        title.add_css_class("heading")
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        title_row.append(title)

        # Test all button
        test_btn = Gtk.Button(label="Test")
        test_btn.connect("clicked", self._on_test_all_clicked)
        title_row.append(test_btn)

        # Server list in scrolled window
        list_scroll = Gtk.ScrolledWindow()
        list_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        list_scroll.set_min_content_height(200)
        list_scroll.set_vexpand(True)
        box.append(list_scroll)

        self.server_list = Gtk.ListBox()
        self.server_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.server_list.add_css_class("boxed-list")
        self.server_list.connect("row-activated", self._on_server_selected)
        list_scroll.set_child(self.server_list)

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

        add_btn = Gtk.Button(label="Add")
        add_btn.connect("clicked", self._on_add_subscription)
        btn_row.append(add_btn)

        update_btn = Gtk.Button(label="Update")
        update_btn.connect("clicked", self._on_update_subscription)
        btn_row.append(update_btn)

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

        if is_running:
            self.status_indicator.set_label("●")
            self.status_indicator.remove_css_class("status-disconnected")
            self.status_indicator.add_css_class("status-connected")
            self.status_label.set_label("Connected")
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

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(12)
        box.set_margin_end(12)
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
        box.append(label)

        # Delay label (placeholder)
        row.delay_label = Gtk.Label(label="")
        row.delay_label.add_css_class("dim-label")
        box.append(row.delay_label)

        return row

    def _on_connect_clicked(self, button):
        """Handle connect/disconnect button click."""
        if self.service.is_running():
            success, msg = self.service.stop()
        else:
            success, msg = self.service.start()

        # Refresh after short delay
        GLib.timeout_add(500, self._refresh_status)

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
                    GLib.idle_add(lambda: row.delay_label.set_label("timeout"))

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

        # Call clashsub add via subprocess
        import subprocess
        try:
            result = subprocess.run(
                ["bash", "-c", f"source ~/.bashrc && clashsub add '{url}'"],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                self.sub_entry.set_text("")
                self._refresh_all()
        except Exception as e:
            print(f"Error adding subscription: {e}")

    def _on_update_subscription(self, button):
        """Handle update subscription."""
        import subprocess
        try:
            subprocess.run(
                ["bash", "-c", "source ~/.bashrc && clashsub update"],
                capture_output=True,
                text=True,
                timeout=120
            )
            self._refresh_all()
        except Exception as e:
            print(f"Error updating subscription: {e}")
