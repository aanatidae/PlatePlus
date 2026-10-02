"""Conservative plate-pattern origin hints for the simulated ALPR workflow.

These rules recognize a deliberately limited set of common layouts. A pattern
match is not proof of registration country, ownership, or legal status.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from alpr.plate.normalization import normalize_plate_text

PlateOrigin = Literal["malaysian", "singaporean", "unknown"]

# Common Malaysian state/territory and special-series initials used by this
# prototype. The broad historic plausibility helper is intentionally separate.
# JPJ publishes series and plate specifications at https://www.jpj.gov.my/.
_MALAYSIAN_PATTERN = re.compile(r"^[A-FH-NP-TVWZ][A-Z]{0,2}[0-9]{1,4}[A-Z]{0,3}$")

# LTA gives SLPxxxxA as a car example and GBC1234R, YN1234R, XD1234E
# as goods-vehicle examples. This subset is not a full Singapore registry.
# https://onemotoring.lta.gov.sg/content/onemotoring/home/buying/upfront-vehicle-costs/vehicle-registration-number--vrn-.html
_SINGAPOREAN_PATTERN = re.compile(r"^[SFGXY][A-Z]{0,2}[0-9]{1,4}[A-Z]$")


@dataclass(frozen=True)
class OriginDecision:
    origin: PlateOrigin
    reason: str


def matches_malaysian_pattern(value: str | None) -> bool:
    """Whether a value fits this prototype's supported Malaysian layout."""
    return bool(_MALAYSIAN_PATTERN.fullmatch(normalize_plate_text(value)))


def matches_singaporean_pattern(value: str | None) -> bool:
    """Whether a value fits this prototype's supported Singaporean layout."""
    return bool(_SINGAPOREAN_PATTERN.fullmatch(normalize_plate_text(value)))


def classify_plate_origin(value: str | None) -> OriginDecision:
    """Return unknown when neither or both supported layouts match."""
    normalized = normalize_plate_text(value)
    malaysian = matches_malaysian_pattern(normalized)
    singaporean = matches_singaporean_pattern(normalized)
    if malaysian and singaporean:
        return OriginDecision("unknown", "ambiguous_supported_patterns")
    if malaysian:
        return OriginDecision("malaysian", "malaysian_supported_pattern")
    if singaporean:
        return OriginDecision("singaporean", "singaporean_supported_pattern")
    return OriginDecision("unknown", "unsupported_plate_pattern")
