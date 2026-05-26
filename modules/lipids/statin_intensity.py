from dataclasses import dataclass


@dataclass(frozen=True)
class StatinIntensityDefinition:
    label: str
    expected_ldl_reduction: str
    examples: tuple[str, ...]
    patient_friendly_summary: str
    clinician_summary: str
    tooltip_text: str


_DEFINITIONS = {
    "low": StatinIntensityDefinition(
        label="Low-intensity statin therapy",
        expected_ldl_reduction="<30%",
        examples=(
            "Pravastatin 10-20 mg daily",
            "Simvastatin 10 mg daily",
        ),
        patient_friendly_summary=(
            "Low-intensity statin therapy usually lowers LDL cholesterol by less than one-third."
        ),
        clinician_summary=(
            "Low-intensity statin therapy: expected LDL-C reduction <30%; "
            "examples include pravastatin 10-20 mg or simvastatin 10 mg daily."
        ),
        tooltip_text=(
            "Low-intensity statin therapy usually lowers LDL-C by <30%. "
            "Examples: pravastatin 10-20 mg daily or simvastatin 10 mg daily."
        ),
    ),
    "moderate": StatinIntensityDefinition(
        label="Moderate-intensity statin therapy",
        expected_ldl_reduction="30% to 49%",
        examples=(
            "Atorvastatin 10-20 mg daily",
            "Rosuvastatin 5-10 mg daily",
            "Pravastatin 40-80 mg daily",
            "Simvastatin 20-40 mg daily",
        ),
        patient_friendly_summary=(
            "Moderate-intensity statin therapy usually lowers LDL cholesterol "
            "by about one-third to one-half."
        ),
        clinician_summary=(
            "Moderate-intensity statin therapy: expected LDL-C reduction 30% to 49%; "
            "examples include atorvastatin 10-20 mg or rosuvastatin 5-10 mg daily."
        ),
        tooltip_text=(
            "Moderate-intensity statin therapy usually lowers LDL-C by 30-49%. "
            "Examples: atorvastatin 10-20 mg daily, rosuvastatin 5-10 mg daily, "
            "pravastatin 40-80 mg daily, or simvastatin 20-40 mg daily."
        ),
    ),
    "high": StatinIntensityDefinition(
        label="High-intensity statin therapy",
        expected_ldl_reduction=">=50%",
        examples=(
            "Atorvastatin 40-80 mg daily",
            "Rosuvastatin 20-40 mg daily",
        ),
        patient_friendly_summary=(
            "High-intensity statin therapy usually lowers LDL cholesterol by at least one-half."
        ),
        clinician_summary=(
            "High-intensity statin therapy: expected LDL-C reduction >=50%; "
            "examples include atorvastatin 40-80 mg or rosuvastatin 20-40 mg daily."
        ),
        tooltip_text=(
            "High-intensity statin therapy usually lowers LDL-C by ≥50%. "
            "Examples: atorvastatin 40-80 mg daily or rosuvastatin 20-40 mg daily."
        ),
    ),
}


def get_statin_intensity_definition(intensity: str) -> StatinIntensityDefinition:
    """Return the standardized RCCKM statin intensity definition."""
    key = str(intensity or "").strip().lower()
    if key not in _DEFINITIONS:
        raise ValueError(f"Unsupported statin intensity: {intensity!r}")
    return _DEFINITIONS[key]


def statin_intensity_help_text() -> str:
    """Return compact UI help text for the statin intensity selector."""
    low = get_statin_intensity_definition("low")
    moderate = get_statin_intensity_definition("moderate")
    high = get_statin_intensity_definition("high")
    return (
        "Statin intensity is based on expected LDL-C reduction:\n"
        f"- Low intensity: LDL-C reduction {low.expected_ldl_reduction}\n"
        f"- Moderate intensity: LDL-C reduction {moderate.expected_ldl_reduction}\n"
        f"- High intensity: LDL-C reduction {high.expected_ldl_reduction}\n\n"
        "Examples:\n"
        f"- Low: {', '.join(example.replace(' daily', '') for example in low.examples)}\n"
        "- Moderate: atorvastatin 10-20 mg, rosuvastatin 5-10 mg, pravastatin 40-80 mg\n"
        "- High: atorvastatin 40-80 mg, rosuvastatin 20-40 mg"
    )
