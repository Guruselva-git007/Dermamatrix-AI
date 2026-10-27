"""Bounded same-origin browser checks for the current single-origin prototype.

These checks are not authentication, a CSRF token protocol or protection from
non-browser clients, which can forge or omit headers. The local host boundary
also rejects DNS-rebinding hostnames rather than trusting an arbitrary Host.
Proxy headers are deliberately not read or reinterpreted by this module.
"""

from __future__ import annotations

from collections.abc import Mapping
import ipaddress
import re
from urllib.parse import urlsplit


UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
_DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
_REPORT_DOWNLOAD = re.compile(r"/api/reports/[^/]+/download\Z")


def canonical_origin(value: str) -> tuple[str, str, int]:
    """Parse one strict HTTP(S) origin; normalize host case and default ports."""
    if not isinstance(value, str) or not value or any(ord(character) <= 32 or ord(character) >= 127 for character in value):
        raise ValueError("Expected a single ASCII HTTP(S) origin.")
    if any(character in value for character in (",", "\\", "%")):
        raise ValueError("Expected a single HTTP(S) origin.")
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Expected an HTTP(S) origin.")
        if parsed.path or parsed.query or parsed.fragment or "?" in value or "#" in value:
            raise ValueError("An origin cannot contain a path, query or fragment.")
        if parsed.username is not None or parsed.password is not None or "@" in parsed.netloc or parsed.netloc.endswith(":"):
            raise ValueError("An origin cannot contain credentials or an empty port.")
        host = parsed.hostname
        port = parsed.port
        if not host:
            raise ValueError("An origin requires a host.")
        if ":" in host:
            if not re.fullmatch(r"\[[^\]]+\](?::[0-9]+)?", parsed.netloc):
                raise ValueError("Invalid IPv6 origin authority.")
            host = str(ipaddress.IPv6Address(host))
        else:
            if not re.fullmatch(r"[^:\[\]]+(?::[0-9]+)?", parsed.netloc):
                raise ValueError("Invalid origin authority.")
            host = host.lower()
            if len(host) > 253 or not all(_DNS_LABEL.fullmatch(label) for label in host.split(".")):
                raise ValueError("Invalid origin hostname.")
        port = port if port is not None else 443 if parsed.scheme.lower() == "https" else 80
        if not 1 <= port <= 65535:
            raise ValueError("Invalid origin port.")
        return parsed.scheme.lower(), host, port
    except (ValueError, TypeError) as error:
        raise ValueError("Expected a single valid HTTP(S) origin.") from error


def request_security_configuration(environment: Mapping[str, str]) -> dict:
    """Require operator-configured exact origins before explicit production use."""
    production = environment.get("DERMAMATRIX_ENV", "local").lower() == "production"
    raw = environment.get("DERMAMATRIX_TRUSTED_ORIGINS", "")
    trusted = []
    if raw:
        for value in raw.split(","):
            try:
                trusted.append(canonical_origin(value.strip()))
            except ValueError as error:
                raise ValueError("DERMAMATRIX_TRUSTED_ORIGINS must contain comma-separated HTTP(S) origins without paths, credentials or empty entries.") from error
    if production and not trusted:
        raise ValueError("Production mode requires explicit DERMAMATRIX_TRUSTED_ORIGINS for the verified application origin(s).")
    return {"REQUEST_SECURITY_PRODUCTION": production, "REQUEST_TRUSTED_ORIGINS": tuple(trusted)}


def _referer_origin(value: str) -> tuple[str, str, int]:
    """Extract an older browser's origin from its full HTTP(S) Referer URL."""
    if not value or any(ord(character) <= 32 or ord(character) >= 127 for character in value) or "\\" in value:
        raise ValueError("Invalid Referer URL.")
    try:
        parsed = urlsplit(value)
        return canonical_origin(f"{parsed.scheme}://{parsed.netloc}")
    except (ValueError, TypeError) as error:
        raise ValueError("Invalid Referer URL.") from error


def request_security_error(request, configuration: Mapping) -> str | None:
    """Return a safe error code before any route reads body data or opens MySQL."""
    try:
        target = canonical_origin(f"{request.scheme}://{request.host}")
    except ValueError:
        return "UNTRUSTED_REQUEST_HOST"
    if configuration.get("REQUEST_SECURITY_PRODUCTION", False):
        if target not in configuration.get("REQUEST_TRUSTED_ORIGINS", ()):
            return "UNTRUSTED_REQUEST_HOST"
    elif target[1] not in LOCAL_HOSTS:
        return "UNTRUSTED_REQUEST_HOST"

    # The existing GET and Flask's automatic HEAD both invoke the view that
    # regenerates report-ledger metadata. Guard both without changing that view.
    report_download = request.method in {"GET", "HEAD"} and bool(_REPORT_DOWNLOAD.fullmatch(request.path))
    if not report_download and (request.method not in UNSAFE_METHODS or not request.path.startswith("/api/")):
        return None
    origin = request.headers.get("Origin")
    if origin is not None:
        try:
            if canonical_origin(origin) != target:
                return "REQUEST_ORIGIN_REJECTED"
        except ValueError:
            return "REQUEST_ORIGIN_REJECTED"
    elif request.headers.get("Referer") is not None:
        try:
            if _referer_origin(request.headers["Referer"]) != target:
                return "REQUEST_ORIGIN_REJECTED"
        except ValueError:
            return "REQUEST_ORIGIN_REJECTED"
    fetch_site = request.headers.get("Sec-Fetch-Site")
    allowed_fetch_sites = {"same-origin", "none"} if report_download else {"same-origin"}
    if fetch_site is not None and fetch_site not in allowed_fetch_sites:
        return "REQUEST_ORIGIN_REJECTED"
    # Same-origin browser requests and existing non-browser/legacy clients
    # without either header remain compatible. This is an explicit boundary,
    # not proof that an arbitrary client without headers is trustworthy.
    return None
