from core.enums import RiskLevel
from core.patient import Patient
from core.results import RCCKMResult
from modules.discordance.engine import build_discordance_insight


def test_build_discordance_insight_returns_none_without_prevent():
    patient = Patient(age=60, sex="male", cac=300)
    result = RCCKMResult(prevent_10y_ascvd=None)

    assert build_discordance_insight(patient, result) is None


def test_build_discordance_insight_plaque_exceeds_population_risk():
    patient = Patient(age=60, sex="male", cac=300)
    result = RCCKMResult(
        prevent_10y_ascvd=8.0,
        prevent_risk_category=RiskLevel.INTERMEDIATE,
    )

    insight = build_discordance_insight(patient, result)

    assert insight["status"] == "discordant"
    assert insight["type"] == "plaque_exceeds_population_risk"


def test_build_discordance_insight_risk_exceeds_plaque_burden():
    patient = Patient(age=60, sex="male", cac=0)
    result = RCCKMResult(
        prevent_10y_ascvd=10.0,
        prevent_risk_category=RiskLevel.HIGH,
    )

    insight = build_discordance_insight(patient, result)

    assert insight["status"] == "discordant"
    assert insight["type"] == "risk_exceeds_plaque_burden"


def test_build_discordance_insight_high_risk_with_cac_missing():
    patient = Patient(age=60, sex="male", cac=None)
    result = RCCKMResult(
        prevent_10y_ascvd=10.0,
        prevent_risk_category=RiskLevel.HIGH,
    )

    insight = build_discordance_insight(patient, result)

    assert insight["status"] == "uncertain"
    assert insight["type"] == "high_population_risk_plaque_unmeasured"


def test_build_discordance_insight_aligned():
    patient = Patient(age=60, sex="male", cac=10)
    result = RCCKMResult(
        prevent_10y_ascvd=4.0,
        prevent_risk_category=RiskLevel.BORDERLINE,
    )

    insight = build_discordance_insight(patient, result)

    assert insight["status"] == "aligned"
    assert insight["type"] == "no_major_discordance"
