"""Mihomo REST API client using urllib (no external dependencies)."""
import json
import urllib.parse
import urllib.request
import urllib.error
from typing import Optional


class ClashAPI:
    """Synchronous client for Mihomo/Clash REST API."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9090, secret: str = ""):
        """Initialize API client.

        Args:
            host: API host address
            port: API port
            secret: API authentication secret
        """
        self.base_url = f"http://{host}:{port}"
        self.headers = {"Content-Type": "application/json"}
        if secret:
            self.headers["Authorization"] = f"Bearer {secret}"

    def _request(self, method: str, path: str, data: Optional[dict] = None,
                 params: Optional[dict] = None, timeout: float = 5.0) -> Optional[dict]:
        """Make an API request.

        Args:
            method: HTTP method (GET, PUT, POST, etc.)
            path: API path
            data: JSON data to send
            params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            JSON response or None if no content/error
        """
        url = f"{self.base_url}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        body = None
        if data:
            body = json.dumps(data).encode('utf-8')

        request = urllib.request.Request(url, data=body, headers=self.headers, method=method)

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.status == 204:
                    return None
                content = response.read().decode('utf-8')
                if content:
                    return json.loads(content)
                return None
        except urllib.error.HTTPError as e:
            if e.code == 204:
                return None
            return None
        except Exception:
            return None

    def is_running(self) -> bool:
        """Check if Clash API is reachable."""
        try:
            request = urllib.request.Request(self.base_url, headers=self.headers)
            with urllib.request.urlopen(request, timeout=2) as response:
                return response.status == 200
        except Exception:
            return False

    def get_proxies(self) -> dict:
        """Get all proxies and proxy groups.

        Returns:
            Dict with 'proxies' key containing all proxy info
        """
        result = self._request("GET", "/proxies")
        return result or {"proxies": {}}

    def get_proxy_group(self, group_name: str) -> Optional[dict]:
        """Get info for a specific proxy group.

        Args:
            group_name: Name of the proxy group

        Returns:
            Group info dict or None
        """
        encoded = urllib.parse.quote(group_name, safe="")
        return self._request("GET", f"/proxies/{encoded}")

    def select_proxy(self, group_name: str, proxy_name: str) -> bool:
        """Select a proxy for a group.

        Args:
            group_name: Name of the proxy group
            proxy_name: Name of the proxy to select

        Returns:
            True if successful
        """
        encoded = urllib.parse.quote(group_name, safe="")
        url = f"{self.base_url}/proxies/{encoded}"
        body = json.dumps({"name": proxy_name}).encode('utf-8')
        request = urllib.request.Request(url, data=body, headers=self.headers, method="PUT")

        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status == 204
        except urllib.error.HTTPError as e:
            return e.code == 204
        except Exception:
            return False

    def get_proxy_delay(self, proxy_name: str, url: str = "http://www.gstatic.com/generate_204",
                        timeout: int = 5000) -> Optional[int]:
        """Test proxy delay.

        Args:
            proxy_name: Name of the proxy to test
            url: Test URL
            timeout: Timeout in milliseconds

        Returns:
            Delay in ms or None if failed
        """
        encoded = urllib.parse.quote(proxy_name, safe="")
        params = {"url": url, "timeout": timeout}
        result = self._request("GET", f"/proxies/{encoded}/delay", params=params, timeout=10)
        if result and "delay" in result:
            return result["delay"]
        return None

    def get_connections(self) -> dict:
        """Get active connections and traffic stats.

        Returns:
            Dict with 'connections', 'downloadTotal', 'uploadTotal'
        """
        result = self._request("GET", "/connections")
        return result or {"connections": [], "downloadTotal": 0, "uploadTotal": 0}

    def get_config(self) -> dict:
        """Get current configuration."""
        result = self._request("GET", "/configs")
        return result or {}
