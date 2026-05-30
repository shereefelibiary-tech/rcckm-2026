from core.results import RCCKMResult
from core.enums import PlaqueCategory
from modules.recommendations.engine import build_dominant_action


def test_extensive_returns_aggressive_wording():
    result = RCCKMResult(plaque_category=PlaqueCategory.EXTENSIVE)
    message = build_dominant_action(None, result)
    assert "aggressive ApoB/LDL-C targets" in message


def test_severe_returns_intensification_wording():
    result = RCCKMResult(plaque_category=PlaqueCategory.SEVERE)
    message = build_dominant_action(None, result)
    assert "Lipid-lowering intensification is recommended" in message


def test_moderate_returns_high_risk_prevention_wording():
    result = RCCKMResult(plaque_category=PlaqueCategory.MODERATE)
    message = build_dominant_action(None, result)
    assert "high-risk prevention goals" in message


def test_mild_returns_preventive_optimization_wording():
    result = RCCKMResult(plaque_category=PlaqueCategory.MILD)
    message = build_dominant_action(None, result)
    assert "Review lipid targets" in message


def test_none_returns_no_plaque_wording():
    result = RCCKMResult(plaque_category=PlaqueCategory.NONE)
    message = build_dominant_action(None, result)
    assert "No plaque identified" in message
