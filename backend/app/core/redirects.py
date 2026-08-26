from __future__ import annotations

import re
from urllib.parse import urlsplit

from app.core.config import settings


OPPORTUNITY_RADAR_PATH = "/OpportunityRadar"
_DANGEROUS_ENCODING = re.compile(r"%(?:00|0a|0d|2f|5c)", re.IGNORECASE)


def normalize_return_to(value: str | None, *, site_origin: str | None = None) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    if not candidate or len(candidate) > 2048:
        return None
    if any(ord(character) < 32 for character in candidate):
        return None
    if "\\" in candidate or _DANGEROUS_ENCODING.search(candidate):
        return None

    origin = urlsplit(site_origin or settings.frontend_origin)
    parsed = urlsplit(candidate)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
            return None
        if (parsed.scheme.casefold(), parsed.netloc.casefold()) != (origin.scheme.casefold(), origin.netloc.casefold()):
            return None
    elif not candidate.startswith("/") or candidate.startswith("//"):
        return None

    if parsed.path != OPPORTUNITY_RADAR_PATH and not parsed.path.startswith(f"{OPPORTUNITY_RADAR_PATH}/"):
        return None
    normalized = parsed.path
    if parsed.query:
        normalized += f"?{parsed.query}"
    return normalized
