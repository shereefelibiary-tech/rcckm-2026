from modules.prevent.engine import classify_prevent_ascvd_risk
from core.enums import RiskLevel


def test_classify_prevent_ascvd_risk_none_and_boundaries():
    assert classify_prevent_ascvd_risk(None) is None

    assert classify_prevent_ascvd_risk(2.9) == RiskLevel.LOW
    assert classify_prevent_ascvd_risk(3.0) == RiskLevel.BORDERLINE
    assert classify_prevent_ascvd_risk(4.9) == RiskLevel.BORDERLINE
    assert classify_prevent_ascvd_risk(5.0) == RiskLevel.INTERMEDIATE
    assert classify_prevent_ascvd_risk(9.9) == RiskLevel.INTERMEDIATE
    assert classify_prevent_ascvd_risk(10.0) == RiskLevel.HIGH
