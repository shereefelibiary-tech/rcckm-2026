from core.engine import evaluate_patient
from core.patient import Patient
from modules.actions.scaffold import build_action_instrument_panel
from modules.levels.level_classifier import classify_rcckm_level
from renderers.patient_roadmap import render_patient_roadmap_text
from renderers.where_patient_falls import build_where_patient_falls_html


def _case(patient: Patient):
    result = evaluate_patient(patient)
    classification = classify_rcckm_level(patient, result)
    panel = {
        item.domain_id: item for item in build_action_instrument_panel(patient, result)
    }
    roadmap = render_patient_roadmap_text(patient, result)
    where_html = build_where_patient_falls_html(patient, result)
    diagnoses = "\n".join(
        candidate.name or "" for candidate in result.diagnosis_candidates
    )
    visible = "\n".join(
        [
            classification.label,
            classification.short_reason,
            roadmap,
            where_html,
            *[
                " ".join([item.label, item.status, item.detail, item.patient_line])
                for item in panel.values()
            ],
            diagnoses,
        ]
    )
    return result, classification, panel, roadmap, where_html, diagnoses, visible


def _domain_text(panel: dict, domain_id: str) -> str:
    item = panel[domain_id]
    return " ".join(
        [
            item.label,
            item.status,
            item.detail,
            item.patient_line,
            item.emr_line,
            item.hover_detail,
        ]
    )


def _assert_general_guardrails(patient: Patient, visible: str, diagnoses: str) -> None:
    text = visible.lower()
    diagnosis_text = diagnoses.lower()
    assert "no kidney-risk signal" not in text
    assert "not routine for primary prevention" not in text
    assert "missing apob" not in text
    assert "missing uacr" not in text
    assert "missing cac" not in text
    if not getattr(patient, "lipid_lowering", False):
        assert "continue current lipid treatment" not in text
        assert "stronger cholesterol-lowering therapy" not in text
    if not getattr(patient, "clinical_ascvd", False):
        assert "secondary-prevention" not in text
        assert "clinical ascvd" not in diagnosis_text


def test_pregnancy_risk_history_plus_apob_is_not_minimal() -> None:
    patient = Patient(
        age=42,
        sex="female",
        ldl_c=155,
        apob=124,
        lp_a_value=40,
        lp_a_unit="nmol/L",
        preeclampsia=True,
        gestational_diabetes=True,
        diabetes=False,
        a1c=5.2,
        egfr=95,
        uacr=5,
        cac=None,
        cac_not_done=True,
        prevent_10y_ascvd=0.8,
        prevent_30y_ascvd=6.0,
    )

    result, classification, panel, roadmap, _, diagnoses, visible = _case(patient)

    assert classification.level in {"3A", "3B"}
    assert "Discuss" in _domain_text(panel, "lipid_lowering")
    assert "CAC may clarify" in _domain_text(panel, "plaque_cac")
    assert "Calcium scan may clarify treatment." in roadmap
    assert "Diabetes" not in diagnoses
    assert getattr(result, "kdigo_stage", None) == "G1A1"
    _assert_general_guardrails(patient, visible, diagnoses)


def test_lpa_and_premature_family_history_with_modest_ldl_keeps_inherited_context() -> None:
    patient = Patient(
        age=48,
        sex="male",
        ldl_c=118,
        apob=96,
        lp_a_value=280,
        lp_a_unit="nmol/L",
        family_history_premature_ascvd=True,
        family_history_relationship="father",
        family_history_event_type="MI",
        family_history_age_at_event=49,
        cac=None,
        cac_not_done=True,
        prevent_10y_ascvd=1.2,
        prevent_30y_ascvd=6.2,
    )

    _, classification, panel, roadmap, _, diagnoses, visible = _case(patient)

    assert classification.level != "1"
    assert "Elevated lipoprotein(a)" in diagnoses
    assert "father" in visible.lower()
    assert "MI" in visible or "mi" in visible.lower()
    assert "CAC may clarify" in _domain_text(panel, "plaque_cac")
    assert "Calcium scan may clarify treatment." in roadmap
    _assert_general_guardrails(patient, visible, diagnoses)


