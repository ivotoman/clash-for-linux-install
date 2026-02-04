"""Parse quota information from proxy names."""
import re
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional


@dataclass
class QuotaInfo:
    """Subscription quota information."""
    remaining_gb: Optional[float] = None
    total_gb: Optional[float] = None
    used_gb: Optional[float] = None
    days_left: Optional[int] = None
    expires_date: Optional[date] = None
    reset_days: Optional[int] = None

    @property
    def usage_percent(self) -> Optional[float]:
        """Calculate usage percentage."""
        if self.total_gb and self.remaining_gb is not None:
            used = self.total_gb - self.remaining_gb
            return (used / self.total_gb) * 100
        if self.total_gb and self.used_gb is not None:
            return (self.used_gb / self.total_gb) * 100
        return None


class QuotaParser:
    """Parse quota info from proxy names in subscription config."""

    # Patterns for matching quota info in proxy names
    PATTERNS = {
        # Remaining traffic patterns
        "remaining": [
            r"(?:remaining|剩余|剩餘)\s*(?:traffic|流量)?[:\s]*([0-9.]+)\s*(GB|MB|TB)",
            r"([0-9.]+)\s*(GB|MB|TB)\s*(?:remaining|剩余|left)",
        ],
        # Total traffic patterns
        "total": [
            r"(?:total|总计|總計|套餐)[:\s]*([0-9.]+)\s*(GB|MB|TB)",
            r"([0-9.]+)\s*(GB|MB|TB)\s*(?:total|package)",
        ],
        # Used traffic patterns
        "used": [
            r"(?:used|已用)[:\s]*([0-9.]+)\s*(GB|MB|TB)",
        ],
        # Days until reset
        "reset_days": [
            r"(?:reset|重置|距离重置)[:\s]*(\d+)\s*(?:days?|天)",
            r"(\d+)\s*(?:days?|天)\s*(?:until reset|后重置)",
        ],
        # Expiry date
        "expires": [
            r"(?:expires?|到期|過期)[:\s]*(\d{4}[-/]\d{2}[-/]\d{2})",
            r"(\d{4}[-/]\d{2}[-/]\d{2})\s*(?:expires?|到期)",
        ],
        # Days left
        "days_left": [
            r"(?:expires? in|剩余|還有)[:\s]*(\d+)\s*(?:days?|天)",
            r"(\d+)\s*(?:days?|天)\s*(?:left|remaining|剩余)",
        ],
    }

    def _to_gb(self, value: float, unit: str) -> float:
        """Convert value to GB."""
        unit = unit.upper()
        if unit == "TB":
            return value * 1024
        elif unit == "MB":
            return value / 1024
        return value

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object."""
        date_str = date_str.replace("/", "-")
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None

    def _extract_value(self, text: str, patterns: list[str]) -> Optional[tuple]:
        """Extract value using patterns."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.groups()
        return None

    def parse_proxy_names(self, proxies: list[dict]) -> QuotaInfo:
        """Parse quota info from proxy names.

        Args:
            proxies: List of proxy dicts with 'name' field

        Returns:
            QuotaInfo with parsed values
        """
        quota = QuotaInfo()

        # Combine all proxy names into one string for parsing
        all_names = "\n".join(p.get("name", "") for p in proxies)

        # Parse remaining traffic
        result = self._extract_value(all_names, self.PATTERNS["remaining"])
        if result:
            quota.remaining_gb = self._to_gb(float(result[0]), result[1])

        # Parse total traffic
        result = self._extract_value(all_names, self.PATTERNS["total"])
        if result:
            quota.total_gb = self._to_gb(float(result[0]), result[1])

        # Parse used traffic
        result = self._extract_value(all_names, self.PATTERNS["used"])
        if result:
            quota.used_gb = self._to_gb(float(result[0]), result[1])

        # Calculate remaining from total - used if not directly available
        if quota.remaining_gb is None and quota.total_gb and quota.used_gb:
            quota.remaining_gb = quota.total_gb - quota.used_gb

        # Parse reset days
        result = self._extract_value(all_names, self.PATTERNS["reset_days"])
        if result:
            quota.reset_days = int(result[0])

        # Parse expiry date
        result = self._extract_value(all_names, self.PATTERNS["expires"])
        if result:
            quota.expires_date = self._parse_date(result[0])

        # Parse days left
        result = self._extract_value(all_names, self.PATTERNS["days_left"])
        if result:
            quota.days_left = int(result[0])

        # Calculate days left from expiry date if not directly available
        if quota.days_left is None and quota.expires_date:
            delta = quota.expires_date - date.today()
            quota.days_left = max(0, delta.days)

        return quota


def format_bytes(gb: float) -> str:
    """Format GB value for display."""
    if gb >= 1024:
        return f"{gb / 1024:.2f} TB"
    elif gb >= 1:
        return f"{gb:.2f} GB"
    else:
        return f"{gb * 1024:.2f} MB"
