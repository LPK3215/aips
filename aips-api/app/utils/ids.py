from __future__ import annotations

import re


_HEX32_RE = re.compile(r"^[0-9a-fA-F]{32}$")


def normalize_hex32(value: str) -> str:
    """Return a normalized (lowercase) 32-char hex id.

    This protects file paths and glob patterns from path traversal / wildcard injection.
    """

    candidate = (value or "").strip()
    if not _HEX32_RE.fullmatch(candidate):
        raise ValueError("非法编号。")
    return candidate.lower()

