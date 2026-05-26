INCIDENTAL_CAC_SEVERITY_OPTIONS = ("present", "mild", "moderate", "severe")


def normalize_incidental_cac_severity(value, *, default="present"):
    """Return a canonical qualitative incidental CAC severity."""
    if value is None or value == "":
        return default
    raw = str(value).strip().lower().replace("_", " ")
    if raw in {"unknown", "unspecified", "not specified"}:
        return "present"
    if raw in INCIDENTAL_CAC_LEGACY_EMPTY_VALUES:
        return default
    if raw in INCIDENTAL_CAC_SEVERITY_ALIASES:
        return INCIDENTAL_CAC_SEVERITY_ALIASES[raw]
    if raw in INCIDENTAL_CAC_SEVERITY_VALUES:
        return raw
    return default


INCIDENTAL_CAC_LEGACY_EMPTY_VALUES = {"none", "no", "false", "absent"}
INCIDENTAL_CAC_SEVERITY_VALUES = set(INCIDENTAL_CAC_SEVERITY_OPTIONS)
INCIDENTAL_CAC_SEVERITY_ALIASES = {
    "yes": "present",
    "true": "present",
    "noted": "present",
    "reported": "present",
}


def has_incidental_cac(patient) -> bool:
    """Return whether qualitative incidental coronary calcification is present."""
    return bool(getattr(patient, "incidental_cac", False))


def incidental_cac_severity(patient) -> str | None:
    """Return severity only when incidental CAC itself is present."""
    if not has_incidental_cac(patient):
        return None
    return normalize_incidental_cac_severity(
        getattr(patient, "incidental_cac_severity", None)
    )


def incidental_cac_context(patient) -> str | None:
    """Format incidental CAC without assigning an Agatston CAC score."""
    severity = incidental_cac_severity(patient)
    if severity is None:
        return None
    if severity == "present":
        return "Incidental coronary artery calcification noted on CT; severity not specified"
    return f"{severity.title()} incidental coronary artery calcification noted on CT"
