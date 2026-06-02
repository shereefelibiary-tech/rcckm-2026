from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PHENOTYPES = (
    "low_risk",
    "intermediate_risk",
    "high_risk",
    "ckd_focused",
    "diabetes_focused",
    "ascvd_focused",
    "edge_case",
)


@dataclass(frozen=True)
class SyntheticCase:
    case_id: str
    phenotype: str
    patient: dict[str, Any]
    smartphrase_text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _choice(rng: random.Random, values: tuple[Any, ...] | list[Any]) -> Any:
    return values[rng.randrange(len(values))]


def _round(value: float, digits: int = 1) -> float:
    return round(float(value), digits)


def _bp(rng: random.Random, sbp_range: tuple[int, int], dbp_range: tuple[int, int]) -> tuple[int, int]:
    return rng.randint(*sbp_range), rng.randint(*dbp_range)


def _base_patient(rng: random.Random) -> dict[str, Any]:
    sex = _choice(rng, ("male", "female"))
    return {
        "age": rng.randint(35, 78),
        "sex": sex,
        "race_ethnicity": _choice(
            rng,
            (
                "White",
                "Black / African American",
                "South Asian",
                "Filipino",
                "Hispanic / Latino",
            ),
        ),
        "smoking": False,
        "sbp": 118,
        "dbp": 74,
        "bmi": _round(rng.uniform(22, 33)),
        "ldl_c": 105,
        "apob": 88,
        "triglycerides": 110,
        "hdl": 52 if sex == "male" else 58,
        "a1c": 5.4,
        "egfr": 82,
        "uacr": 8,
        "cac": None,
        "diabetes": False,
        "clinical_ascvd": False,
        "family_history_premature_ascvd": False,
        "family_history_relationship": None,
        "family_history_event_type": None,
        "family_history_age_at_event": None,
        "inflammatory_disease": False,
        "rheumatoid_arthritis": False,
        "psoriasis": False,
        "lp_a_value": None,
        "lp_a_unit": "nmol/L",
        "lipid_lowering": False,
        "bp_treated": False,
        "aspirin": False,
    }


def _apply_low_risk(patient: dict[str, Any], rng: random.Random) -> None:
    patient["age"] = rng.randint(35, 55)
    patient["sbp"], patient["dbp"] = _bp(rng, (102, 124), (62, 78))
    patient["bmi"] = _round(rng.uniform(20, 27))
    patient["ldl_c"] = rng.randint(65, 112)
    patient["apob"] = rng.randint(55, 88)
    patient["triglycerides"] = rng.randint(50, 130)
    patient["hdl"] = rng.randint(48, 75)
    patient["a1c"] = _round(rng.uniform(4.8, 5.5))
    patient["egfr"] = rng.randint(75, 110)
    patient["uacr"] = rng.randint(2, 18)
    patient["cac"] = _choice(rng, (None, 0))


def _apply_intermediate_risk(patient: dict[str, Any], rng: random.Random) -> None:
    patient["age"] = rng.randint(48, 68)
    patient["sbp"], patient["dbp"] = _bp(rng, (126, 148), (76, 92))
    patient["bmi"] = _round(rng.uniform(27, 36))
    patient["ldl_c"] = rng.randint(120, 168)
    patient["apob"] = rng.randint(95, 128)
    patient["triglycerides"] = rng.randint(135, 260)
    patient["hdl"] = rng.randint(34, 52)
    patient["a1c"] = _round(rng.uniform(5.7, 6.4))
    patient["egfr"] = rng.randint(60, 90)
    patient["uacr"] = _choice(rng, (rng.randint(8, 25), rng.randint(30, 140)))
    patient["cac"] = _choice(rng, (None, 0, rng.randint(1, 85)))
    patient["bp_treated"] = rng.random() < 0.45


