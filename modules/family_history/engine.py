MALE_RELATIVES = {"father", "brother"}
FEMALE_RELATIVES = {"mother", "sister"}


def normalize_family_history_event(event_type):
    event = str(event_type or "").strip()
    event_map = {
        "mi": "MI",
        "pci/cabg": "PCI/CABG",
        "pci": "PCI/CABG",
        "cabg": "PCI/CABG",
        "stroke": "stroke",
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

    return {
        "relationship": relationship,
        "event_type": normalize_family_history_event(event_type),
        "age_at_event": age_at_event,
        "summary": summary,
        "premature_fhx_ascvd": premature or legacy_flag,
    }
