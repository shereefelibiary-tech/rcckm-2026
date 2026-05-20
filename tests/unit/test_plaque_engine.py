from core.patient import Patient
from core.enums import PlaqueCategory
from modules.plaque.engine import build_plaque_result


def test_build_plaque_result_sets_plaque_category():
    # CAC 0 -> NONE
    patient = Patient(age=55, sex="male", cac=0)
    result = build_plaque_result(patient)
    assert result.plaque_category == PlaqueCategory.NONE


def test_build_plaque_result_cac_50_is_mild():
    patient = Patient(age=55, sex="male", cac=50)
    result = build_plaque_result(patient)
    assert result.plaque_category == PlaqueCategory.MILD


def test_build_plaque_result_cac_150_is_moderate():
    patient = Patient(age=55, sex="male", cac=150)
    result = build_plaque_result(patient)
    assert result.plaque_category == PlaqueCategory.MODERATE


def test_build_plaque_result_cac_350_is_severe():
    patient = Patient(age=55, sex="male", cac=350)
    result = build_plaque_result(patient)
    assert result.plaque_category == PlaqueCategory.SEVERE


def test_build_plaque_result_cac_1200_is_extensive():
    patient = Patient(age=55, sex="male", cac=1200)
    result = build_plaque_result(patient)
    assert result.plaque_category == PlaqueCategory.EXTENSIVE
