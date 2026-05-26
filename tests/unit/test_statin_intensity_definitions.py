from core.patient import Patient
from core.results import RCCKMResult
from modules.lipids.statin_intensity import (
    get_statin_intensity_definition,
    statin_intensity_help_text,
)
from renderers.emr_renderer import render_emr_note
from renderers.patient_roadmap import render_patient_roadmap_text


def test_moderate_intensity_definition_is_standardized():
    definition = get_statin_intensity_definition("moderate")

    assert definition.expected_ldl_reduction == "30% to 49%"
    assert "Atorvastatin 10-20 mg daily" in definition.examples
    assert "Rosuvastatin 5-10 mg daily" in definition.examples
    assert "one-third to one-half" in definition.patient_friendly_summary
    assert "expected LDL-C reduction 30% to 49%" in definition.clinician_summary


def test_low_intensity_definition_is_standardized():
    definition = get_statin_intensity_definition("low")

    assert definition.expected_ldl_reduction == "<30%"
    assert "Pravastatin 10-20 mg daily" in definition.examples
    assert "Simvastatin 10 mg daily" in definition.examples
    assert "less than one-third" in definition.patient_friendly_summary
    assert "expected LDL-C reduction <30%" in definition.clinician_summary


def test_high_intensity_definition_is_standardized():
    definition = get_statin_intensity_definition("high")

    assert definition.expected_ldl_reduction == ">=50%"
    assert "Atorvastatin 40-80 mg daily" in definition.examples
    assert "Rosuvastatin 20-40 mg daily" in definition.examples
    assert "at least one-half" in definition.patient_friendly_summary
    assert "expected LDL-C reduction >=50%" in definition.clinician_summary


def test_statin_intensity_help_text_uses_single_source_definitions():
    help_text = statin_intensity_help_text()

    assert "Statin intensity is based on expected LDL-C reduction" in help_text
    assert "Low intensity: LDL-C reduction <30%" in help_text
    assert "Moderate intensity: LDL-C reduction 30% to 49%" in help_text
    assert "High intensity: LDL-C reduction >=50%" in help_text
    assert "Low: Pravastatin 10-20 mg, Simvastatin 10 mg" in help_text
    assert "Moderate: atorvastatin 10-20 mg, rosuvastatin 5-10 mg, pravastatin 40-80 mg" in help_text
    assert "High: atorvastatin 40-80 mg, rosuvastatin 20-40 mg" in help_text


def test_emr_does_not_dump_statin_example_lists_by_default():
    patient = Patient(age=55, sex="male")
    result = RCCKMResult(
        recommendations=[
            "Moderate-intensity statin therapy is generally favored based on 10-year ASCVD risk."
        ]
    )

    note = render_emr_note(patient, result)

    assert "atorvastatin 10-20" not in note.lower()
    assert "rosuvastatin 5-10" not in note.lower()
    assert "pravastatin 40-80" not in note.lower()
    assert "simvastatin 20-40" not in note.lower()


def test_patient_roadmap_uses_plain_language_statin_definition():
    patient = Patient(age=55, sex="male")
    result = RCCKMResult(
        recommendations=[
            "Moderate-intensity statin therapy is generally favored based on 10-year ASCVD risk."
        ]
    )

    roadmap = render_patient_roadmap_text(patient, result)

    assert "usually lowers LDL cholesterol by about one-third to one-half" in roadmap
    assert "Atorvastatin 10-20 mg daily" not in roadmap
    assert "Rosuvastatin 5-10 mg daily" not in roadmap
