import pytest

from core.patient import Patient
from ui.report_layout import run_patient
from renderers.where_patient_falls import (
    build_where_patient_falls_html,
    normalize_risk_impact_label,
)


def _row_snippet(html: str, marker: str) -> str:
    idx = html.index(marker)
    end = html.index("</tr>", idx)
    return html[idx : end + len("</tr>")]


def test_where_patient_falls_displays_measured_values_and_effects():
    patient = Patient(
        age=60,
        sex="male",
        cac=350,
        apob=110,
        ldl_c=115,
        a1c=7.1,
        diabetes=True,
        egfr=55,
        uacr=45,
        lp_a_value=180,
        lp_a_unit="nmol/L",
        smoker=True,
        hscrp=4.2,
        rheumatoid_arthritis=True,
        osa=True,
        masld=True,
    )
    result, _rss_total, _contributions = run_patient(patient)

    html = build_where_patient_falls_html(patient, result, show_not_active=True)

    assert "WHERE THIS PATIENT FALLS" in html
    assert "Inputs, available data, and level-driving findings." in html
    assert "Risk impact: Major = changes level/action" in html
    assert "Contributes = supports risk" in html
    assert "Context = background" in html
    assert "Not active = audit only" in html
    assert "supports risk interpretation" not in html
    assert "not currently contributing" not in html
    assert "Active findings:" not in html
    assert "Active signals:" not in html
    assert "ApoB ApoB" not in html
    assert "A1c A1c" not in html
    assert "CAC CAC" not in html
    assert "<table class=\"wpf-table\">" in html
    assert "<th>Marker</th><th>Patient</th><th>Risk impact</th>" in html
    assert "colspan=\"3\"" in html
    assert "<td class=\"wpf-marker\">" in html
    assert "<td class=\"wpf-patient\">" in html
    assert "<td class=\"wpf-effect\">" in html
    assert "Level 5" in html
    assert "ATHEROGENIC BURDEN" in html
    assert "GLYCEMIA" in html
    assert "KIDNEY (EGFR/UACR)" in html
    assert "LP(A)" in html
    assert "FAMILY HISTORY" in html
    assert "SMOKING" in html
    assert "HSCRP" in html
    assert "INFLAMMATORY DISEASE" in html
    assert "SLEEP / HYPOXIA" in html
    assert "LIVER / FATTY LIVER" in html
    assert "PLAQUE / CAC" in html
    assert "ApoB 110 mg/dL" in html
    assert "LDL-C 115 mg/dL" in html
    assert "&lt;80 optimal/goal if treated; 80-99 mild; 100-119 elevated; &gt;=120 risk-enhancing; &gt;=140 severe" in html
    assert "A1c 7.1%" in html
    assert "eGFR 55" in html
    assert "UACR 45 mg/g" in html
    assert "Lp(a) 180 nmol/L" in html
    assert "CAC 350" in html
    assert "RA" in html
    assert "hsCRP" in html
    assert "&gt;=2 mg/L is interpreted in clinical context" in html
    assert "OSA reported" in html
    assert "Metabolic fatty liver disease" in html
    assert "MASLD reported" in html
    assert "Inflammation" not in html
    assert "LP(A)" in html
    assert "Major driver" in html
    assert "wpf-patient-pill" in html
    assert "wpf-domain-row" in html
    assert "grid-template-columns" not in html
    assert "--rc-garnet: #73000A" in html
    assert "background: rgba(115,0,10,0.045)" in html
    assert "background: var(--rc-garnet)" in html
    assert "border: 2px solid rgba(115,0,10,0.72)" in html


def test_where_patient_falls_surfaces_missing_clarifiers():
    patient = Patient(age=60, sex="male", ldl_c=140, prevent_10y_ascvd=8.2)
    result, _rss_total, _contributions = run_patient(patient)

    html = build_where_patient_falls_html(patient, result)

    assert "ApoB not available" in html
    assert "Plaque unmeasured" in html
    assert "not available" in html


