"""Environment attribute resolution module."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class EnvironmentAttributes(BaseModel):
    current_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    business_hours: bool = True       # 09:00 to 18:00 Mon-Fri
    weekend: bool = False             # Sat/Sun
    public_holiday: bool = False
    country: str = "US"
    location: str = "Office HQ"
    office_network: bool = True        # Corporate Subnet
    vpn_connected: bool = True         # Corporate VPN
    device_type: str = "Desktop"       # Desktop, Mobile, Tablet
    browser: str = "Chrome"
    operating_system: str = "Windows"
    ip_address: str = "127.0.0.1"
    ip_reputation: str = "High"        # High, Medium, Low, Malicious
    device_managed: bool = True        # MDM enrolled
    session_duration: int = 300        # Seconds
    connection_security: str = "TLS1.3"
    request_frequency: int = 5         # Requests / min


def extract_environment_attributes(request: Optional[Any] = None, custom_overrides: Optional[Dict[str, Any]] = None) -> EnvironmentAttributes:
    """Extracts environmental attributes from FastAPI request, headers, or simulation payload."""
    now = datetime.now(timezone.utc)
    is_weekend = now.weekday() >= 5
    # Business hours: 09:00 to 18:00 Mon-Fri
    is_business_hours = (9 <= now.hour < 18) and not is_weekend

    ip = "127.0.0.1"
    vpn = True
    office_net = True
    device_type = "Desktop"
    browser = "Chrome"
    os_name = "Windows"

    if request:
        headers = getattr(request, "headers", {})
        ip = headers.get("x-forwarded-for") or getattr(getattr(request, "client", None), "host", "127.0.0.1")
        if "," in ip:
            ip = ip.split(",")[0].strip()

        vpn_hdr = headers.get("x-vpn-connected") or headers.get("x-corporate-vpn")
        if vpn_hdr is not None:
            vpn = str(vpn_hdr).lower() in ("true", "1", "yes")

        ua = headers.get("user-agent", "").lower()
        if "mobile" in ua or "android" in ua or "iphone" in ua:
            device_type = "Mobile"
        if "macintosh" in ua or "mac os" in ua:
            os_name = "macOS"
        elif "linux" in ua:
            os_name = "Linux"
        if "firefox" in ua:
            browser = "Firefox"
        elif "edg" in ua:
            browser = "Edge"

    merged = {
        "current_time": now.isoformat(),
        "business_hours": is_business_hours,
        "weekend": is_weekend,
        "public_holiday": False,
        "country": "US",
        "location": "HQ",
        "office_network": office_net,
        "vpn_connected": vpn,
        "device_type": device_type,
        "browser": browser,
        "operating_system": os_name,
        "ip_address": ip,
        "ip_reputation": "High",
        "device_managed": True,
        "session_duration": 300,
        "connection_security": "TLS1.3",
        "request_frequency": 5,
    }

    if custom_overrides:
        for k, v in custom_overrides.items():
            if v is not None and k in EnvironmentAttributes.model_fields:
                merged[k] = v

    return EnvironmentAttributes(**merged)