def test_young_cac_positive_patient_is_level4_with_plaque_present() -> None:
    patient = Patient(
        age=42,
        sex="male",
        cac=18,
        ldl_c=112,
        apob=90,
        prevent_10y_ascvd=0.9,
        prevent_30y_ascvd=5.5,
    )

    _, classification, panel, roadmap, _, diagnoses, visible = _case(patient)

    assert classification.level == "4"
    assert "Present (CAC 18)" in _domain_text(panel, "plaque_cac")
    assert "Coronary plaque: Present (CAC 18)." in roadmap
    assert "mild noise" not in visible.lower()
    assert "Not indicated" in _domain_text(panel, "aspirin_antiplatelet")
    _assert_general_guardrails(patient, visible, diagnoses)


def test_high_cac_percentile_with_modest_absolute_cac_keeps_percentile_context() -> None:
    patient = Patient(
        age=45,
        sex="female",
        cac=38,
        cac_percentile=92,
        ldl_c=126,
        apob=102,
        prevent_10y_ascvd=1.6,
        prevent_30y_ascvd=7.5,
    )

    _, classification, panel, roadmap, where_html, diagnoses, visible = _case(patient)

    assert classification.level == "4"
    assert "Present (CAC 38)" in _domain_text(panel, "plaque_cac")
    assert "Coronary plaque: Present (CAC 38)." in roadmap
    assert "92th percentile" in where_html
    assert "Discuss" in _domain_text(panel, "lipid_lowering")
    _assert_general_guardrails(patient, visible, diagnoses)


def test_ldl_160_to_189_with_clean_vitals_low_prevent_is_not_minimal() -> None:
    patient = Patient(
        age=46,
        sex="male",
        ldl_c=172,
        hdl_c=60,
        triglycerides=80,
        a1c=5.2,
        bmi=23,
        sbp=112,
        dbp=72,
        cac=None,
        cac_not_done=True,
        prevent_10y_ascvd=1.1,
        prevent_30y_ascvd=7.0,
    )

    _, classification, panel, roadmap, _, diagnoses, visible = _case(patient)

    assert classification.level in {"3A", "3B"}
    assert "Discuss" in _domain_text(panel, "lipid_lowering")
    assert "CAC may clarify" in _domain_text(panel, "plaque_cac")
    assert "Calcium scan may clarify treatment." in roadmap
    _assert_general_guardrails(patient, visible, diagnoses)


def test_apob_non_hdl_discordance_is_not_treated_as_ldl_all_clear() -> None:
    patient = Patient(
        age=48,
        sex="male",
        ldl_c=95,
        triglycerides=260,
        hdl_c=34,
        non_hdl_c=147,
        apob=122,
        a1c=5.8,
        cac=None,
        cac_not_done=True,
        prevent_10y_ascvd=1.8,
        prevent_30y_ascvd=8.0,
    )

    _, _, panel, _, _, diagnoses, visible = _case(patient)

    assert "ApoB" in visible and "122" in visible
    assert "Hypertriglyceridemia" in diagnoses
    assert "Discuss" in _domain_text(panel, "lipid_lowering")
    assert "all clear" not in visible.lower()
    _assert_general_guardrails(patient, visible, diagnoses)


def test_albuminuria_with_normal_egfr_remains_visible() -> None:
    patient = Patient(
        age=50,
        sex="female",
        egfr=96,
        uacr=125,
        a1c=5.8,
        diabetes=False,
        bp_treated=True,
        sbp=128,
        dbp=78,
        prevent_10y_ascvd=2.0,
    )

    result, _, panel, roadmap, _, diagnoses, visible = _case(patient)

    assert result.kdigo_stage == "G1A2"
    assert result.ckm_stage["stage"] == 3
    assert "UACR 125" in _domain_text(panel, "kidney_protection")
    assert "Albuminuria present (UACR 125)." in roadmap
    assert "Kidneys: Stable." not in roadmap
    _assert_general_guardrails(patient, visible, diagnoses)


