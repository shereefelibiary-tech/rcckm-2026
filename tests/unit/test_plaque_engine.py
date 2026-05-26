from core.patient import Patient
from core.enums import PlaqueCategory
from modules.plaque.engine import build_plaque_result
from modules.plaque.engine import format_cac_percentile_context, normalize_cac_percentile


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


def test_normalize_cac_percentile_accepts_only_valid_bounds():
    assert normalize_cac_percentile(0) == 0
    assert normalize_cac_percentile(75.5) == 75.5
    assert normalize_cac_percentile(100) == 100
    assert normalize_cac_percentile(-1) is None
    assert normalize_cac_percentile(101) is None
    assert normalize_cac_percentile("not numeric") is None


def test_format_cac_percentile_context_respects_absolute_cac_hierarchy():
    assert format_cac_percentile_context(0, 95) is None
    assert format_cac_percentile_context(None, 95) is None
    assert format_cac_percentile_context(38, None) is None
    assert format_cac_percentile_context(38, 82) == "Higher than expected for age and sex."
    assert format_cac_percentile_context(38, 52) == "Within the expected range for age and sex."
    assert format_cac_percentile_context(145, 82) == "Higher than expected for age and sex."
    assert format_cac_percentile_context(145, 52) is None
    assert format_cac_percentile_context(350, 95) is None


def test_format_cac_percentile_context_can_include_clinician_detail():
    assert (
        format_cac_percentile_context(38, 82, include_clinician_detail=True)
        == "Higher than expected for age and sex. Clinician detail: 82th percentile."
    )
    assert (
        format_cac_percentile_context(145, 52, include_clinician_detail=True)
        == "Clinician detail: 52th percentile."
    )
