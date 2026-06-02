from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class OracleOutput:
    prevent_category: str | None
    ckm_stage: int | None
    ckm_reason: str
    egfr_stage: str | None
    albuminuria_category: str | None
    kdigo_stage: str | None
    plaque_status: str
    risk_level: str | None
    lipid_action: str
    ldl_c_target: int | None
    apob_target: int | None
    aspirin_action: str
    aspirin_primary_prevention_indicated: bool
    diabetes_range: bool
    prediabetes_range: bool
    albuminuria_present: bool
    structural_plaque_detected: bool | None
    diagnoses: list[str]
    drivers: list[str]


def _num(patient: dict, *keys: str) -> float | None:
    for key in keys:
        value = patient.get(key)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _bool(patient: dict, *keys: str) -> bool:
    return any(bool(patient.get(key)) for key in keys)


def prevent_category(value: float | int | None) -> str | None:
    if value is None:
        return None
    if value < 5:
        return "Low"
    if value < 7.5:
        return "Borderline"
    if value < 20:
        return "Intermediate"
    return "High"


def egfr_stage(egfr: float | int | None) -> str | None:
    if egfr is None:
        return None
    if egfr >= 90:
        return "G1"
    if egfr >= 60:
        return "G2"
    if egfr >= 45:
        return "G3a"
    if egfr >= 30:
        return "G3b"
    if egfr >= 15:
        return "G4"
    return "G5"


def albuminuria_category(uacr: float | int | None) -> str | None:
    if uacr is None:
        return None
    if uacr < 30:
        return "A1"
    if uacr < 300:
        return "A2"
    return "A3"


def kdigo_stage(egfr: float | int | None, uacr: float | int | None) -> str | None:
    g_stage = egfr_stage(egfr)
    a_stage = albuminuria_category(uacr)
    if not g_stage:
        return None
    if not a_stage:
        return g_stage
    return f"{g_stage}{a_stage}"


def diabetes_range(a1c: float | int | None) -> bool:
    return bool(a1c is not None and a1c >= 6.5)


def prediabetes_range(a1c: float | int | None) -> bool:
    return bool(a1c is not None and 5.7 <= a1c < 6.5)


def plaque_status(cac: float | int | None, clinical_ascvd: bool = False) -> str:
    if clinical_ascvd:
        return "clinical ASCVD"
    if cac is None:
        return "not measured"
    if cac == 0:
        return "not detected"
    if cac < 100:
        return "present"
    if cac < 300:
        return "high burden"
    return "very high burden"


def structural_plaque_detected(cac: float | int | None) -> bool | None:
    if cac is None:
        return None
    return cac > 0


def _has_major_enhancer(patient: dict) -> bool:
    return bool(
        _bool(
            patient,
            "family_history_premature_ascvd",
            "premature_fhx_ascvd",
            "rheumatoid_arthritis",
            "psoriasis",
            "sle",
            "ibd",
            "south_asian_ancestry",
            "filipino_ancestry",
            "preeclampsia",
            "gestational_diabetes",
            "gestational_hypertension",
            "premature_menopause",
            "breast_arterial_calcification",
        )
    )


def ckm_stage(patient: dict) -> tuple[int | None, str]:
    if _bool(patient, "clinical_ascvd"):
        return 4, "Clinical cardiovascular disease present."
    cac = _num(patient, "cac")
    egfr = _num(patient, "egfr")
    uacr = _num(patient, "uacr")
    a1c = _num(patient, "a1c")
    bmi = _num(patient, "bmi")
    ldl_c = _num(patient, "ldl_c", "ldl")
    apob = _num(patient, "apob")

    if (cac is not None and cac > 0) or (egfr is not None and egfr < 60) or (
        uacr is not None and uacr >= 30
    ):
        return 3, "Subclinical cardiovascular disease or CKD is present."
    if _bool(patient, "diabetes") or diabetes_range(a1c):
        return 2, "Metabolic disease is present."
    if any(
        [
            bmi is not None and bmi >= 25,
            prediabetes_range(a1c),
            ldl_c is not None and ldl_c >= 130,
            apob is not None and apob >= 100,
            _bool(patient, "bp_treated", "hypertension"),
        ]
    ):
        return 1, "Risk factors are present."
    return 0, "No major CKM risk factors detected."


def risk_level(patient: dict, ckm: int | None, plaque: str) -> str | None:
    if _bool(patient, "clinical_ascvd"):
        return "5"
    cac = _num(patient, "cac")
    if cac is not None and cac >= 300:
        return "5"
    if cac is not None and cac > 0:
        return "4"
    if ckm == 3:
        return "3B"
    if ckm == 2:
        return "3A"
    if _has_major_enhancer(patient):
        return "3A"
    if ckm == 1:
        return "2"
    if ckm == 0:
        return "1"
    return None


