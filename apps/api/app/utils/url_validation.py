"""SSRF protection: validate URLs before server-side fetching.

Prevents Server-Side Request Forgery by blocking:
  - Private/internal IP ranges (10.x, 172.16-31.x, 192.168.x, 127.x, ::1)
  - Cloud metadata endpoints (169.254.169.254, metadata.google.internal)
  - Known dangerous hostnames (.local, .internal, .localhost)
"""

import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger("app.utils.url_validation")

_BLOCKED_HOSTS = frozenset({
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "[::1]",
    "metadata.google.internal",
    "169.254.169.254",
})

_BLOCKED_SUFFIXES = (".local", ".internal", ".localhost", ".test")

_ALLOWED_SCHEMES = ("http", "https")


def validate_url_for_fetch(url: str) -> str:
    """Validate a URL is safe for server-side fetching.

    Returns the normalized URL if safe.
    Raises ValueError if the URL is blocked.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL is required")

    parsed = urlparse(url.strip())

    # Scheme check
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"URL scheme '{parsed.scheme}' is not allowed. Use http or https.")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("URL has no hostname")

    # Blocked hostnames
    if hostname in _BLOCKED_HOSTS:
        raise ValueError(f"URL hostname '{hostname}' is blocked (internal/private)")

    # Blocked suffixes
    for suffix in _BLOCKED_SUFFIXES:
        if hostname.endswith(suffix):
            raise ValueError(f"URL hostname '{hostname}' uses a blocked suffix")

    # IP address checks
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError(f"URL resolves to private/internal IP: {ip}")
    except ValueError:
        # Not an IP literal — resolve hostname
        try:
            resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for family, _, _, _, sockaddr in resolved:
                ip_str = sockaddr[0]
                ip = ipaddress.ip_address(ip_str)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    raise ValueError(f"URL hostname '{hostname}' resolves to private IP: {ip}")
        except socket.gaierror:
            # DNS resolution failed — allow the request to fail naturally downstream
            logger.debug("DNS resolution failed for %s — allowing", hostname)

    return url.strip()
