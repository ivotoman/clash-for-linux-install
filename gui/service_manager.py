"""Manage mihomo service via clashctl commands."""
import os
import subprocess


class ServiceManager:
    """Control mihomo VPN service using clashctl bash functions."""

    def __init__(self, kernel_path: str, resources_dir: str):
        """Initialize service manager.

        Args:
            kernel_path: Path to mihomo binary
            resources_dir: Path to resources directory
        """
        self.kernel_path = kernel_path
        self.resources_dir = resources_dir
        # Find clashctl.sh location
        base_dir = os.path.dirname(resources_dir)
        self.clashctl_path = os.path.join(base_dir, "scripts", "cmd", "clashctl.sh")

    def _run_clash_cmd(self, cmd: str, timeout: int = 30) -> tuple[bool, str]:
        """Run a clash command by sourcing clashctl.sh.

        Args:
            cmd: Command to run (e.g., 'clashon', 'clashoff', 'clashtun on')
            timeout: Command timeout in seconds

        Returns:
            Tuple of (success, output)
        """
        # Source clashctl.sh and run the command
        bash_cmd = f'source "{self.clashctl_path}" && {cmd}'
        try:
            result = subprocess.run(
                ["bash", "-c", bash_cmd],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "TERM": "dumb"}  # Avoid terminal escape codes
            )
            output = result.stdout.strip() or result.stderr.strip()
            return result.returncode == 0, output
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def has_systemd(self) -> bool:
        """Check if systemd service file exists."""
        return os.path.exists("/etc/systemd/system/mihomo.service")

    def is_running(self) -> bool:
        """Check if mihomo is currently running."""
        try:
            result = subprocess.run(
                ["pgrep", "-f", self.kernel_path],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def is_tun_enabled(self) -> bool:
        """Check if TUN mode is enabled in config."""
        try:
            import yaml
            runtime_config = os.path.join(self.resources_dir, "runtime.yaml")
            if os.path.exists(runtime_config):
                with open(runtime_config, 'r') as f:
                    config = yaml.safe_load(f) or {}
                    return config.get("tun", {}).get("enable", False)
        except Exception:
            pass
        return False

    def start(self) -> tuple[bool, str]:
        """Start VPN using clashon (handles proxy env, config merge, etc.).

        Returns:
            Tuple of (success, message)
        """
        if self.is_running():
            # Still set proxy env
            self._run_clash_cmd("_set_system_proxy")
            return True, "Already running"

        return self._run_clash_cmd("clashon", timeout=15)

    def stop(self) -> tuple[bool, str]:
        """Stop VPN using clashoff (clears proxy env, stops service).

        Returns:
            Tuple of (success, message)
        """
        if not self.is_running():
            return True, "Not running"

        return self._run_clash_cmd("clashoff", timeout=15)

    def restart(self) -> tuple[bool, str]:
        """Restart the service."""
        return self._run_clash_cmd("clashrestart", timeout=20)

    def enable_tun(self) -> tuple[bool, str]:
        """Enable TUN mode using clashtun on.

        Returns:
            Tuple of (success, message)
        """
        return self._run_clash_cmd("clashtun on", timeout=30)

    def disable_tun(self) -> tuple[bool, str]:
        """Disable TUN mode using clashtun off.

        Returns:
            Tuple of (success, message)
        """
        return self._run_clash_cmd("clashtun off", timeout=15)

    def get_status(self) -> str:
        """Get service status string."""
        if self.is_running():
            tun_status = " + TUN" if self.is_tun_enabled() else ""
            if self.has_systemd():
                try:
                    result = subprocess.run(
                        ["systemctl", "is-active", "mihomo"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.stdout.strip() == "active":
                        return f"Running (systemd){tun_status}"
                except Exception:
                    pass
            return f"Running{tun_status}"
        return "Stopped"

    def update_subscription(self) -> tuple[bool, str]:
        """Update current subscription."""
        return self._run_clash_cmd("clashsub update", timeout=120)

    def add_subscription(self, url: str) -> tuple[bool, str]:
        """Add a new subscription."""
        # Escape single quotes in URL
        safe_url = url.replace("'", "'\"'\"'")
        return self._run_clash_cmd(f"clashsub add '{safe_url}'", timeout=60)
