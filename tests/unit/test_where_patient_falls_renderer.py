import pytest

from core.patient import Patient
from ui.report_layout import run_patient
from renderers.where_patient_falls import build_where_patient_falls_html


def _row_snippet(html: str, marker: str) -> str:
    idx = html.index(marker)
    return html[idx : idx + 1500]


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

    html = build_where_patient_falls_html(patient, result)

    assert "WHERE THIS PATIENT FALLS" in html
    assert "Inputs, missing data, and level-driving findings." in html
    assert "Active findings:" not in html
    assert "Active signals:" not in html
    assert "ApoB ApoB" not in html
    assert "A1c A1c" not in html
    assert "CAC CAC" not in html
    assert "<table class=\"wpf-table\">" in html
    assert "<th>Marker</th><th>Patient</th><th>Level effect</th>" in html
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
    assert "LIVER / MASLD" in html
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
    assert "MASLD reported" in html
    assert "Inflammation" not in html
    assert "LP(A)" in html
    assert "very high risk" in html
    assert "major driver" in html
    assert "wpf-patient-pill" in html
    assert "wpf-domain-row" in html
    assert "grid-template-columns" not in html
    assert "--rc-garnet: #73000A" in html
    assert "background: rgba(115,0,10,0.045)" in html
    assert "background: var(--rc-garnet)" in html
    assert "border: 2px solid rgba(115,0,10,0.72)" in html
    assert "background: var(--rc-garnet-deep)" in html


def test_where_patient_falls_surfaces_missing_clarifiers():
    patient = Patient(age=60, sex="male", ldl_c=140, prevent_10y_ascvd=8.2)
    result, _rss_total, _contributions = run_patient(patient)

    html = build_where_patient_falls_html(patient, result)

    assert "ApoB missing" in html
    assert "Plaque unmeasured" in html
    assert "missing" in html


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
        (74, "nmol/L", "no major signal", ["mild/context", "elevated", "high", "very high"]),
        (80, "nmol/L", "mild/context", ["major driver", "elevated", "high", "very high"]),
        (124, "nmol/L", "mild/context", ["major driver", "elevated", "high", "very high"]),
        (125, "nmol/L", "elevated", ["major driver", "mild/context", "high", "very high"]),
        (250, "nmol/L", "high", ["major driver", "mild/context", "elevated", "very high"]),
        (430, "nmol/L", "very high", ["major driver", "mild/context", "elevated"]),
        (29, "mg/dL", "no major signal", ["mild/context", "elevated", "high", "very high"]),
        (30, "mg/dL", "mild/context", ["major driver", "elevated", "high", "very high"]),
        (50, "mg/dL", "elevated", ["major driver", "mild/context", "high", "very high"]),
        (100, "mg/dL", "high", ["major driver", "mild/context", "elevated", "very high"]),
        (180, "mg/dL", "very high", ["major driver", "mild/context", "elevated"]),
    ],
)
def test_where_patient_falls_lpa_threshold_tiers(
    value, unit, expected_effect, unexpected_effects
):
    patient = Patient(age=60, sex="male", lp_a_value=value, lp_a_unit=unit)
    result, _rss_total, _contributions = run_patient(patient)

    html = build_where_patient_falls_html(patient, result)
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

    assert "Lp(a) missing" in row
    assert ">clarifier<" in row
    assert "nmol/L: &lt;75 reference; 75-124 mild; &gt;=125 elevated; &gt;=250 high; &gt;=430 very high" in row
    assert "mg/dL: &lt;30 reference; 30-49 mild; &gt;=50 elevated; &gt;=100 high; &gt;=180 very high" in row
    assert "genetics" not in row.lower()
    assert "inherited risk" not in row.lower()


@pytest.mark.parametrize(
    ("apob", "expected_effect", "unexpected_effects"),
    [
        (72, "no major signal", ["mild signal", "elevated", "major driver / risk-enhancing", "severe particle burden"]),
        (82, "mild signal", ["elevated", "major driver / risk-enhancing", "severe particle burden"]),
        (99, "mild signal", ["elevated", "major driver / risk-enhancing", "severe particle burden"]),
        (100, "elevated", ["major driver / risk-enhancing", "severe particle burden"]),
        (119, "elevated", ["major driver / risk-enhancing", "severe particle burden"]),
        (120, "major driver / risk-enhancing", ["severe particle burden"]),
        (140, "severe particle burden", []),
    ],
)
def test_where_patient_falls_apob_severity_thresholds(apob, expected_effect, unexpected_effects):
    patient = Patient(age=60, sex="male", apob=apob)

    html = build_where_patient_falls_html(patient, run_patient(patient)[0])
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

    assert "mild signal" in _row_snippet(mild_html, "A1c / diabetes")
    assert "major driver" in _row_snippet(major_html, "A1c / diabetes")


def test_where_patient_falls_kidney_severity_thresholds():
    egfr_patient = Patient(age=60, sex="male", egfr=55)
    uacr_patient = Patient(age=60, sex="male", uacr=45)

    egfr_html = build_where_patient_falls_html(egfr_patient, run_patient(egfr_patient)[0])
    uacr_html = build_where_patient_falls_html(uacr_patient, run_patient(uacr_patient)[0])

    assert "major driver" in _row_snippet(egfr_html, "eGFR / UACR")
    assert "major driver" in _row_snippet(uacr_html, "eGFR / UACR")


def test_where_patient_falls_hscrp_alone_is_not_red_major():
    patient = Patient(age=60, sex="male", hscrp=2.5)
    result, _rss_total, _contributions = run_patient(patient)

    html = build_where_patient_falls_html(patient, result)
    row = _row_snippet(html, "hsCRP")

    assert "mild signal" in row
    assert "major driver" not in row


def test_where_patient_falls_current_smoking_is_major_driver():
    patient = Patient(age=60, sex="male", smoker=True)
    result, _rss_total, _contributions = run_patient(patient)

    html = build_where_patient_falls_html(patient, result)

    assert "major driver" in _row_snippet(html, "Current smoking")