def _apply_high_risk(patient: dict[str, Any], rng: random.Random) -> None:
    patient["age"] = rng.randint(52, 78)
    patient["sbp"], patient["dbp"] = _bp(rng, (138, 168), (82, 102))
    patient["bmi"] = _round(rng.uniform(30, 42))
    patient["ldl_c"] = rng.randint(145, 218)
    patient["apob"] = rng.randint(118, 165)
    patient["triglycerides"] = rng.randint(180, 430)
    patient["hdl"] = rng.randint(28, 44)
    patient["a1c"] = _round(rng.uniform(6.0, 8.8))
    patient["diabetes"] = patient["a1c"] >= 6.5
    patient["egfr"] = rng.randint(45, 76)
    patient["uacr"] = rng.randint(35, 360)
    patient["cac"] = _choice(rng, (rng.randint(100, 299), rng.randint(300, 650)))
    patient["smoking"] = rng.random() < 0.25
    patient["bp_treated"] = True


def _apply_ckd_focused(patient: dict[str, Any], rng: random.Random) -> None:
    patient["age"] = rng.randint(45, 80)
    patient["sbp"], patient["dbp"] = _bp(rng, (128, 160), (74, 96))
    patient["bmi"] = _round(rng.uniform(25, 40))
    patient["ldl_c"] = rng.randint(85, 155)
    patient["apob"] = rng.randint(80, 125)
    patient["triglycerides"] = rng.randint(95, 320)
    patient["hdl"] = rng.randint(32, 58)
    patient["a1c"] = _round(rng.uniform(5.4, 7.4))
    patient["diabetes"] = rng.random() < 0.45 or patient["a1c"] >= 6.5
    patient["egfr"] = _choice(rng, (rng.randint(15, 29), rng.randint(30, 44), rng.randint(45, 59)))
    patient["uacr"] = _choice(rng, (rng.randint(30, 250), rng.randint(300, 2400)))
    patient["cac"] = _choice(rng, (None, 0, rng.randint(1, 180)))
    patient["bp_treated"] = True


def _apply_diabetes_focused(patient: dict[str, Any], rng: random.Random) -> None:
    patient["age"] = rng.randint(35, 72)
    patient["sbp"], patient["dbp"] = _bp(rng, (122, 156), (74, 96))
    patient["bmi"] = _round(rng.uniform(29, 58))
    patient["ldl_c"] = rng.randint(75, 165)
    patient["apob"] = rng.randint(78, 140)
    patient["triglycerides"] = rng.randint(130, 520)
    patient["hdl"] = rng.randint(28, 50)
    patient["a1c"] = _round(rng.uniform(6.5, 11.8))
    patient["diabetes"] = True
    patient["egfr"] = rng.randint(45, 100)
    patient["uacr"] = _choice(rng, (rng.randint(10, 25), rng.randint(30, 299), rng.randint(300, 1200)))
    patient["cac"] = _choice(rng, (None, 0, rng.randint(1, 220)))
    patient["bp_treated"] = rng.random() < 0.65


def _apply_ascvd_focused(patient: dict[str, Any], rng: random.Random) -> None:
    patient["age"] = rng.randint(48, 82)
    patient["sbp"], patient["dbp"] = _bp(rng, (118, 152), (68, 90))
    patient["bmi"] = _round(rng.uniform(24, 38))
    patient["ldl_c"] = rng.randint(58, 145)
    patient["apob"] = rng.randint(65, 125)
    patient["triglycerides"] = rng.randint(80, 320)
    patient["hdl"] = rng.randint(32, 60)
    patient["a1c"] = _round(rng.uniform(5.4, 8.5))
    patient["diabetes"] = patient["a1c"] >= 6.5
    patient["egfr"] = rng.randint(38, 90)
    patient["uacr"] = _choice(rng, (rng.randint(5, 25), rng.randint(30, 220)))
    patient["cac"] = _choice(rng, (None, rng.randint(300, 900)))
    patient["clinical_ascvd"] = True
    patient["lipid_lowering"] = True
    patient["aspirin"] = True
    patient["bp_treated"] = True


