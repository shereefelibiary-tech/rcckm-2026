BAC_ALLOWED_VALUES = ("unknown", "absent", "present", "mild", "moderate", "severe")
BAC_PRESENT_VALUES = {"present", "mild", "moderate", "severe"}

BAC_HELP_TEXT = (
    "Breast arterial calcification is vascular calcification seen on mammogram. "
    "It may be associated with cardiovascular risk, but it is not the same as a coronary calcium score."
)

BAC_PATIENT_CONTEXT_TEXT = (
    "Calcification was noted in breast arteries on mammogram. This is not the same as a coronary calcium score, "
    "but it can be a clue to vascular risk and may support a closer prevention review."
)

BAC_CLINICIAN_CONTEXT_TEXT = (
    "Breast arterial calcification noted on mammography; non-coronary vascular calcification marker."
)

BAC_CAC_CLARIFICATION_TEXT = (
    "Breast arterial calcification is a non-coronary vascular calcification marker. "
    "CAC may clarify coronary plaque burden."
)


def normalize_breast_arterial_calcification(value):
    """Return a canonical breast arterial calcification value from UI, parser, or boolean input."""
    if value is None or value == "":
        return "unknown"
    if isinstance(value, bool):
        return "present" if value else "absent"

    raw = str(value).strip().lower().replace("_", " ")
    if raw in {"yes", "true", "reported", "noted", "positive"}:
        return "present"
    if raw in {"no", "false", "none", "negative", "not present"}:
        return "absent"
    if raw in {"unknown", "unsure", "not known"}:
        return "unknown"
    if raw in BAC_ALLOWED_VALUES:
        return raw
    return "unknown"


def has_breast_arterial_calcification(patient) -> bool:
    """Return whether BAC is present as a contextual non-coronary vascular imaging marker."""
    value = normalize_breast_arterial_calcification(
        getattr(patient, "breast_arterial_calcification", None)
    )
    return value in BAC_PRESENT_VALUES


def breast_arterial_calcification_display(value) -> str:
    """Format BAC for compact UI and clinician-facing context."""
    normalized = normalize_breast_arterial_calcification(value)
    if normalized in {"unknown", "absent"}:
        return normalized
    if normalized == "present":
        return "present"
    return f"{normalized}"


def breast_arterial_calcification_context(patient) -> str | None:
    """Build clinician-facing BAC context without treating it as coronary plaque."""
    if not has_breast_arterial_calcification(patient):
        return None
    value = normalize_breast_arterial_calcification(
        getattr(patient, "breast_arterial_calcification", None)
    )
    severity = "" if value == "present" else f" ({value})"
    return f"Breast arterial calcification on mammogram{severity}; non-coronary vascular calcification marker"