def test_where_patient_falls_does_not_label_missing_needed_data_as_context_only():
    patient = Patient(
        age=43,
        sex="female",
        ldl_c=146,
        apob=122,
        sbp=124,
        dbp=76,
        bmi=28.1,
        egfr=96,
        a1c=None,
        uacr=None,
        lp_a_value=None,
        cac=None,
        cac_not_done=True,
    )
    result, _rss_total, _contributions = run_patient(patient)

    html = build_where_patient_falls_html(patient, result, show_not_active=True)

    a1c_row = _row_snippet(html, "A1c / diabetes")
    kidney_row = _row_snippet(html, "eGFR / UACR")
    lpa_row = _row_snippet(html, "Lp(a)")
    cac_row = _row_snippet(html, "No CAC performed")

    assert "A1c not available" in a1c_row
    assert "Missing / needed" in a1c_row
    assert "Context only" not in a1c_row
    assert "UACR not available" in kidney_row
    assert "Missing / needed" in kidney_row
    assert "Context only" not in kidney_row
    assert "Lp(a) not available" in lpa_row
    assert "Missing / needed" in lpa_row
    assert "Context only" not in lpa_row
    assert "No CAC performed" in cac_row
    assert "Not measured / may clarify risk" in cac_row
    assert "Context only" not in cac_row


def test_where_patient_falls_shows_cac_percentile_as_clinician_detail_when_useful():
    patient = Patient(age=45, sex="male", cac=38, cac_percentile=82)
    result, _rss_total, _contributions = run_patient(patient)

    html = build_where_patient_falls_html(patient, result)

    assert "CAC 38; Higher than expected for age and sex. Clinician detail: 82th percentile." in html


def test_where_patient_falls_omits_invalid_or_zero_cac_percentile_context():
    cac_zero = Patient(age=45, sex="male", cac=0, cac_percentile=99)
    zero_result, _rss_total, _contributions = run_patient(cac_zero)
    zero_html = build_where_patient_falls_html(cac_zero, zero_result, show_not_active=True)
    assert "CAC 0" in zero_html
    assert "99th percentile" not in zero_html

    invalid = Patient(age=45, sex="male", cac=38, cac_percentile=120)
    invalid_result, _rss_total, _contributions = run_patient(invalid)
    invalid_html = build_where_patient_falls_html(invalid, invalid_result)
    assert "CAC 38" in invalid_html
    assert "percentile" not in invalid_html.lower()


def test_where_patient_falls_marks_level_defining_cac_as_major_driver():
    patient = Patient(
        age=58,
        sex="male",
        cac=145,
        cac_percentile=91,
        ldl_c=124,
        apob=112,
        lp_a_value=238,
        lp_a_unit="nmol/L",
        premature_fhx_ascvd=True,
        family_history_premature_ascvd=True,
        family_history_summary="father MI age 54",
        a1c=5.9,
        egfr=78,
        uacr=14,
    )
    result, _rss_total, _contributions = run_patient(patient)

    html = build_where_patient_falls_html(patient, result)

    assert result.level_classification["level"] == "4"
    cac_row = _row_snippet(html, "CAC 145")
    assert "CAC 145" in cac_row
    assert "91th percentile" in cac_row
    assert ">Major driver<" in cac_row
    assert ">Contributes<" not in cac_row
    assert "Contributes" in _row_snippet(html, "ApoB / LDL-C")
    assert "Major driver" in _row_snippet(html, "Lp(a)")
    assert "Major driver" in _row_snippet(html, "Premature family history")
    assert "Contributes" in _row_snippet(html, "A1c / diabetes")
    assert "Contributes" in _row_snippet(html, "eGFR / UACR")
    assert "Missing / needed" in _row_snippet(html, "hsCRP")


def test_where_patient_falls_normalizes_risk_impact_labels():
    assert normalize_risk_impact_label("major driver") == "Major driver"
    assert normalize_risk_impact_label("very high risk") == "Major driver"
    assert normalize_risk_impact_label("elevated") == "Contributes"
    assert normalize_risk_impact_label("mild signal") == "Contributes"
    assert normalize_risk_impact_label("mild/context") == "Context only"
    assert normalize_risk_impact_label("enhancer context") == "Context only"
    assert normalize_risk_impact_label("no major signal") == "Not active"
    assert normalize_risk_impact_label("no active signal") == "Not active"


