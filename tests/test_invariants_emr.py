from __future__ import annotations

import re

from core.patient import Patient
from tests.helpers import assert_absent, assert_no_contradictions, assert_present, render_case_output


EMR_FORBIDDEN = (
    "<div",
    "</div>",
    "<span",
    "</span>",
    "Impression:",
    "HCC-supported",
    "Atherogenic/metabolic burden:",
    "Recheck lipid profile",
    "dominant_action",
    "action_domains",
    "risk_continuum_sublevel",
    "None",
    "null",
    "NaN",
    "{{",
    "}}",
)


def test_emr_is_plain_text_concise_and_copy_paste_ready():
    bundle = render_case_output(
        Patient(
            age=61,
            sex="female",
            tc=218,
            ldl_c=124,
            hdl_c=56,
            triglycerides=190,
            cac=350,
            diabetes=False,
            prevent_10y_ascvd=10.16,
            prevent_30y_ascvd=30.65,
        )
    )
    emr = bundle["outputs"]["emr"]
    assert emr.startswith("RISK CONTINUUM CKM\n\nLevel")
    assert_present(emr, ("Assessment:", "Recommendations:", "PREVENT: ASCVD 10y", "30y"))
    assert_absent(emr, EMR_FORBIDDEN)
    assert_no_contradictions(emr)


def test_emr_does_not_include_long_statin_example_lists_by_default():
    emr = render_case_output(Patient(age=50, sex="male", ldl_c=204, tc=280, hdl_c=45, triglycerides=150))["outputs"]["emr"]
    assert "High-intensity lipid-lowering therapy indicated" in emr
    assert "Atorvastatin 40-80" not in emr
    assert "Rosuvastatin 20-40" not in emr


def test_emr_recommendations_are_domain_specific_not_vague():
    emr = render_case_output(Patient(age=60, sex="female", diabetes=True, egfr=52, uacr=210, ldl_c=132))["outputs"]["emr"]
    assert any(domain in emr for domain in ("lipid", "statin", "kidney", "glycemic", "BP", "SGLT2"))
    assert "risk-factor control" not in emr.lower()
    assert "pharmacotherapy" not in emr.lower()


def test_emr_has_no_duplicate_diagnosis_or_recommendation_lines():
    emr = render_case_output(Patient(age=60, sex="female", diabetes=True, egfr=52, uacr=210, ldl_c=132))["outputs"]["emr"]
    lines = [line.strip() for line in emr.splitlines() if line.strip().startswith("- ")]
    assert len(lines) == len(set(lines))
    assert not re.search(r"<[^>]+>", emr)
