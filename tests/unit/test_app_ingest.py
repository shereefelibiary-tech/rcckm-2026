from app import build_patient_from_inputs, parse_ingest_text
from core.engine import evaluate_patient
from modules.rss.engine import build_rss_contributions, calculate_rss_total
from renderers.where_patient_falls import build_where_patient_falls_html
from ui.input_worksheet import normalize_input_aliases, patient_to_payload


def test_parse_ingest_text_extracts_common_fields():
    text = """
    60M. BP 132/78. TC 210 LDL 142 HDL 42 TG 180.
    ApoB 118. Lp(a) 180 nmol/L. A1c 7.1%.
    eGFR 55 UACR 45 mg/g CAC 350 BMI 31.
    Father MI age 49.
    Current smoker on statin and SGLT2.
    """

    parsed = parse_ingest_text(text)

    assert parsed["age"] == 60
    assert parsed["sex"] == "male"
    assert parsed["sbp"] == 132
    assert parsed["dbp"] == 78
    assert parsed["tc"] == 210
    assert parsed["ldl_c"] == 142
    assert parsed["hdl_c"] == 42
    assert parsed["triglycerides"] == 180
    assert parsed["apob"] == 118
    assert parsed["lp_a_value"] == 180
    assert parsed["lp_a_unit"] == "nmol/L"
    assert parsed["a1c"] == 7.1
    assert parsed["egfr"] == 55
    assert parsed["uacr"] == 45
    assert parsed["cac"] == 350
    assert parsed["bmi"] == 31
    assert parsed["family_history_relationship"] == "father"
    assert parsed["family_history_event_type"] == "mi"
    assert parsed["family_history_age_at_event"] == 49
    assert parsed["smoker"] is True
    assert parsed["lipid_lowering"] is True
    assert parsed["sglt2"] is True


def test_build_patient_from_inputs_uses_reviewed_values():
    inputs = {
        "age": 61,
        "sex": "female",
        "tc": 210,
        "ldl_c": 142,
        "hdl_c": 42,
        "triglycerides": 180,
        "apob": 118,
        "lp_a_value": 180,
        "lp_a_unit": "nmol/L",
        "a1c": 7.1,
        "diabetes": True,
        "bmi": 31,
        "egfr": 55,
        "uacr": 45,
        "cac": 350,
        "sbp": 132,
        "dbp": 78,
        "bp_treated": True,
        "smoker": True,
        "family_history_premature_ascvd": True,
        "family_history_relationship": "mother",
        "family_history_event_type": "stroke",
        "family_history_age_at_event": 61,
        "hscrp": 4.2,
        "rheumatoid_arthritis": True,
        "osa": True,
        "masld": True,
        "lipid_lowering": True,
        "sglt2": True,
        "glp1": True,
        "ace_arb": True,
    }

    patient = build_patient_from_inputs(inputs)

    assert patient.age == 61
    assert patient.sex == "female"
    assert patient.tc == 210
    assert patient.ldl_c == 142
    assert patient.hdl_c == 42
    assert patient.triglycerides == 180
    assert patient.apob == 118
    assert patient.lp_a_value == 180
    assert patient.lp_a_unit == "nmol/L"
    assert patient.a1c == 7.1
    assert patient.diabetes is True
    assert patient.bmi == 31
    assert patient.egfr == 55
    assert patient.uacr == 45
    assert patient.cac == 350
    assert patient.sbp == 132
    assert patient.dbp == 78
    assert patient.bp_treated is True
    assert patient.smoker is True
    assert patient.smoking is True
    assert patient.family_history_premature_ascvd is True
    assert patient.premature_fhx_ascvd is True
    assert patient.family_history_relationship == "mother"
    assert patient.family_history_event_type == "stroke"
    assert patient.family_history_age_at_event == 61
    assert patient.family_history_summary == "Mother stroke age 61"
    assert patient.hscrp == 4.2
    assert patient.inflammatory_disease is True
    assert patient.rheumatoid_arthritis is True
    assert patient.osa is True
    assert patient.masld is True
    assert patient.lipid_lowering is True
    assert patient.sglt2 is True
    assert patient.glp1 is True
    assert patient.ace_arb is True


def test_build_patient_from_inputs_distinguishes_cac_zero_from_no_cac():
    no_cac = build_patient_from_inputs(
        {
            "age": 60,
            "sex": "male",
            "cac": None,
            "cac_not_done": True,
        }
    )
    cac_zero = build_patient_from_inputs(
        {
            "age": 60,
            "sex": "male",
            "cac": 0,
            "cac_not_done": True,
        }
    )
    blank = build_patient_from_inputs({"age": 60, "sex": "male", "cac": None})

    assert no_cac.cac is None
    assert no_cac.cac_not_done is True
    assert cac_zero.cac == 0
    assert cac_zero.cac_not_done is False
    assert blank.cac is None
    assert blank.cac_not_done is False