def lipid_action_and_targets(patient: dict, level: str | None) -> tuple[str, int | None, int | None]:
    clinical_ascvd = _bool(patient, "clinical_ascvd")
    ldl_c = _num(patient, "ldl_c", "ldl")
    apob = _num(patient, "apob")
    cac = _num(patient, "cac")
    uacr = _num(patient, "uacr")
    on_lipid = _bool(patient, "lipid_lowering")

    if clinical_ascvd:
        return "secondary-prevention lipid-lowering therapy", 70, 80
    if ldl_c is not None and ldl_c >= 190:
        return "high-intensity lipid-lowering therapy indicated", 70, 80
    if cac is not None and cac >= 100:
        return "lipid-lowering therapy indicated", 70, 80
    if cac is not None and cac > 0:
        return "lipid-lowering therapy indicated", 100, 90
    if (
        level in {"3A", "3B"}
        and (
            (ldl_c is not None and ldl_c >= 130)
            or (apob is not None and apob >= 100)
            or (uacr is not None and uacr >= 30)
            or _has_major_enhancer(patient)
        )
    ):
        if on_lipid:
            return "review lipid-lowering intensity", 100, 90
        return "discuss moderate-intensity statin", 100, 90
    return "no lipid-lowering medication indicated", None, None


def aspirin_action(patient: dict) -> tuple[str, bool]:
    if _bool(patient, "clinical_ascvd"):
        return "secondary-prevention antiplatelet therapy", True
    if _bool(patient, "aspirin_bleeding_risk_high"):
        return "avoid routine primary-prevention aspirin", False
    age = _num(patient, "age")
    cac = _num(patient, "cac")
    if age is not None and age >= 70:
        return "not indicated", False
    if cac is not None and cac >= 300:
        return "consider if bleeding risk is low; plaque burden is high", False
    if cac is not None and cac >= 100:
        return "consider only if bleeding risk is low", False
    return "not indicated", False


def diagnoses(patient: dict) -> list[str]:
    names: list[str] = []
    a1c = _num(patient, "a1c")
    bmi = _num(patient, "bmi")
    uacr = _num(patient, "uacr")
    cac = _num(patient, "cac")
    if _bool(patient, "diabetes") or diabetes_range(a1c):
        names.append("Diabetes")
    elif prediabetes_range(a1c):
        names.append("Prediabetes")
    if bmi is not None and bmi >= 40:
        names.append("Morbid obesity")
    elif bmi is not None and bmi >= 30:
        names.append("Obesity")
    if uacr is not None and uacr >= 300:
        names.append("Severely increased albuminuria")
    elif uacr is not None and uacr >= 30:
        names.append("Moderately increased albuminuria")
    if cac is not None and cac > 0:
        names.append("Subclinical coronary atherosclerosis")
    return names


def drivers(patient: dict) -> list[str]:
    items: list[str] = []
    for label, condition in (
        ("clinical ASCVD", _bool(patient, "clinical_ascvd")),
        ("CAC", (_num(patient, "cac") or 0) > 0),
        ("albuminuria", (_num(patient, "uacr") or 0) >= 30),
        ("ApoB", (_num(patient, "apob") or 0) >= 100),
        ("LDL-C", (_num(patient, "ldl_c", "ldl") or 0) >= 130),
        ("prediabetes", prediabetes_range(_num(patient, "a1c"))),
        (
            "premature family history",
            _bool(patient, "family_history_premature_ascvd", "premature_fhx_ascvd"),
        ),
    ):
        if condition:
            items.append(label)
    return items


def oracle_from_patient(patient: dict[str, Any]) -> dict[str, Any]:
    egfr = _num(patient, "egfr")
    uacr = _num(patient, "uacr")
    a1c = _num(patient, "a1c")
    cac = _num(patient, "cac")
    clinical_ascvd = _bool(patient, "clinical_ascvd")
    ckm, ckm_reason = ckm_stage(patient)
    plaque = plaque_status(cac, clinical_ascvd)
    level = risk_level(patient, ckm, plaque)
    lipid_action, ldl_target, apob_target = lipid_action_and_targets(patient, level)
    aspirin, aspirin_primary = aspirin_action(patient)
    output = OracleOutput(
        prevent_category=prevent_category(_num(patient, "prevent_10y_ascvd")),
        ckm_stage=ckm,
        ckm_reason=ckm_reason,
        egfr_stage=egfr_stage(egfr),
        albuminuria_category=albuminuria_category(uacr),
        kdigo_stage=kdigo_stage(egfr, uacr),
        plaque_status=plaque,
        risk_level=level,
        lipid_action=lipid_action,
        ldl_c_target=ldl_target,
        apob_target=apob_target,
        aspirin_action=aspirin,
        aspirin_primary_prevention_indicated=aspirin_primary,
        diabetes_range=diabetes_range(a1c),
        prediabetes_range=prediabetes_range(a1c),
        albuminuria_present=bool(uacr is not None and uacr >= 30),
        structural_plaque_detected=structural_plaque_detected(cac),
        diagnoses=diagnoses(patient),
        drivers=drivers(patient),
    )
    return asdict(output)
