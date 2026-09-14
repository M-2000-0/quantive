"""Trusted-proxy-aware client IP resolution.

X-Forwarded-For is ONLY honored when the direct TCP peer is a configured
trusted proxy. Otherwise the header is ignored entirely — otherwise any
client can rotate the header and bypass per-IP rate limits / IP blocking.
"""

import ipaddress

from fastapi import Request

from app.config import get_settings


def _trusted_entries() -> list[str]:
    raw = get_settings().TRUSTED_PROXIES or ""
    return [e.strip() for e in raw.split(",") if e.strip()]


def _is_trusted(address: str) -> bool:
    try:
        peer = ipaddress.ip_address(address)
    except ValueError:
        return False
    for entry in _trusted_entries():
        try:
            network = ipaddress.ip_network(entry, strict=False)
        except ValueError:
            continue
        if peer in network:
            return True
    return False


def get_client_ip(request: Request) -> str:
    """Resolve the true client IP.

    Honors ``X-Forwarded-For`` only when the direct peer is a trusted proxy.
    The first untrusted hop is located by scanning right-to-left (the inverse
    of the standard X-Forwarded-For ordering), so a client cannot forge the
    header to pretend to be another IP.
    """
    peer = request.client.host if request.client else "unknown"

    if not _trusted_entries() or not _is_trusted(peer):
        return peer

    forwarded = request.headers.get("X-Forwarded-For", "")
    hops = [h.strip() for h in forwarded.split(",") if h.strip()]
    for hop in reversed(hops):
        if not _is_trusted(hop):
            return hop
    return peer