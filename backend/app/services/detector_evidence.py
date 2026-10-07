"""Checked-in aggregate evidence; never run inference from the dashboard."""

import json
from pathlib import Path

EVIDENCE_PATH = Path(__file__).resolve().parents[1] / "evidence" / "sg_detector.json"


def singaporean_detector_evidence():
    try:
        result = json.loads(EVIDENCE_PATH.read_text(encoding="utf8"))
    except (OSError, ValueError):
        return None
    if result.get("verified") is not True or result.get("fine_tuned_on_singaporean") is not False:
        return None
    return result
