from __future__ import annotations

from typing import Any


REPRODUCTIVE_MARKERS = (
    ("premature_menopause", "Premature menopause", "Premature menopause"),
    ("early_menopause", "Early menopause", "Early menopause"),
    ("preeclampsia", "Preeclampsia", "History of preeclampsia"),
    ("gestational_hypertension", "Gestational hypertension", "Gestational hypertension"),
    ("gestational_diabetes", "Gestational diabetes", "Gestational diabetes"),
    ("preterm_delivery", "Preterm delivery", "Preterm delivery <37 weeks"),
    ("small_for_gestational_age", "SGA infant", "Small-for-gestational-age infant"),
    ("recurrent_pregnancy_loss", "Recurrent pregnancy loss", "Recurrent pregnancy loss"),
    ("pcos_or_irregular_menses", "PCOS / irregular menses", "PCOS / irregular menses"),
    ("early_menarche", "Early menarche", "Early menarche"),
)


def _fmt_age(value: Any) -> str | None:
    try:
        if value is None:
            return None
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return None


def _is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"yes", "true", "present", "positive", "1"}
    return False


def reproductive_marker_items(patient: Any) -> list[dict[str, str]]:
    """Return present reproductive risk markers with compact display labels."""
    items: list[dict[str, str]] = []
    raw_menopause_age = getattr(patient, "menopause_age", None)
    raw_menarche_age = getattr(patient, "menarche_age", None)
    menopause_age = _fmt_age(raw_menopause_age)
    menarche_age = _fmt_age(raw_menarche_age)
    menopause_number = None
    menarche_number = None
    try:
        menopause_number = float(raw_menopause_age) if raw_menopause_age is not None else None
    except (TypeError, ValueError):
        menopause_number = None
    try:
        menarche_number = float(raw_menarche_age) if raw_menarche_age is not None else None
    except (TypeError, ValueError):
        menarche_number = None

    premature_menopause = _is_true(getattr(patient, "premature_menopause", False)) or (
        menopause_number is not None and menopause_number < 40
    )
    early_menopause = _is_true(getattr(patient, "early_menopause", False)) or (
        menopause_number is not None and menopause_number < 45
    )
    early_menarche = _is_true(getattr(patient, "early_menarche", False)) or (
        menarche_number is not None and menarche_number < 10
    )

    if premature_menopause:
        detail = f"age {menopause_age}" if menopause_age else "<40 years"
        items.append(
            {
                "field": "premature_menopause",
                "label": "Premature menopause",
                "detail": detail,
                "patient_label": f"Premature menopause {detail}",
            }
        )
    elif early_menopause:
        detail = f"age {menopause_age}" if menopause_age else "<45 years"
        items.append(
            {
                "field": "early_menopause",
                "label": "Early menopause",
                "detail": detail,
                "patient_label": f"Early menopause {detail}",
            }
        )

    for field, label, patient_label in REPRODUCTIVE_MARKERS[2:9]:
        if _is_true(getattr(patient, field, False)):
            items.append(
                {
                    "field": field,
                    "label": label,
                    "detail": patient_label,
                    "patient_label": patient_label,
                }
            )

    if early_menarche:
        detail = f"age {menarche_age}" if menarche_age else "<10 years"
        items.append(
            {
                "field": "early_menarche",
                "label": "Early menarche",
                "detail": detail,
                "patient_label": f"Early menarche {detail}",
            }
        )

    return items


def reproductive_history_summary(patient: Any, *, patient_facing: bool = False) -> str | None:
    items = reproductive_marker_items(patient)
    if not items:
        return None
    key = "patient_label" if patient_facing else "label"
    parts = []
    for item in items:
        if item["field"] in {"early_menopause", "premature_menopause", "early_menarche"}:
            parts.append(item["patient_label"].replace(" age ", " "))
        else:
            parts.append(item[key])
    return "; ".join(parts)


def has_reproductive_risk_markers(patient: Any) -> bool:
    return bool(reproductive_marker_items(patient))


def is_reproductive_history_applicable(patient: Any) -> bool:
    sex = str(getattr(patient, "sex", "") or "").strip().lower()
    return sex in {"female", "f", "woman", "unknown", ""}