def _apply_edge_case(patient: dict[str, Any], rng: random.Random) -> None:
    edge = _choice(
        rng,
        (
            "young_occult",
            "cac_zero_high_lpa",
            "albuminuria_normal_egfr",
            "severe_tg_ldl_unavailable",
            "suspected_inflammation",
        ),
    )
    patient["edge_case_type"] = edge
    if edge == "young_occult":
        patient["age"] = rng.randint(40, 52)
        patient["sex"] = "female"
        patient["ldl_c"] = rng.randint(145, 178)
        patient["apob"] = rng.randint(118, 142)
        patient["triglycerides"] = rng.randint(85, 180)
        patient["hdl"] = rng.randint(45, 68)
        patient["a1c"] = _round(rng.uniform(5.2, 6.1))
        patient["egfr"] = rng.randint(75, 105)
        patient["uacr"] = rng.randint(3, 22)
        patient["cac"] = None
        patient["lp_a_value"] = rng.randint(175, 360)
        patient["family_history_premature_ascvd"] = True
        patient["family_history_relationship"] = _choice(rng, ("father", "mother", "brother"))
        patient["family_history_event_type"] = "MI"
        patient["family_history_age_at_event"] = rng.randint(41, 54)
        patient["rheumatoid_arthritis"] = rng.random() < 0.5
        patient["inflammatory_disease"] = patient["rheumatoid_arthritis"]
    elif edge == "cac_zero_high_lpa":
        patient["age"] = rng.randint(42, 64)
        patient["ldl_c"] = rng.randint(100, 155)
        patient["apob"] = rng.randint(88, 118)
        patient["a1c"] = _round(rng.uniform(5.0, 6.2))
        patient["egfr"] = rng.randint(70, 105)
        patient["uacr"] = rng.randint(2, 24)
        patient["cac"] = 0
        patient["lp_a_value"] = rng.randint(150, 420)
    elif edge == "albuminuria_normal_egfr":
        patient["age"] = rng.randint(38, 66)
        patient["ldl_c"] = rng.randint(80, 145)
        patient["apob"] = rng.randint(78, 120)
        patient["a1c"] = _round(rng.uniform(5.5, 8.8))
        patient["diabetes"] = patient["a1c"] >= 6.5
        patient["egfr"] = rng.randint(90, 115)
        patient["uacr"] = _choice(rng, (rng.randint(80, 250), rng.randint(300, 900)))
        patient["cac"] = _choice(rng, (None, 0))
    elif edge == "severe_tg_ldl_unavailable":
        patient["age"] = rng.randint(35, 70)
        patient["ldl_c"] = None
        patient["apob"] = rng.randint(90, 150)
        patient["triglycerides"] = rng.randint(450, 900)
        patient["hdl"] = rng.randint(24, 42)
        patient["a1c"] = _round(rng.uniform(5.8, 10.5))
        patient["diabetes"] = patient["a1c"] >= 6.5
        patient["egfr"] = rng.randint(35, 95)
        patient["uacr"] = _choice(rng, (None, rng.randint(30, 600)))
        patient["cac"] = None
    else:
        patient["age"] = rng.randint(42, 68)
        patient["ldl_c"] = rng.randint(115, 165)
        patient["apob"] = rng.randint(95, 130)
        patient["a1c"] = _round(rng.uniform(5.3, 6.4))
        patient["egfr"] = rng.randint(60, 100)
        patient["uacr"] = rng.randint(4, 28)
        patient["cac"] = None
        patient["psoriasis"] = True
        patient["inflammatory_disease"] = True


