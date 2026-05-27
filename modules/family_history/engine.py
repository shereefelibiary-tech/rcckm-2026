MALE_RELATIVES = {"father", "brother"}
FEMALE_RELATIVES = {"mother", "sister"}

PREMATURE_FAMILY_HISTORY_HELP = (
    "Premature ASCVD includes MI, stroke, PCI, CABG, or PAD before "
    "age 55 in men or before age 65 in women."
)

COMPACT_FAMILY_HISTORY_OPTIONS = {
    "none_unknown": "None / Unknown",
    "father_premature_ascvd": "Father <55",
    "mother_premature_ascvd": "Mother <65",
    "sibling_premature_ascvd": "Sibling",
    "multiple_first_degree": "Multiple first-degree relatives",
    "other_premature_relative": "Other premature relative",
}

_OPTION_PAYLOADS = {
    "none_unknown": {
        "family_history_premature_ascvd": False,
        "family_history_relationship": None,
        "family_history_event_type": None,
        "family_history_age_at_event": None,
    },
    "father_premature_ascvd": {
        "family_history_premature_ascvd": True,
        "family_history_relationship": "father",
        "family_history_event_type": "ASCVD",
        "family_history_age_at_event": None,
    },
    "mother_premature_ascvd": {
        "family_history_premature_ascvd": True,
        "family_history_relationship": "mother",
        "family_history_event_type": "ASCVD",
        "family_history_age_at_event": None,
    },
    "sibling_premature_ascvd": {
        "family_history_premature_ascvd": True,
        "family_history_relationship": "sibling",
        "family_history_event_type": "ASCVD",
        "family_history_age_at_event": None,
    },
    "multiple_first_degree": {
        "family_history_premature_ascvd": True,
        "family_history_relationship": "multiple first-degree relatives",
        "family_history_event_type": "ASCVD",
        "family_history_age_at_event": None,
    },
    "other_premature_relative": {
        "family_history_premature_ascvd": True,
        "family_history_relationship": "other premature relative",
        "family_history_event_type": "ASCVD",
        "family_history_age_at_event": None,
    },
}


def compact_family_history_option_values():
    """Return canonical compact family-history option values."""
    return tuple(COMPACT_FAMILY_HISTORY_OPTIONS.keys())


def compact_family_history_label(option):
    """Return the short display label for a compact family-history option."""
    return COMPACT_FAMILY_HISTORY_OPTIONS.get(str(option or ""), "None / Unknown")


def compact_family_history_payload(option):
    """Map a compact family-history option to worksheet field values."""
    return dict(_OPTION_PAYLOADS.get(str(option or ""), _OPTION_PAYLOADS["none_unknown"]))


def infer_compact_family_history_option(premature=False, relationship=None, age_at_event=None):
    """Infer the compact UI option from structured family-history values."""
    relationship_value = str(relationship or "").strip().lower()
    age_value = None
    try:
        age_value = float(age_at_event) if age_at_event is not None else None
    except (TypeError, ValueError):
        age_value = None

    if relationship_value == "father" and (age_value is None or age_value < 55):
        return "father_premature_ascvd" if premature or age_value is not None else "none_unknown"
    if relationship_value == "mother" and (age_value is None or age_value < 65):
        return "mother_premature_ascvd" if premature or age_value is not None else "none_unknown"
    if relationship_value in {"brother", "sister", "sibling"} and (
        premature or is_premature_ascvd_family_history(relationship_value, age_value)
    ):
        return "sibling_premature_ascvd"
    if relationship_value == "multiple first-degree relatives" and premature:
        return "multiple_first_degree"
    if relationship_value == "other premature relative" and premature:
        return "other_premature_relative"
    return "other_premature_relative" if premature else "none_unknown"


def normalize_family_history_event(event_type):
    event = str(event_type or "").strip()
    event_map = {
        "mi": "MI",
        "pci/cabg": "PCI/CABG",
        "pci": "PCI/CABG",
        "cabg": "PCI/CABG",
        "stroke": "stroke",
        "ascvd": "ASCVD",
        "pad": "PAD",
        "sudden cardiac death": "sudden cardiac death",
        "scd": "sudden cardiac death",
    }
    return event_map.get(event.lower(), event)


def is_premature_ascvd_family_history(relationship, age_at_event):
    if relationship is None or age_at_event is None:
        return False

    relationship_value = str(relationship).strip().lower()
    try:
        age_value = float(age_at_event)
    except (TypeError, ValueError):
        return False

    if relationship_value in MALE_RELATIVES:
        return age_value < 55

    if relationship_value in FEMALE_RELATIVES:
        return age_value < 65

    return False


def _summary_without_exact_age(relationship):
    relationship_value = str(relationship or "").strip().lower()
    if relationship_value == "father":
        return "Father with premature ASCVD before age 55"
    if relationship_value == "mother":
        return "Mother with premature ASCVD before age 65"
    if relationship_value in {"brother", "sister", "sibling"}:
        return "Sibling with premature ASCVD"
    if relationship_value == "multiple first-degree relatives":
        return "Multiple first-degree relatives with premature ASCVD"
    if relationship_value == "other premature relative":
        return "Other premature relative with premature ASCVD"
    return "Premature family history of ASCVD"


def build_family_history_summary(relationship, event_type, age_at_event):
    if not relationship or not event_type or age_at_event is None:
        return None

    relationship_label = str(relationship).strip().title()
    event_label = normalize_family_history_event(event_type)

    try:
        age_label = f"{float(age_at_event):g}"
    except (TypeError, ValueError):
        return None

    return f"{relationship_label} {event_label} age {age_label}"


def build_family_history_payload(patient):
    relationship = getattr(patient, "family_history_relationship", None)
    event_type = getattr(patient, "family_history_event_type", None)
    age_at_event = getattr(patient, "family_history_age_at_event", None)
    summary = build_family_history_summary(
        relationship,
        event_type,
        age_at_event,
    )
    premature = is_premature_ascvd_family_history(relationship, age_at_event)
    legacy_flag = bool(getattr(patient, "family_history_premature_ascvd", False))
    if relationship and age_at_event is not None:
        legacy_flag = False
    if summary is None and legacy_flag:
        summary = _summary_without_exact_age(relationship)

    return {
        "relationship": relationship,
        "event_type": normalize_family_history_event(event_type),
        "age_at_event": age_at_event,
        "summary": summary,
        "premature_fhx_ascvd": premature or legacy_flag,
    }
