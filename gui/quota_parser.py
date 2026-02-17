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
    # Note: [:\s：] matches both ASCII colon, Chinese colon, and whitespace
    PATTERNS = {
        # Remaining traffic patterns (Chinese provider format)
        "remaining": [
            r"剩余流量[:\s：]*([0-9.]+)\s*(GB|MB|TB|G|M|T)",
            r"剩[餘余].*?([0-9.]+)\s*(GB|MB|TB|G|M|T)",
            r"(?:remaining|left)[:\s]*([0-9.]+)\s*(GB|MB|TB)",
            r"([0-9.]+)\s*(GB|MB|TB)\s*(?:remaining|剩余|left)",
            r"([0-9.]+)\s*(GB|MB|TB)", # Broad fallback for anything with GB/MB/TB
        ],
        # Total traffic patterns
        "total": [
            r"(?:total|总计|總計|总流量|套餐)[:\s：]*([0-9.]+)\s*(GB|MB|TB|G|M|T)",
            r"([0-9.]+)\s*(GB|MB|TB)\s*(?:total|package)",
            r"套餐[:\s：]*([0-9.]+)\s*(GB|MB|TB|G|M|T)",
        ],
        # Used traffic patterns
        "used": [
            r"(?:used|已用)[:\s：]*([0-9.]+)\s*(GB|MB|TB|G|M|T)",
        ],
        # Days until reset (Chinese provider format)
        "reset_days": [
            r"(?:距离?下次重置剩?余?|重置)[:\s：]*(\d+)\s*(?:days?|天|日)",
            r"(\d+)\s*(?:days?|天|日)\s*(?:until reset|后重置|後重置)",
            r"(?:reset|重置)[:\s：]*(\d+)\s*(?:days?|天)",
        ],
        # Expiry date (Chinese provider format)
        "expires": [
            r"(?:套餐)?到期[:\s：]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
            r"(?:expires?|過期|过期)[:\s：]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
            r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s*(?:expires?|到期)",
        ],
        # Days left until expiry
        "days_left": [
            r"(?:expires? in|有效期|剩余|還有)[:\s：]*(\d+)\s*(?:days?|天|日)",
            r"(\d+)\s*(?:days?|天|日)\s*(?:left|remaining|剩余|有效)",
        ],
    }

    def _to_gb(self, value: float, unit: str) -> float:
        """Convert value to GB."""
        unit = unit.upper()
        if unit in ("TB", "T"):
            return value * 1024
        elif unit in ("MB", "M"):
            return value / 1024
        return value  # GB or G

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object."""
        # Normalize separators
        date_str = date_str.replace("/", "-").replace("年", "-").replace("月", "-").replace("日", "")

        # Try different formats
        for fmt in ("%Y-%m-%d", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
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
        
        # Default total to 300 GB as requested by user
        quota.total_gb = 300.0

        # Combine all proxy names into one string for parsing
        # Support both list of dicts (proxies) and list of strings (proxy names)
        if proxies and isinstance(proxies[0], str):
            all_names = "\n".join(proxies)
        else:
            all_names = "\n".join(p.get("name", "") for p in proxies)

        # Parse remaining traffic
        result = self._extract_value(all_names, self.PATTERNS["remaining"])
        if result and len(result) >= 2:
            try:
                quota.remaining_gb = self._to_gb(float(result[0]), result[1])
            except (ValueError, TypeError):
                pass

        # Parse total traffic
        result = self._extract_value(all_names, self.PATTERNS["total"])
        if result and len(result) >= 2:
            try:
                quota.total_gb = self._to_gb(float(result[0]), result[1])
            except (ValueError, TypeError):
                pass
        
        # Calculate used_gb if total and remaining are available
        if quota.total_gb and quota.remaining_gb is not None:
            quota.used_gb = quota.total_gb - quota.remaining_gb

        # Parse reset days
        result = self._extract_value(all_names, self.PATTERNS["reset_days"])
        if result:
            try:
                quota.reset_days = int(result[0])
            except (ValueError, TypeError):
                pass

        # Parse expiry date
        result = self._extract_value(all_names, self.PATTERNS["expires"])
        if result:
            quota.expires_date = self._parse_date(result[0])

        # Parse days left
        result = self._extract_value(all_names, self.PATTERNS["days_left"])
        if result:
            try:
                quota.days_left = int(result[0])
            except (ValueError, TypeError):
                pass

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
