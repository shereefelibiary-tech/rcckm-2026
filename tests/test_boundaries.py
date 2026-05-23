import pytest

from core.enums import PlaqueCategory, RiskLevel
from core.patient import Patient
from modules.kdigo.engine import classify_albuminuria_stage, classify_egfr_stage
from modules.plaque.engine import build_plaque_result
from modules.prevent.engine import classify_prevent_ascvd_risk
from tests.validation_helpers import diagnosis_names, evaluate_dict


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (2.99, RiskLevel.LOW),
        (3.00, RiskLevel.BORDERLINE),
        (4.99, RiskLevel.BORDERLINE),
        (5.00, RiskLevel.INTERMEDIATE),
        (9.99, RiskLevel.INTERMEDIATE),
        (10.00, RiskLevel.HIGH),
    ],
)
def test_prevent_category_thresholds(value, expected):
    assert classify_prevent_ascvd_risk(value) == expected


@pytest.mark.parametrize(
    ("cac", "expected"),
    [
        (None, PlaqueCategory.UNKNOWN),
        (0, PlaqueCategory.NONE),
        (1, PlaqueCategory.MILD),
        (99, PlaqueCategory.MILD),
        (100, PlaqueCategory.MODERATE),
        (299, PlaqueCategory.MODERATE),
        (300, PlaqueCategory.SEVERE),
        (999, PlaqueCategory.SEVERE),
        (1000, PlaqueCategory.EXTENSIVE),
    ],
)
def test_cac_thresholds(cac, expected):
    assert build_plaque_result(Patient(age=55, sex="male", cac=cac)).plaque_category == expected


@pytest.mark.parametrize(
    ("a1c", "expected"),
    [(5.6, None), (5.7, "Prediabetes"), (6.4, "Prediabetes"), (6.5, "Type 2 diabetes")],
)
def test_a1c_thresholds(a1c, expected):
    _patient, result = evaluate_dict({"age": 55, "sex": "male", "a1c": a1c})
    names = diagnosis_names(result)
    if expected is None:
        assert not any("Prediabetes" in name or "Type 2 diabetes" in name for name in names)
    else:
        assert any(expected in name for name in names)


@pytest.mark.parametrize(
    ("egfr", "expected"),
    [(60, "G2"), (59, "G3a"), (45, "G3a"), (44, "G3b"), (30, "G3b"), (29, "G4")],
)
def test_egfr_thresholds(egfr, expected):
    assert classify_egfr_stage(egfr) == expected


@pytest.mark.parametrize(
    ("uacr", "expected"),
    [(None, None), (0, "A1"), (9, "A1"), (10, "A1"), (29, "A1"), (30, "A2"), (299, "A2"), (300, "A3")],
)
def test_uacr_thresholds(uacr, expected):
    assert classify_albuminuria_stage(uacr) == expected


@pytest.mark.parametrize(
    ("value", "unit", "diagnosed"),
    [
        (75, "nmol/L", False),
        (124, "nmol/L", False),
        (125, "nmol/L", True),
        (249, "nmol/L", True),
        (250, "nmol/L", True),
        (430, "nmol/L", True),
        (30, "mg/dL", False),
        (49, "mg/dL", False),
        (50, "mg/dL", True),
        (99, "mg/dL", True),
        (100, "mg/dL", True),
    ],
)
def test_lpa_thresholds(value, unit, diagnosed):
    _patient, result = evaluate_dict({"age": 55, "sex": "female", "lp_a_value": value, "lp_a_unit": unit})
    has_lpa_dx = any("lipoprotein(a)" in name for name in diagnosis_names(result))
    assert has_lpa_dx is diagnosed


@pytest.mark.parametrize(
    ("apob", "diagnosed"),
    [(79, False), (80, False), (99, False), (100, True), (119, True), (120, True)],
)
def test_apob_thresholds(apob, diagnosed):
    _patient, result = evaluate_dict({"age": 55, "sex": "male", "apob": apob})
    assert any("Elevated ApoB" in name for name in diagnosis_names(result)) is diagnosed


@pytest.mark.parametrize(
    ("tg", "expected"),
    [
        (149, None),
        (150, "Hypertriglyceridemia"),
        (499, "Hypertriglyceridemia"),
        (500, "Severe hypertriglyceridemia"),
        (999, "Severe hypertriglyceridemia"),
        (1000, "Severe hypertriglyceridemia"),
    ],
)
def test_triglyceride_thresholds(tg, expected):
    _patient, result = evaluate_dict({"age": 55, "sex": "male", "triglycerides": tg})
    names = diagnosis_names(result)
    if expected is None:
        assert not any("triglyceridemia" in name for name in names)
    else:
        assert any(expected in name for name in names)


@pytest.mark.parametrize(
    ("ldl", "expected_dx"),
    [
        (69, False),
        (70, False),
        (99, False),
        (100, False),
        (129, False),
        (130, False),
        (159, False),
        (160, False),
        (189, False),
        (190, True),
    ],
)
def test_ldl_thresholds(ldl, expected_dx):
    _patient, result = evaluate_dict({"age": 55, "sex": "male", "ldl_c": ldl})
    assert any("Severe hypercholesterolemia" in name for name in diagnosis_names(result)) is expected_dx