def test_where_patient_falls_uses_only_simplified_risk_impact_vocabulary():
    patient = Patient(
        age=60,
        sex="male",
        apob=110,
        lp_a_value=80,
        lp_a_unit="nmol/L",
        a1c=5.8,
        hscrp=2.5,
        preeclampsia=True,
        smoker=True,
    )
    html = build_where_patient_falls_html(
        patient,
        run_patient(patient)[0],
        show_not_active=True,
    )

    assert "Risk impact" in html
    assert "Level effect" not in html
    for label in ("Major driver", "Contributes", "Context only", "Not active"):
        assert label in html
    for old_label in (
        ">elevated<",
        ">mild signal<",
        ">mild/context<",
        ">enhancer context<",
        ">no major signal<",
        ">no active signal<",
        ">very high risk<",
    ):
        assert old_label not in html


def test_where_patient_falls_reproductive_history_uses_clean_deduplicated_labels():
    patient = Patient(
        age=48,
        sex="female",
        preeclampsia=True,
        gestational_diabetes=True,
        premature_menopause=True,
        early_menopause=True,
        pcos_or_irregular_menses=True,
    )
    html = build_where_patient_falls_html(patient, run_patient(patient)[0])
    row = _row_snippet(html, "Reproductive history")

    assert "Preeclampsia; gestational diabetes; premature menopause; PCOS / irregular menses" in row
    assert "Preeclampsia History of preeclampsia" not in row
    assert "Gestational diabetes Gestational diabetes" not in row
    assert row.count("premature menopause") == 1


def test_where_patient_falls_risk_impact_chip_hierarchy_is_restrained():
    patient = Patient(age=60, sex="male", apob=110, lp_a_value=80, lp_a_unit="nmol/L", smoker=True)
    html = build_where_patient_falls_html(
        patient,
        run_patient(patient)[0],
    )

    assert ".wpf-chip-major-driver" in html
    assert ".wpf-chip-contributes" in html
    assert ".wpf-chip-context-only" in html
    assert ".wpf-chip-not-active" in html
    context_block = html.split(".wpf-chip-context-only", 1)[1].split("}", 1)[0]
    not_active_block = html.split(".wpf-chip-not-active", 1)[1].split("}", 1)[0]
    contributes_block = html.split(".wpf-chip-contributes", 1)[1].split("}", 1)[0]
    major_block = html.split(".wpf-chip-major-driver", 1)[1].split("}", 1)[0]

    assert "background: transparent" in context_block
    assert "font-weight: 650" in context_block
    assert "background: transparent" in not_active_block
    assert "border: 0" in not_active_block
    assert "rgba(47, 95, 143, 0.12)" in contributes_block
    assert "font-weight: 750" in contributes_block
    assert "background: var(--rc-garnet)" in major_block
    assert "font-weight: 800" in major_block


def test_where_patient_falls_risk_impact_rows_have_hierarchy_classes():
    patient = Patient(
        age=60,
        sex="male",
        apob=110,
        lp_a_value=80,
        lp_a_unit="nmol/L",
        smoker=True,
    )
    html = build_where_patient_falls_html(patient, run_patient(patient)[0])

    assert "marker-row-major-driver" in html
    assert "marker-row-contributes" in html
    assert "marker-row-context-only" in html
    assert "marker-row-not-active" in html
    assert ".wpf-row.marker-row-context-only" in html
    assert ".wpf-row.marker-row-not-active" in html
    assert "rgba(7, 26, 47, 0.52)" in html
    assert "rgba(7, 26, 47, 0.42)" in html


