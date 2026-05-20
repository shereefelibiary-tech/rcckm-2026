from typing import Optional

from core.enums import RiskLevel


def classify_prevent_ascvd_risk(prevent_10y_ascvd: Optional[float]) -> Optional[RiskLevel]:
    if prevent_10y_ascvd is None:
        return None

    try:
        value = float(prevent_10y_ascvd)
    except (TypeError, ValueError):
        return None

    if value < 3:
        return RiskLevel.LOW

    if 3 <= value < 5:
        return RiskLevel.BORDERLINE

    if 5 <= value < 10:
        return RiskLevel.INTERMEDIATE

    return RiskLevel.HIGH
