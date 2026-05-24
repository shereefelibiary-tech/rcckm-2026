from core.engine import evaluate_patient
from core.enums import RiskLevel
from core.patient import Patient
from modules.actions.scaffold import build_action_scaffold


def _section(sections, label):
    for section in sections:
        if section.label == label:
            return section
    raise AssertionError(f"Missing action section: {label}")


def test_low_10y_elevated_30y_ldl_pathway_and_nonpremature_family_history():
    patient = Patient(
        age=39,
        sex="male",
        ldl_c=162,
        apob=124,
        prevent_10y_ascvd=1.57,
        prevent_30y_ascvd=10.87,
        cac=None,
        cac_not_done=True,
        family_history_relationship="father",
        family_history_event_type="MI",
        family_history_age_at_event=61,
    )

    result = evaluate_patient(patient)
    sections = build_action_scaffold(patient, result)
    diagnosis_names = [candidate.name for candidate in result.diagnosis_candidates]

    assert result.prevent_risk_category == RiskLevel.LOW
    assert result.prevent_30y_ascvd == 10.87
    assert patient.family_history_summary == "Father MI age 61"
    assert patient.premature_fhx_ascvd is False
    assert "Premature family history of ASCVD" not in diagnosis_names
    assert result.recommendations[0] == (
        "Moderate-intensity statin therapy is reasonable to reduce cumulative atherogenic exposure."
    )
    assert _section(sections, "Lipid therapy").line == (
        "Moderate-intensity statin therapy is reasonable to reduce cumulative atherogenic exposure."
    )
    assert _section(sections, "Coronary calcium").line == (
        "CAC not performed; below usual age threshold, use only if it would change management."
    )