def _add_optional_enhancers(patient: dict[str, Any], phenotype: str, rng: random.Random) -> None:
    if patient.get("lp_a_value") is None and rng.random() < (0.35 if phenotype != "low_risk" else 0.12):
        patient["lp_a_value"] = rng.randint(60, 320)
    if not patient.get("family_history_premature_ascvd") and rng.random() < 0.22:
        patient["family_history_premature_ascvd"] = True
        patient["family_history_relationship"] = _choice(rng, ("father", "mother", "brother", "sister"))
        patient["family_history_event_type"] = _choice(rng, ("MI", "stroke", "CABG", "PCI"))
        patient["family_history_age_at_event"] = rng.randint(42, 62)
    if not patient.get("inflammatory_disease") and rng.random() < 0.16:
        disease = _choice(rng, ("rheumatoid_arthritis", "psoriasis"))
        patient[disease] = True
        patient["inflammatory_disease"] = True
    if patient.get("race_ethnicity") == "South Asian":
        patient["south_asian_ancestry"] = True
    if patient.get("race_ethnicity") == "Filipino":
        patient["filipino_ancestry"] = True
    if patient.get("sex") == "female" and rng.random() < 0.14:
        patient[_choice(rng, ("gestational_diabetes", "preeclampsia", "gestational_hypertension"))] = True


def generate_patient(
    *,
    case_id: str = "synthetic_001",
    phenotype: str | None = None,
    seed: int | None = None,
) -> SyntheticCase:
    rng = random.Random(seed)
    selected = phenotype or _choice(rng, PHENOTYPES)
    if selected not in PHENOTYPES:
        raise ValueError(f"Unknown phenotype: {selected}")

    patient = _base_patient(rng)
    {
        "low_risk": _apply_low_risk,
        "intermediate_risk": _apply_intermediate_risk,
        "high_risk": _apply_high_risk,
        "ckd_focused": _apply_ckd_focused,
        "diabetes_focused": _apply_diabetes_focused,
        "ascvd_focused": _apply_ascvd_focused,
        "edge_case": _apply_edge_case,
    }[selected](patient, rng)
    _add_optional_enhancers(patient, selected, rng)
    patient["case_id"] = case_id
    patient["phenotype"] = selected
    return SyntheticCase(
        case_id=case_id,
        phenotype=selected,
        patient=patient,
        smartphrase_text=render_epic_smartphrase(patient),
    )


def _value(value: Any, suffix: str = "") -> str:
    if value is None or value == "":
        return "Not available"
    return f"{value}{suffix}"


def _yes_no(value: Any) -> str:
    return "Yes" if bool(value) else "No"


def _problem_list(patient: dict[str, Any]) -> list[str]:
    items: list[str] = []
    if patient.get("clinical_ascvd"):
        items.append(_choice(random.Random(patient["case_id"]), ("Coronary artery disease", "History of myocardial infarction", "Peripheral arterial disease")))
    if patient.get("diabetes"):
        items.append("Type 2 diabetes mellitus")
    if patient.get("bp_treated") or (patient.get("sbp") or 0) >= 140:
        items.append("Essential hypertension")
    if (patient.get("bmi") or 0) >= 40:
        items.append("Morbid obesity")
    elif (patient.get("bmi") or 0) >= 30:
        items.append("Obesity")
    if patient.get("rheumatoid_arthritis"):
        items.append("Rheumatoid arthritis")
    if patient.get("psoriasis"):
        items.append("Psoriasis")
    if patient.get("egfr") is not None and patient["egfr"] < 60:
        items.append("Chronic kidney disease")
    if patient.get("uacr") is not None and patient["uacr"] >= 30:
        items.append("Albuminuria")
    return items


def _medications(patient: dict[str, Any]) -> list[str]:
    meds: list[str] = []
    if patient.get("bp_treated"):
        meds.append("Losartan 50 mg daily")
    if patient.get("lipid_lowering"):
        meds.append("Rosuvastatin 20 mg daily")
    if patient.get("diabetes"):
        meds.append("Metformin ER 1000 mg daily")
        if (patient.get("uacr") or 0) >= 30 or (patient.get("egfr") or 100) < 60:
            meds.append("Empagliflozin 10 mg daily")
    if patient.get("aspirin"):
        meds.append("Aspirin 81 mg daily")
    return meds