def test_severe_albuminuria_with_normal_egfr_and_diabetes_is_not_undercalled() -> None:
    patient = Patient(
        age=38,
        sex="female",
        egfr=105,
        uacr=420,
        a1c=9.2,
        diabetes=True,
        prevent_10y_ascvd=1.5,
    )

    result, _, panel, roadmap, _, diagnoses, visible = _case(patient)

    assert result.kdigo_stage == "G1A3"
    assert result.ckm_stage["stage"] == 3
    assert "Type 2 diabetes" in diagnoses
    assert "albuminuria" in diagnoses.lower() or "kidney involvement" in diagnoses.lower()
    assert "UACR 420" in _domain_text(panel, "kidney_protection")
    assert "Significant albuminuria is present (UACR 420)." in roadmap
    assert "Kidneys: Stable." not in roadmap
    _assert_general_guardrails(patient, visible, diagnoses)


def test_chronic_inflammatory_disease_with_borderline_lipids_keeps_context() -> None:
    patient = Patient(
        age=50,
        sex="female",
        rheumatoid_arthritis=True,
        ldl_c=142,
        apob=108,
        hscrp=3.4,
        cac=None,
        cac_not_done=True,
        prevent_10y_ascvd=2.5,
        prevent_30y_ascvd=8.0,
    )

    _, classification, panel, roadmap, _, diagnoses, visible = _case(patient)

    assert "rheumatoid arthritis" in visible.lower() or "RA" in visible
    assert "hsCRP" in visible
    assert "Not measured" in _domain_text(panel, "plaque_cac")
    assert "Coronary plaque: Not measured." in roadmap
    if classification.level == "3B":
        assert "No lipid escalation" not in _domain_text(panel, "lipid_lowering")
    _assert_general_guardrails(patient, visible, diagnoses)


def test_south_asian_metabolic_pattern_at_non_obese_bmi_is_not_minimal() -> None:
    patient = Patient(
        age=44,
        sex="male",
        bmi=25,
        triglycerides=220,
        hdl_c=32,
        a1c=6.1,
        apob=112,
        south_asian_ancestry=True,
        cac=None,
        cac_not_done=True,
        prevent_10y_ascvd=1.0,
        prevent_30y_ascvd=7.0,
    )

    _, classification, panel, roadmap, _, diagnoses, visible = _case(patient)

    assert classification.level not in {"1", "2A"}
    assert "South Asian ancestry" in visible
    assert "A1c 6.1" in _domain_text(panel, "glycemia_metabolic")
    assert "Blood sugar" in roadmap
    _assert_general_guardrails(patient, visible, diagnoses)


def test_controlled_diabetes_with_albuminuria_keeps_kidney_risk_output() -> None:
    patient = Patient(
        age=58,
        sex="female",
        a1c=6.5,
        diabetes=True,
        egfr=82,
        uacr=180,
        ldl_c=80,
        apob=78,
        medications_raw="metformin",
        prevent_10y_ascvd=2.0,
    )

    result, _, panel, roadmap, _, diagnoses, visible = _case(patient)

    assert result.kdigo_stage == "G2A2"
    assert "Type 2 diabetes" in diagnoses
    assert "albuminuria" in diagnoses.lower() or "kidney involvement" in diagnoses.lower()
    assert "UACR 180" in _domain_text(panel, "kidney_protection")
    assert "Albuminuria present (UACR 180)." in roadmap
    assert "Kidneys: Stable." not in roadmap
    _assert_general_guardrails(patient, visible, diagnoses)


def test_breast_arterial_calcification_is_context_not_clinical_ascvd() -> None:
    patient = Patient(
        age=56,
        sex="female",
        breast_arterial_calcification="present",
        ldl_c=132,
        apob=104,
        cac=None,
        cac_not_done=True,
        prevent_10y_ascvd=3.2,
        prevent_30y_ascvd=12.0,
    )

    _, _, panel, roadmap, _, diagnoses, visible = _case(patient)

    assert "BAC" in visible or "breast arterial calcification" in visible.lower()
    assert "breast arterial calcification" not in diagnoses.lower()
    assert "CAC may clarify" in _domain_text(panel, "plaque_cac")
    assert "Calcium scan may clarify treatment." in roadmap
    _assert_general_guardrails(patient, visible, diagnoses)
