from core.patient import Patient
from core.enums import PlaqueCategory
from modules.plaque.engine import build_plaque_result


def test_build_plaque_result_sets_plaque_category():
    patient = Patient(age=55, sex="male", cac=250)

    result = build_plaque_result(patient)

    assert result.plaque_category == PlaqueCategory.HIGH
