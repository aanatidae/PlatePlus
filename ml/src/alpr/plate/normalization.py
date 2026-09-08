"""Conservative canonicalization for Malaysian plate-number matching."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable

_CANONICAL_PATTERN = re.compile(r"^[A-Z]{1,3}[0-9]{1,4}[A-Z]{0,3}$")
_LETTER_CORRECTIONS = {"0": "O", "1": "I", "2": "Z", "5": "S", "8": "B"}
_DIGIT_CORRECTIONS = {"O": "0", "I": "1", "L": "1", "Z": "2", "S": "5", "B": "8"}


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


def correct_common_ocr_confusions(value: str | None) -> str:
    """Return one auditable, format-constrained OCR correction when unambiguous.

    Corrections are applied only to a string that is not already plausible and
    only when exactly one common Malaysian plate layout can be recovered. This
    avoids broad substitutions that could turn one synthetic vehicle into another.
    """
    normalized = normalize_plate_text(value)
    if not normalized or is_plausible_malaysian_plate(normalized):
        return normalized

    candidates: set[str] = set()
    for prefix_length in range(1, 4):
        for digit_length in range(1, 5):
            suffix_length = len(normalized) - prefix_length - digit_length
            if not 0 <= suffix_length <= 3:
                continue
            prefix = _correct_segment(normalized[:prefix_length], _LETTER_CORRECTIONS, str.isalpha)
            digits = _correct_segment(
                normalized[prefix_length : prefix_length + digit_length], _DIGIT_CORRECTIONS, str.isdigit
            )
            suffix = _correct_segment(normalized[prefix_length + digit_length :], _LETTER_CORRECTIONS, str.isalpha)
            if prefix is not None and digits is not None and suffix is not None:
                candidates.add(prefix + digits + suffix)
    return candidates.pop() if len(candidates) == 1 else normalized


def _correct_segment(
    value: str, corrections: dict[str, str], valid: Callable[[str], bool]
) -> str | None:
    corrected = "".join(character if valid(character) else corrections.get(character, "") for character in value)
    return corrected if len(corrected) == len(value) else None
