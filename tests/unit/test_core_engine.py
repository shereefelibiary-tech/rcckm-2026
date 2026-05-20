from core.patient import Patient
from core.enums import DecisionStability, PlaqueCategory
from core.engine import evaluate_patient


def test_evaluate_patient_returns_combined_results():
    patient = Patient(
        age=60,
        sex="male",
        cac=350,
        apob=110,
        lp_a_value=80,
        uacr=45,
        egfr=55,
        diabetes=True,
        clinical_ascvd=False,
    )

    result = evaluate_patient(patient)

    assert result.plaque_category == PlaqueCategory.SEVERE
    assert result.decision_stability == DecisionStability.HIGH
    assert len(result.targets) == 1
    assert any(c.name == "Chronic kidney disease" for c in result.diagnosis_candidates)
    assert any(c.name == "Albuminuria" for c in result.diagnosis_candidates)
    assert any(c.name == "Diabetes mellitus" for c in result.diagnosis_candidates)