def test_parse_ingest_text_separates_enhancer_contexts():
    parsed = parse_ingest_text("RA with OSA and MASLD. hsCRP 3.2. HIV negative.")

    assert parsed["rheumatoid_arthritis"] is True
    assert parsed["osa"] is True
    assert parsed["masld"] is True
    assert parsed["hscrp"] == 3.2
    assert parsed["inflammatory_disease"] is False


def test_build_patient_from_inputs_accepts_common_aliases():
    patient = build_patient_from_inputs(
        {
            "age": 60,
            "sex": "male",
            "total_cholesterol": 190,
            "ldl": 115,
            "hdl": 50,
            "tg": 150,
            "lpa": 80,
            "lpa_unit": "nmol/L",
            "smoking": True,
            "premature_family_history": True,
        }
    )

    assert patient.tc == 190
    assert patient.ldl_c == 115
    assert patient.hdl_c == 50
    assert patient.triglycerides == 150
    assert patient.non_hdl_c == 140
    assert patient.lp_a_value == 80
    assert patient.lp_a_unit == "nmol/L"
    assert patient.smoker is True
    assert patient.smoking is True
    assert patient.family_history_premature_ascvd is True

    payload = patient_to_payload(patient)
    assert payload["total_cholesterol"] == 190
    assert payload["ldl"] == 115
    assert payload["hdl"] == 50
    assert payload["tg"] == 150
    assert payload["lpa"] == 80


def test_build_patient_from_inputs_ignores_invalid_cac_percentile():
    valid = build_patient_from_inputs({"age": 45, "sex": "male", "cac": 38, "cac_percentile": 75})
    invalid = build_patient_from_inputs({"age": 45, "sex": "male", "cac": 38, "cac_percentile": 101})

    assert valid.cac_percentile == 75
    assert invalid.cac_percentile is None


def test_normalize_input_aliases_manual_canonical_values_override_parsed_aliases():
    values = normalize_input_aliases(
        {
            "ldl": 180,
            "ldl_c": 130,
            "smoking": True,
            "smoker": False,
        }
    )

    assert values["ldl_c"] == 130
    assert values["smoker"] is False


def test_empty_patient_inputs_preserve_missing_numeric_values():
    patient = build_patient_from_inputs({})

    assert patient.age is None
    assert patient.sbp is None
    assert patient.dbp is None
    assert patient.tc is None
    assert patient.ldl_c is None
    assert patient.hdl_c is None
    assert patient.non_hdl_c is None
    assert patient.triglycerides is None
    assert patient.apob is None
    assert patient.lp_a_value is None
    assert patient.a1c is None
    assert patient.bmi is None
    assert patient.egfr is None
    assert patient.uacr is None
    assert patient.cac is None
    assert patient.hscrp is None

    result = evaluate_patient(patient)
    contributions = build_rss_contributions(patient, result)

    assert result.prevent_available is False
    assert result.prevent_missing_inputs
    assert calculate_rss_total(contributions) == 0

    wpf_html = build_where_patient_falls_html(patient, result, show_not_active=True)
    assert "UACR missing" in wpf_html
    assert "ApoB missing" in wpf_html
    assert "Lp(a) missing" in wpf_html
    assert "hsCRP missing" in wpf_html
    assert "Plaque unmeasured" in wpf_html
    assert "UACR 0" not in wpf_html
    assert "ApoB 0" not in wpf_html
    assert "Lp(a) 0" not in wpf_html
    assert "hsCRP 0" not in wpf_html


def test_true_zero_values_are_preserved_as_measured_values():
    patient = build_patient_from_inputs(
        {
            "age": 55,
            "sex": "male",
            "cac": "0",
            "uacr": "0",
            "hscrp": "0",
        }
    )
    result = evaluate_patient(patient)
    wpf_html = build_where_patient_falls_html(patient, result, show_not_active=True)

    assert patient.cac == 0
    assert patient.cac_not_done is False
    assert patient.uacr == 0
    assert patient.hscrp == 0
    assert "CAC 0" in wpf_html
    assert "UACR 0 mg/g" in wpf_html
    assert "hsCRP 0.0 mg/L" in wpf_html
    assert "Plaque unmeasured" not in wpf_html
