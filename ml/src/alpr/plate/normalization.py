"""Conservative canonicalization for Malaysian plate-number matching."""

from __future__ import annotations

import re
import unicodedata

_CANONICAL_PATTERN = re.compile(r"^[A-Z]{1,3}[0-9]{1,4}[A-Z]{0,3}$")


def normalize_plate_text(value: str | None) -> str:
    """Uppercase and remove separators without guessing ambiguous OCR characters."""
    if not value:
        return ""
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return "".join(character for character in ascii_value.upper() if character.isascii() and character.isalnum())


def is_plausible_malaysian_plate(value: str | None) -> bool:
    """Check a common Malaysian plate shape after normalization.

    This is intentionally a confidence aid, not a hard gate: legitimate special
    registration formats can be handled later through registered-vehicle lookup.
    """
    return bool(_CANONICAL_PATTERN.fullmatch(normalize_plate_text(value)))