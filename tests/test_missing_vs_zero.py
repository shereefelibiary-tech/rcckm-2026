from core.engine import evaluate_patient
from ui.input_worksheet import build_patient_from_inputs
from renderers.where_patient_falls import build_where_patient_falls_html


def test_missing_numeric_fields_stay_none_and_do_not_render_as_zero():
    patient = build_patient_from_inputs({})
    result = evaluate_patient(patient)
    html = build_where_patient_falls_html(patient, result)

    for field in (
        "age",
        "sbp",
        "dbp",
        "tc",
        "ldl_c",
        "hdl_c",
        "triglycerides",
        "apob",
        "lp_a_value",
        "a1c",
        "bmi",
        "egfr",
        "uacr",
        "hscrp",
        "cac",
    ):
        assert getattr(patient, field) is None

    assert patient.cac_not_done is False
    assert result.prevent_available is False
    assert "UACR missing" in html
    assert "ApoB missing" in html
    assert "Lp(a) missing" in html
    assert "hsCRP missing" in html
    assert "Plaque unmeasured" in html
    assert "UACR 0" not in html
    assert "ApoB 0" not in html
    assert "Lp(a) 0" not in html
    assert "hsCRP 0" not in html


def test_true_zero_values_are_preserved_as_measured_zero():
    patient = build_patient_from_inputs({"age": 55, "sex": "male", "cac": "0", "uacr": "0", "hscrp": "0"})
    result = evaluate_patient(patient)
    html = build_where_patient_falls_html(patient, result, show_not_active=True)

    assert patient.cac == 0
    assert patient.cac_not_done is False
    assert patient.uacr == 0
    assert patient.hscrp == 0
    assert "CAC 0" in html
    assert "UACR 0 mg/g" in html
    assert "hsCRP 0.0 mg/L" in html
    assert "Plaque unmeasured" not in html


def test_cac_not_done_is_not_cac_zero():
    patient = build_patient_from_inputs({"age": 55, "sex": "male", "cac": None, "cac_not_done": True})
    result = evaluate_patient(patient)
    html = build_where_patient_falls_html(patient, result)

    assert patient.cac is None
    assert patient.cac_not_done is True
    assert "No CAC performed" in html
    assert "CAC 0" not in html
