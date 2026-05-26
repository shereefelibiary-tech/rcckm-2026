from __future__ import annotations

from typing import Any

from modules.levels.level_classifier import classify_rcckm_level


def _num(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _level_text(level: str) -> str:
    return f"Level {level}"


def _driver_phrase(drivers: list[str]) -> str:
    clean = [str(driver).strip() for driver in drivers if str(driver or "").strip()]
    if not clean:
        return ""
    return ", ".join(clean[:4])


def _secondary_contributors(patient: Any, result: Any) -> list[str]:
    contributors: list[str] = []
    apob = _num(getattr(patient, "apob", None))
    if apob is not None and apob >= 100:
        contributors.append("elevated ApoB")
    if bool(getattr(patient, "diabetes", False)):
        contributors.append("diabetes")
    uacr = _num(getattr(patient, "uacr", None))
    egfr = _num(getattr(patient, "egfr", None))
    if (uacr is not None and uacr >= 30) or (egfr is not None and egfr < 60):
        contributors.append("kidney involvement")
    prevent_30 = _num(getattr(result, "prevent_30y_ascvd", None))
    if prevent_30 is not None and prevent_30 >= 15:
        contributors.append("elevated 30-year risk")
    return contributors


def _missing_clarifiers(patient: Any) -> list[str]:
    missing: list[str] = []
    if getattr(patient, "apob", None) is None:
        missing.append("ApoB")
    if getattr(patient, "lp_a_value", None) is None:
        missing.append("Lp(a)")
    if getattr(patient, "uacr", None) is None:
        missing.append("UACR")
    if getattr(patient, "cac", None) is None and bool(getattr(patient, "cac_not_done", False)):
        missing.append("CAC")
    return missing


def build_level_explanation(patient: Any, result: Any) -> str:
    """Explain why the current RCCKM level was assigned using patient-specific drivers."""
    classification = classify_rcckm_level(patient, result)
    level = _level_text(classification.level)
    drivers = list(getattr(classification, "drivers", None) or [])
    cac = _num(getattr(patient, "cac", None))
    prevent_10 = _num(getattr(result, "prevent_10y_ascvd", None))
    prevent_30 = _num(getattr(result, "prevent_30y_ascvd", None))
    uacr = _num(getattr(patient, "uacr", None))
    apob = _num(getattr(patient, "apob", None))

    if bool(getattr(patient, "clinical_ascvd", False)):
        sentences = [
            f"{level} is assigned because clinical ASCVD places the patient in a secondary-prevention pathway."
        ]
    elif cac is not None and cac >= 300:
        sentences = [
            f"{level} is assigned because coronary calcium shows high plaque burden."
        ]
    elif cac is not None and cac > 0:
        sentences = [
            f"{level} is assigned because CAC {cac:g} shows calcified coronary plaque is present."
        ]
    elif cac == 0:
        sentences = [
            "CAC 0 indicates no calcified coronary plaque detected.",
            f"{level} reflects calculated risk and risk-enhancing factors, not detected plaque.",
        ]
    elif classification.level == "3B" and uacr is not None and uacr >= 30:
        sentences = [
            f"{level} is assigned because CKM stage 3 with albuminuria indicates kidney-mediated cardiometabolic risk.",
            "ASCVD risk and metabolic markers add context.",
        ]
    elif (
        classification.level == "3B"
        and prevent_10 is not None
        and prevent_10 < 5
        and prevent_30 is not None
        and prevent_30 >= 15
    ):
        sentences = [
            f"{level} is assigned because short-term ASCVD risk is low, but longer-term risk is elevated."
        ]
        if any("family history" in driver.lower() for driver in drivers):
            sentences[0] += " Premature family history and metabolic risk signals contribute."
    elif apob is not None and apob >= 100:
        sentences = [
            f"{level} is assigned because ApoB/atherogenic particle burden is contributing to risk."
        ]
    else:
        sentences = [f"{level} is assigned based on the current RCCKM risk signals."]

    driver_text = _driver_phrase(
        [
            driver
            for driver in drivers
            if "CAC " not in driver and driver.lower() not in {"albuminuria"}
        ]
    )
    if driver_text and not any(driver_text in sentence for sentence in sentences):
        sentences.append(f"Additional contributors include {driver_text}.")
    elif not driver_text:
        contributors = _secondary_contributors(patient, result)
        if contributors:
            sentences.append(f"Additional contributors include {', '.join(contributors[:4])}.")

    missing = _missing_clarifiers(patient)
    if missing:
        sentences.append(f"{', '.join(missing)} could further clarify risk if not already available.")

    return " ".join(sentences[:3])