def test_where_patient_falls_hides_not_active_rows_by_default():
    patient = Patient(age=60, sex="male", apob=72, lp_a_value=74, lp_a_unit="nmol/L")
    result = run_patient(patient)[0]

    html = build_where_patient_falls_html(patient, result)
    full_html = build_where_patient_falls_html(patient, result, show_not_active=True)

    assert "ApoB 72 mg/dL" not in html
    assert "Lp(a) 74 nmol/L" not in html
    assert "ApoB 72 mg/dL" in full_html
    assert "Lp(a) 74 nmol/L" in full_html


def test_where_patient_falls_sorts_abnormal_rows_before_context_and_not_active():
    patient = Patient(
        age=60,
        sex="male",
        smoker=True,
        apob=110,
        lp_a_value=80,
        lp_a_unit="nmol/L",
    )
    html = build_where_patient_falls_html(patient, run_patient(patient)[0])
    full_html = build_where_patient_falls_html(
        patient,
        run_patient(patient)[0],
        show_not_active=True,
    )

    assert html.index("Current smoking") < html.index("ApoB / LDL-C")
    assert html.index("ApoB / LDL-C") < html.index("Lp(a)")
    assert full_html.index("Lp(a)") < full_html.index("Premature family history")


def test_where_patient_falls_keeps_missing_clarifiers_visible_by_default():
    patient = Patient(age=60, sex="male", ldl_c=140, prevent_10y_ascvd=8.2)
    html = build_where_patient_falls_html(patient, run_patient(patient)[0])

    assert "ApoB not available" in html
    assert "Lp(a) not available" in html
    assert "UACR not available" in html
    assert "Plaque unmeasured" in html
    assert "Missing / needed" in html


def test_where_patient_falls_shows_hiv_separately_from_inflammatory_disease():
    patient = Patient(age=55, sex="male", hiv=True, inflammatory_disease=False)
    result, _rss_total, _contributions = run_patient(patient)

    html = build_where_patient_falls_html(patient, result)

    assert "HIV" in html
    assert "HIV reported" in html
    assert "guideline risk-enhancing pathway" in html
    assert "RA, SLE, psoriasis, IBD, HIV" not in html


@pytest.mark.parametrize(
    ("value", "unit", "expected_effect", "unexpected_effects"),
    [
        (74, "nmol/L", "Not active", ["Context only", "Contributes", "Major driver"]),
        (80, "nmol/L", "Context only", ["Not active", "Contributes", "Major driver"]),
        (124, "nmol/L", "Context only", ["Not active", "Contributes", "Major driver"]),
        (125, "nmol/L", "Contributes", ["Not active", "Context only", "Major driver"]),
        (250, "nmol/L", "Major driver", ["Not active", "Context only", "Contributes"]),
        (430, "nmol/L", "Major driver", ["Not active", "Context only", "Contributes"]),
        (29, "mg/dL", "Not active", ["Context only", "Contributes", "Major driver"]),
        (30, "mg/dL", "Context only", ["Not active", "Contributes", "Major driver"]),
        (50, "mg/dL", "Contributes", ["Not active", "Context only", "Major driver"]),
        (100, "mg/dL", "Major driver", ["Not active", "Context only", "Contributes"]),
        (180, "mg/dL", "Major driver", ["Not active", "Context only", "Contributes"]),
    ],
)
def test_where_patient_falls_lpa_threshold_tiers(
    value, unit, expected_effect, unexpected_effects
):
    patient = Patient(age=60, sex="male", lp_a_value=value, lp_a_unit=unit)
    result, _rss_total, _contributions = run_patient(patient)

    html = build_where_patient_falls_html(
        patient,
        result,
        show_not_active=(expected_effect == "Not active"),
    )
    row = _row_snippet(html, "Lp(a)")

    assert f"Lp(a) {value} {unit}" in row
    assert f">{expected_effect}<" in row
    for effect in unexpected_effects:
        assert f">{effect}<" not in row
    assert "nmol/L: &lt;75 reference; 75-124 mild; &gt;=125 elevated; &gt;=250 high; &gt;=430 very high" in row
    assert "mg/dL: &lt;30 reference; 30-49 mild; &gt;=50 elevated; &gt;=100 high; &gt;=180 very high" in row
    assert "genetics" not in row.lower()
    assert "inherited risk" not in row.lower()


