from __future__ import annotations


def albuminuria_category(uacr: float | int | None) -> str | None:
    if uacr is None:
        return None
    if uacr < 30:
        return "A1"
    if uacr < 300:
        return "A2"
    return "A3"


def diabetes_range(a1c: float | int | None) -> bool:
    return bool(a1c is not None and a1c >= 6.5)


def prediabetes_range(a1c: float | int | None) -> bool:
    return bool(a1c is not None and 5.7 <= a1c < 6.5)


def structural_plaque_detected(cac: float | int | None) -> bool | None:
    if cac is None:
        return None
    return bool(cac > 0)


def aspirin_primary_prevention_indicated(
    *, cac: float | int | None, known_ascvd: bool
) -> bool:
    if known_ascvd:
        return True
    if cac == 0:
        return False
    return False


def lipid_therapy_reasonable(
    *,
    ldl_c: float | int | None,
    apob: float | int | None,
    uacr: float | int | None,
    family_history_premature_ascvd: bool,
    known_ascvd: bool,
) -> bool:
    return bool(
        known_ascvd
        or family_history_premature_ascvd
        or (ldl_c is not None and ldl_c >= 130)
        or (apob is not None and apob >= 100)
        or (uacr is not None and uacr >= 30)
    )


def derived_expectations(parsed: dict) -> dict:
    a1c = parsed.get("a1c")
    cac = parsed.get("cac")
    known_ascvd = bool(parsed.get("clinical_ascvd"))
    uacr = parsed.get("uacr")
    return {
        "albuminuria_category": albuminuria_category(uacr),
        "diabetes_range": diabetes_range(a1c),
        "prediabetes_range": prediabetes_range(a1c),
        "structural_plaque_detected": structural_plaque_detected(cac),
        "aspirin_primary_prevention_indicated": aspirin_primary_prevention_indicated(
            cac=cac,
            known_ascvd=known_ascvd,
        ),
        "lipid_therapy_reasonable": lipid_therapy_reasonable(
            ldl_c=parsed.get("ldl_c"),
            apob=parsed.get("apob"),
            uacr=uacr,
            family_history_premature_ascvd=bool(
                parsed.get("family_history_premature_ascvd")
                or parsed.get("premature_fhx_ascvd")
            ),
            known_ascvd=known_ascvd,
        ),
    }
