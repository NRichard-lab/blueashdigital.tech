from __future__ import annotations

import re
from urllib.parse import urlsplit

from app.core.config import settings


_DANGEROUS_ENCODING = re.compile(r"%(?:0[0-9a-f]|1[0-9a-f]|7f|25|2e|2f|5c)", re.IGNORECASE)


def normalize_radar_return_path(value: str | None) -> str | None:
    candidate = (value or "/").strip()
    if not candidate or len(candidate) > 2048:
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in candidate):
        return None
    if "\\" in candidate or _DANGEROUS_ENCODING.search(candidate):
        return None
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return None
    if parsed.scheme or parsed.netloc or parsed.fragment:
        return None
    if not candidate.startswith("/") or candidate.startswith("//"):
        return None
    if any(segment in {".", ".."} for segment in parsed.path.split("/")):
        return None
    if parsed.path == "/api" or parsed.path.startswith("/api/"):
        return None
    normalized = parsed.path or "/"
    if parsed.query:
        normalized += f"?{parsed.query}"
    return normalized


def radar_return_url(return_path: str) -> str:
    return f"{settings.opportunity_radar_public_origin.rstrip('/')}{return_path}"


def normalize_return_to(value: str | None, *, radar_origin: str | None = None) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    if not candidate or len(candidate) > 2048:
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in candidate):
        return None
    if "\\" in candidate or _DANGEROUS_ENCODING.search(candidate):
        return None

    try:
        origin = urlsplit((radar_origin or settings.opportunity_radar_public_origin).rstrip("/"))
        parsed = urlsplit(candidate)
    except ValueError:
        return None
    if parsed.scheme or parsed.netloc:
        if parsed.username or parsed.password or parsed.fragment:
            return None
        if (parsed.scheme.casefold(), parsed.netloc.casefold()) != (origin.scheme.casefold(), origin.netloc.casefold()):
            return None
        return_path = normalize_radar_return_path(f"{parsed.path or '/'}{f'?{parsed.query}' if parsed.query else ''}")
    else:
        return_path = normalize_radar_return_path(candidate)
    if return_path is None:
        return None
    return f"{origin.scheme}://{origin.netloc}{return_path}"