def test_where_patient_falls_lpa_missing_shows_clarifier_and_thresholds():
    patient = Patient(age=60, sex="male")
    result, _rss_total, _contributions = run_patient(patient)

    html = build_where_patient_falls_html(patient, result)
    row = _row_snippet(html, "Lp(a)")

    assert "Lp(a) not available" in row
    assert ">Missing / needed<" in row
    assert "nmol/L: &lt;75 reference; 75-124 mild; &gt;=125 elevated; &gt;=250 high; &gt;=430 very high" in row
    assert "mg/dL: &lt;30 reference; 30-49 mild; &gt;=50 elevated; &gt;=100 high; &gt;=180 very high" in row
    assert "genetics" not in row.lower()
    assert "inherited risk" not in row.lower()


@pytest.mark.parametrize(
    ("apob", "expected_effect", "unexpected_effects"),
    [
        (72, "Not active", ["Contributes", "Major driver"]),
        (82, "Contributes", ["Not active", "Major driver"]),
        (99, "Contributes", ["Not active", "Major driver"]),
        (100, "Contributes", ["Not active", "Major driver"]),
        (119, "Contributes", ["Not active", "Major driver"]),
        (120, "Major driver", ["Not active", "Contributes"]),
        (140, "Major driver", ["Not active", "Contributes"]),
    ],
)
def test_where_patient_falls_apob_severity_thresholds(apob, expected_effect, unexpected_effects):
    patient = Patient(age=60, sex="male", apob=apob)

    html = build_where_patient_falls_html(
        patient,
        run_patient(patient)[0],
        show_not_active=(expected_effect == "Not active"),
    )
    row = _row_snippet(html, "ApoB / LDL-C")

    assert f"ApoB {apob} mg/dL" in row
    assert f">{expected_effect}<" in row
    for effect in unexpected_effects:
        assert f">{effect}<" not in row
    assert "&lt;80 optimal/goal if treated; 80-99 mild; 100-119 elevated; &gt;=120 risk-enhancing; &gt;=140 severe" in row
    if 100 <= apob <= 119:
        assert "guideline risk enhancer" not in row
        assert "guideline risk-enhancing" not in row


def test_where_patient_falls_glycemia_severity_thresholds():
    mild = Patient(age=60, sex="male", a1c=5.8)
    major = Patient(age=60, sex="male", a1c=7.1)

    mild_html = build_where_patient_falls_html(mild, run_patient(mild)[0])
    major_html = build_where_patient_falls_html(major, run_patient(major)[0])

    assert "Contributes" in _row_snippet(mild_html, "A1c / diabetes")
    assert "Major driver" in _row_snippet(major_html, "A1c / diabetes")


def test_where_patient_falls_kidney_severity_thresholds():
    egfr_patient = Patient(age=60, sex="male", egfr=55)
    uacr_patient = Patient(age=60, sex="male", uacr=45)

    egfr_html = build_where_patient_falls_html(egfr_patient, run_patient(egfr_patient)[0])
    uacr_html = build_where_patient_falls_html(uacr_patient, run_patient(uacr_patient)[0])

    assert "Major driver" in _row_snippet(egfr_html, "eGFR / UACR")
    assert "Major driver" in _row_snippet(uacr_html, "eGFR / UACR")


def test_where_patient_falls_hscrp_alone_is_not_red_major():
    patient = Patient(age=60, sex="male", hscrp=2.5)
    result, _rss_total, _contributions = run_patient(patient)

    html = build_where_patient_falls_html(patient, result)
    row = _row_snippet(html, "hsCRP")

    assert "Contributes" in row
    assert ">Major driver<" not in row


def test_where_patient_falls_current_smoking_is_major_driver():
    patient = Patient(age=60, sex="male", smoker=True)
    result, _rss_total, _contributions = run_patient(patient)

    html = build_where_patient_falls_html(patient, result)

    assert "Major driver" in _row_snippet(html, "Current smoking")