def render_epic_smartphrase(patient: dict[str, Any]) -> str:
    fhx = "No premature ASCVD in first-degree relative."
    if patient.get("family_history_premature_ascvd"):
        relationship = patient.get("family_history_relationship") or "father"
        event = patient.get("family_history_event_type") or "MI"
        age = patient.get("family_history_age_at_event") or 49
        fhx = f"{relationship.title()} {event} age {age}."

    ldl_line = (
        "LDL-C unable to calculate due to high triglycerides"
        if patient.get("ldl_c") is None
        else f"LDL-C {patient['ldl_c']} mg/dL"
    )
    lpa = "Lp(a) not checked"
    if patient.get("lp_a_value") is not None:
        lpa = f"LIPOA {patient['lp_a_value']} {patient.get('lp_a_unit') or 'nmol/L'}"

    inflammatory = []
    if patient.get("rheumatoid_arthritis"):
        inflammatory.append("Rheumatoid arthritis")
    if patient.get("psoriasis"):
        inflammatory.append("Psoriasis")
    if patient.get("inflammatory_disease") and not inflammatory:
        inflammatory.append("Chronic inflammatory disease")

    reproductive = []
    for key, label in (
        ("gestational_diabetes", "Gestational diabetes"),
        ("preeclampsia", "Preeclampsia"),
        ("gestational_hypertension", "Gestational hypertension"),
    ):
        if patient.get(key):
            reproductive.append(label)

    problem_list = _problem_list(patient)
    medications = _medications(patient)
    return "\n".join(
        [
            "=== CARDIOVASCULAR RISK ASSESSMENT ===",
            "",
            f"Age: {patient['age']} y.o.",
            f"Sex: {patient['sex']}",
            f"Race/Ethnicity: {patient.get('race_ethnicity', 'Not specified')}",
            "",
            f"Smoking status: {'Current smoker' if patient.get('smoking') else 'Never smoker'}",
            "",
            "Blood pressure (most recent):",
            f"BP: {patient['sbp']}/{patient['dbp']}",
            f"BMI: {patient['bmi']}",
            "",
            f"Clinical ASCVD: {_yes_no(patient.get('clinical_ascvd'))}",
            "Clinical ASCVD details:",
            "Documented CAD/MI/PAD/stroke." if patient.get("clinical_ascvd") else "No known ASCVD.",
            "",
            "Family History:",
            fhx,
            "",
            "Lipids:",
            ldl_line,
            f"HDL-C {patient['hdl']} mg/dL",
            f"Triglycerides {patient['triglycerides']} mg/dL",
            "",
            "A1c:",
            f"HEMOGLOBIN A1C {patient['a1c']}%",
            "",
            "ApoB:",
            f"APOB {patient['apob']} mg/dL",
            "",
            "Lp(a):",
            lpa,
            "",
            "eGFR:",
            f"LABGLOM {patient['egfr']} mL/min/1.73m2",
            "",
            "Urine ACR:",
            f"ALBCREAT {_value(patient.get('uacr'), ' mg/g')}",
            "",
            f"Coronary artery calcium (CAC) score: {_value(patient.get('cac'))}",
            "CAC percentile:",
            "",
            "Risk enhancers:",
            f"Inflammatory disease: {'; '.join(inflammatory) if inflammatory else 'No'}",
            f"Reproductive history: {'; '.join(reproductive) if reproductive else 'No'}",
            "",
            "Medications:",
            "\n".join(medications) if medications else "No active cardiometabolic medications.",
            "",
            "Problem list:",
            "\n".join(problem_list) if problem_list else "No active cardiometabolic diagnoses listed.",
            "",
        ]
    )


def write_case(case: SyntheticCase, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{case.case_id}.json"
    txt_path = output_dir / f"{case.case_id}.txt"
    json_path.write_text(json.dumps(case.to_dict(), indent=2, default=str), encoding="utf-8")
    txt_path.write_text(case.smartphrase_text, encoding="utf-8")
    return json_path, txt_path
