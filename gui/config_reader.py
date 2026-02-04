"""Read clash-linux configuration files."""
import os
import re
from pathlib import Path
from typing import Optional
import yaml


class ConfigReader:
    """Reads and parses clash-linux configuration files."""

    def __init__(self, base_dir: Optional[str] = None):
        """Initialize with base directory.

        Args:
            base_dir: Override CLASH_BASE_DIR. If None, reads from .env
        """
        self.base_dir = base_dir or self._find_base_dir()
        self.resources_dir = os.path.join(self.base_dir, "resources")

    def _find_base_dir(self) -> str:
        """Find CLASH_BASE_DIR from .env file."""
        # Try common locations
        search_paths = [
            os.path.expanduser("~/clashctl/.env"),
            os.path.expanduser("~/clash-linux/.env"),
            "/home/ivo/clashctl/.env",
        ]

        for env_path in search_paths:
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith("CLASH_BASE_DIR="):
                            return line.split("=", 1)[1].strip()

        # Default fallback
        return os.path.expanduser("~/clashctl")

    def get_mixin_config(self) -> dict:
        """Read mixin.yaml for API settings."""
        mixin_path = os.path.join(self.resources_dir, "mixin.yaml")
        if os.path.exists(mixin_path):
            with open(mixin_path, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}

    def get_runtime_config(self) -> dict:
        """Read runtime.yaml for current proxy config."""
        runtime_path = os.path.join(self.resources_dir, "runtime.yaml")
        if os.path.exists(runtime_path):
            with open(runtime_path, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}

    def get_profiles(self) -> dict:
        """Read profiles.yaml for subscription list."""
        profiles_path = os.path.join(self.resources_dir, "profiles.yaml")
        if os.path.exists(profiles_path):
            with open(profiles_path, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}

    def get_api_settings(self) -> tuple[str, int, str]:
        """Get API host, port, and secret from mixin config.

        Returns:
            Tuple of (host, port, secret)
        """
        mixin = self.get_mixin_config()
        ext_controller = mixin.get("external-controller", "127.0.0.1:9090")
        secret = mixin.get("secret", "")

        # Parse host:port
        if ":" in ext_controller:
            host, port_str = ext_controller.rsplit(":", 1)
            port = int(port_str)
        else:
            host = ext_controller
            port = 9090

        # Convert 0.0.0.0 to localhost
        if host == "0.0.0.0":
            host = "127.0.0.1"

        return host, port, secret

    def get_kernel_path(self) -> str:
        """Get path to mihomo binary."""
        return os.path.join(self.base_dir, "bin", "mihomo")

    def get_proxies(self) -> list[dict]:
        """Get list of proxies from runtime config."""
        config = self.get_runtime_config()
        return config.get("proxies", [])

    def get_proxy_groups(self) -> list[dict]:
        """Get list of proxy groups from runtime config."""
        config = self.get_runtime_config()
        return config.get("proxy-groups", [])
