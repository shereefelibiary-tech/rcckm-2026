from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class MedicationEntry:
    normalized_name: str
    med_class: str
    aliases: tuple[str, ...]


LIPID_MEDICATIONS: tuple[MedicationEntry, ...] = (
    MedicationEntry("atorvastatin", "statin", ("atorvastatin", "Lipitor")),
    MedicationEntry("rosuvastatin", "statin", ("rosuvastatin", "Crestor")),
    MedicationEntry("simvastatin", "statin", ("simvastatin", "Zocor")),
    MedicationEntry("pravastatin", "statin", ("pravastatin", "Pravachol")),
    MedicationEntry("lovastatin", "statin", ("lovastatin", "Mevacor", "Altoprev")),
    MedicationEntry("pitavastatin", "statin", ("pitavastatin", "Livalo", "Zypitamag")),
    MedicationEntry("fluvastatin", "statin", ("fluvastatin", "Lescol")),
    MedicationEntry("ezetimibe", "ezetimibe", ("ezetimibe", "Zetia")),
    MedicationEntry("evolocumab", "pcsk9", ("evolocumab", "Repatha")),
    MedicationEntry("alirocumab", "pcsk9", ("alirocumab", "Praluent")),
    MedicationEntry("inclisiran", "inclisiran", ("inclisiran", "Leqvio")),
    MedicationEntry("bempedoic acid", "bempedoic_acid", ("bempedoic acid", "Nexletol")),
    MedicationEntry("bempedoic acid-ezetimibe", "bempedoic_acid_ezetimibe", ("bempedoic acid-ezetimibe", "Nexlizet")),
    MedicationEntry("icosapent ethyl", "icosapent_ethyl", ("icosapent ethyl", "Vascepa")),
    MedicationEntry("omega-3 acid ethyl esters", "omega3", ("omega-3 acid ethyl esters", "Lovaza")),
    MedicationEntry("fenofibrate", "fibrate", ("fenofibrate", "Tricor", "Trilipix", "Antara", "Lofibra", "Lipofen")),
    MedicationEntry("gemfibrozil", "fibrate", ("gemfibrozil", "Lopid")),
    MedicationEntry("niacin", "niacin", ("niacin", "Niaspan")),
    MedicationEntry("colesevelam", "bile_acid_sequestrant", ("colesevelam", "Welchol")),
    MedicationEntry("cholestyramine", "bile_acid_sequestrant", ("cholestyramine", "Questran", "Prevalite")),
    MedicationEntry("colestipol", "bile_acid_sequestrant", ("colestipol", "Colestid")),
)


BP_KIDNEY_MEDICATIONS: tuple[MedicationEntry, ...] = (
    MedicationEntry("lisinopril", "ace_inhibitor", ("lisinopril",)),
    MedicationEntry("benazepril", "ace_inhibitor", ("benazepril",)),
    MedicationEntry("enalapril", "ace_inhibitor", ("enalapril",)),
    MedicationEntry("ramipril", "ace_inhibitor", ("ramipril",)),
    MedicationEntry("captopril", "ace_inhibitor", ("captopril",)),
    MedicationEntry("quinapril", "ace_inhibitor", ("quinapril",)),
    MedicationEntry("fosinopril", "ace_inhibitor", ("fosinopril",)),
    MedicationEntry("trandolapril", "ace_inhibitor", ("trandolapril",)),
    MedicationEntry("losartan", "arb", ("losartan",)),
    MedicationEntry("valsartan", "arb", ("valsartan",)),
    MedicationEntry("irbesartan", "arb", ("irbesartan",)),
    MedicationEntry("olmesartan", "arb", ("olmesartan",)),
    MedicationEntry("telmisartan", "arb", ("telmisartan",)),
    MedicationEntry("candesartan", "arb", ("candesartan",)),
    MedicationEntry("azilsartan", "arb", ("azilsartan",)),
    MedicationEntry("hydrochlorothiazide", "thiazide", ("hydrochlorothiazide", "HCTZ")),
    MedicationEntry("chlorthalidone", "thiazide", ("chlorthalidone",)),
    MedicationEntry("indapamide", "thiazide", ("indapamide",)),
    MedicationEntry("amlodipine", "calcium_channel_blocker", ("amlodipine",)),
    MedicationEntry("felodipine", "calcium_channel_blocker", ("felodipine",)),
    MedicationEntry("nifedipine", "calcium_channel_blocker", ("nifedipine",)),
    MedicationEntry("diltiazem", "calcium_channel_blocker", ("diltiazem",)),
    MedicationEntry("verapamil", "calcium_channel_blocker", ("verapamil",)),
    MedicationEntry("metoprolol", "beta_blocker", ("metoprolol",)),
    MedicationEntry("carvedilol", "beta_blocker", ("carvedilol",)),
    MedicationEntry("atenolol", "beta_blocker", ("atenolol",)),
    MedicationEntry("nebivolol", "beta_blocker", ("nebivolol",)),
    MedicationEntry("bisoprolol", "beta_blocker", ("bisoprolol",)),
    MedicationEntry("propranolol", "beta_blocker", ("propranolol",)),
    MedicationEntry("spironolactone", "mra", ("spironolactone",)),
    MedicationEntry("eplerenone", "mra", ("eplerenone",)),
    MedicationEntry("finerenone", "mra", ("finerenone", "Kerendia")),
)


DIABETES_CKM_MEDICATIONS: tuple[MedicationEntry, ...] = (
    MedicationEntry("metformin", "metformin", ("metformin",)),
    MedicationEntry("empagliflozin", "sglt2", ("empagliflozin", "Jardiance")),
    MedicationEntry("dapagliflozin", "sglt2", ("dapagliflozin", "Farxiga")),
    MedicationEntry("canagliflozin", "sglt2", ("canagliflozin", "Invokana")),
    MedicationEntry("ertugliflozin", "sglt2", ("ertugliflozin", "Steglatro")),
    MedicationEntry("bexagliflozin", "sglt2", ("bexagliflozin", "Brenzavvy")),
    MedicationEntry("semaglutide", "glp1_gip", ("semaglutide", "Ozempic", "Wegovy", "Rybelsus")),
    MedicationEntry("tirzepatide", "glp1_gip", ("tirzepatide", "Mounjaro", "Zepbound")),
    MedicationEntry("dulaglutide", "glp1_gip", ("dulaglutide", "Trulicity")),
    MedicationEntry("liraglutide", "glp1_gip", ("liraglutide", "Victoza", "Saxenda")),
    MedicationEntry("exenatide", "glp1_gip", ("exenatide", "Byetta", "Bydureon")),
    MedicationEntry("lixisenatide", "glp1_gip", ("lixisenatide", "Adlyxin")),
    MedicationEntry("sitagliptin", "dpp4", ("sitagliptin", "Januvia")),
    MedicationEntry("linagliptin", "dpp4", ("linagliptin", "Tradjenta")),
    MedicationEntry("saxagliptin", "dpp4", ("saxagliptin", "Onglyza")),
    MedicationEntry("alogliptin", "dpp4", ("alogliptin", "Nesina")),
    MedicationEntry("glipizide", "sulfonylurea", ("glipizide",)),
    MedicationEntry("glyburide", "sulfonylurea", ("glyburide",)),
    MedicationEntry("glimepiride", "sulfonylurea", ("glimepiride",)),
    MedicationEntry("pioglitazone", "tzd", ("pioglitazone", "Actos")),
    MedicationEntry("rosiglitazone", "tzd", ("rosiglitazone", "Avandia")),
    MedicationEntry("insulin glargine", "insulin", ("insulin glargine", "Lantus", "Basaglar", "Toujeo")),
    MedicationEntry("insulin degludec", "insulin", ("insulin degludec", "Tresiba")),
    MedicationEntry("insulin detemir", "insulin", ("insulin detemir", "Levemir")),
    MedicationEntry("insulin lispro", "insulin", ("insulin lispro", "Humalog")),
    MedicationEntry("insulin aspart", "insulin", ("insulin aspart", "Novolog")),
    MedicationEntry("insulin glulisine", "insulin", ("insulin glulisine", "Apidra")),
    MedicationEntry("regular insulin", "insulin", ("regular insulin", "Humulin R", "Novolin R")),
    MedicationEntry("NPH insulin", "insulin", ("NPH", "Humulin N", "Novolin N")),
)


COMBINATION_MEDICATIONS: tuple[MedicationEntry, ...] = (
    MedicationEntry("empagliflozin/metformin", "sglt2_metformin_combo", ("empagliflozin/metformin", "Synjardy")),
    MedicationEntry("dapagliflozin/metformin", "sglt2_metformin_combo", ("dapagliflozin/metformin", "Xigduo")),
    MedicationEntry("canagliflozin/metformin", "sglt2_metformin_combo", ("canagliflozin/metformin", "Invokamet")),
    MedicationEntry("sitagliptin/metformin", "dpp4_metformin_combo", ("sitagliptin/metformin", "Janumet")),
    MedicationEntry("linagliptin/metformin", "dpp4_metformin_combo", ("linagliptin/metformin", "Jentadueto")),
    MedicationEntry("saxagliptin/metformin", "dpp4_metformin_combo", ("saxagliptin/metformin", "Kombiglyze")),
    MedicationEntry("dapagliflozin/saxagliptin", "sglt2_dpp4_combo", ("dapagliflozin/saxagliptin", "Qtern")),
    MedicationEntry("empagliflozin/linagliptin", "sglt2_dpp4_combo", ("empagliflozin/linagliptin", "Glyxambi")),
    MedicationEntry("sacubitril/valsartan", "arni", ("sacubitril/valsartan", "Entresto")),
    MedicationEntry("amlodipine/benazepril", "ccb_ace_combo", ("amlodipine/benazepril", "Lotrel")),
    MedicationEntry("losartan/HCTZ", "arb_thiazide_combo", ("losartan/HCTZ", "Hyzaar")),
    MedicationEntry("valsartan/HCTZ", "arb_thiazide_combo", ("valsartan/HCTZ", "Diovan HCT")),
    MedicationEntry("olmesartan/HCTZ", "arb_thiazide_combo", ("olmesartan/HCTZ", "Benicar HCT")),
)


ALL_MEDICATIONS: tuple[MedicationEntry, ...] = (
    COMBINATION_MEDICATIONS
    + LIPID_MEDICATIONS
    + DIABETES_CKM_MEDICATIONS
    + BP_KIDNEY_MEDICATIONS
)

INACTIVE_RE = re.compile(
    r"\b(stopped|stop|discontinue[sd]?|dc\b|d/c|held|off|no longer taking|"
    r"allerg(?:y|ic)|intoleran(?:ce|t)|failed|could not tolerate)\b",
    re.IGNORECASE,
)

ACTIVE_RE = re.compile(
    r"\b(on|taking|takes|current(?:ly)?|active|continue|continues|start(?:ed)?|"
    r"med(?:ication)?s?\s*(?:include|:)|rx|prescribed)\b",
    re.IGNORECASE,
)

MED_SECTION_RE = re.compile(
    r"\b(current meds?|medications?|active medications?|home meds?|outpatient medications?|"
    r"antihypertensive|hypertension meds?|htn meds?|patient-reported)\b",
    re.IGNORECASE,
)

DOSE_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|units?|u)\b", re.IGNORECASE)

FREQUENCY_RE = re.compile(
    r"\b(daily|nightly|bid|twice daily|tid|three times daily|qhs|weekly|qweek|"
    r"every\s+\d+\s+weeks?|q\d+\s*weeks?|monthly)\b",
    re.IGNORECASE,
)


def _line_fragments(raw: str) -> list[str]:
    lines: list[str] = []
    for line in (raw or "").splitlines():
        line = line.strip(" \t-*•")
        if not line:
            continue
        parts = [p.strip(" \t-*•") for p in re.split(r"(?<=[.;])\s+", line) if p.strip()]
        lines.extend(parts or [line])
    if not lines and raw.strip():
        lines = [raw.strip()]
    return lines


def _alias_pattern(alias: str) -> str:
    escaped = re.escape(alias)
    escaped = escaped.replace(r"\/", r"\s*/\s*")
    escaped = escaped.replace(r"\ ", r"\s+")
    return rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])"


def _line_active_state(line: str, has_dose_or_frequency: bool) -> bool | None:
    if INACTIVE_RE.search(line):
        return False
    if ACTIVE_RE.search(line) or MED_SECTION_RE.search(line) or has_dose_or_frequency:
        return True
    return None


def _med_segment(line: str, start: int) -> str:
    window = line[start : start + 90]
    return re.split(r"[,;]", window, maxsplit=1)[0]


def _best_dose(line: str, start: int) -> str | None:
    window = _med_segment(line, start)
    match = DOSE_RE.search(window)
    return match.group(0).replace(" ", " ") if match else None


def _best_frequency(line: str, start: int) -> str | None:
    window = _med_segment(line, start)
    match = FREQUENCY_RE.search(window)
    return match.group(0) if match else None


def _dose_number(dose: str | None) -> float | None:
    if not dose:
        return None
    match = re.search(r"\d+(?:\.\d+)?", dose)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _statin_intensity(normalized_name: str, dose: str | None, source_line: str = "") -> str | None:
    amount = _dose_number(dose)
    if amount is None:
        return None
    name = normalized_name.lower()
    line = source_line.lower()

    if name == "atorvastatin":
        if 40 <= amount <= 80:
            return "high"
        if 10 <= amount <= 20:
            return "moderate"
    if name == "rosuvastatin":
        if 20 <= amount <= 40:
            return "high"
        if 5 <= amount <= 10:
            return "moderate"
    if name == "simvastatin":
        if 20 <= amount <= 40:
            return "moderate"
        if amount == 10:
            return "low"
    if name == "pravastatin":
        if 40 <= amount <= 80:
            return "moderate"
        if 10 <= amount <= 20:
            return "low"
    if name == "lovastatin":
        if amount == 40:
            return "moderate"
        if amount == 20:
            return "low"
    if name == "fluvastatin":
        if amount == 80 or "xl" in line:
            return "moderate"
        if 20 <= amount <= 40:
            return "low"
    if name == "pitavastatin" and 1 <= amount <= 4:
        return "moderate"
    return None


def _set_true_if_active(result: dict[str, Any], key: str, active: bool | None) -> None:
    if active is True:
        result[key] = True
    elif result.get(key) is not True and result.get(key) is None:
        result[key] = None


def _apply_flags(result: dict[str, Any], med: dict[str, Any]) -> None:
    if med.get("active") is not True:
        return
    med_class = str(med.get("class") or "")

    if med_class in {
        "statin",
        "ezetimibe",
        "pcsk9",
        "inclisiran",
        "bempedoic_acid",
        "bempedoic_acid_ezetimibe",
        "icosapent_ethyl",
        "omega3",
        "fibrate",
        "niacin",
        "bile_acid_sequestrant",
    }:
        result["lipidLowering"] = True
    if med_class == "statin":
        result["statin"] = True
        intensity = _statin_intensity(
            str(med.get("normalized_name") or ""),
            med.get("dose"),
            str(med.get("source_line") or ""),
        )
        if intensity:
            order = {"low": 1, "moderate": 2, "high": 3}
            current = result.get("statin_intensity")
            if current is None or order[intensity] > order.get(current, 0):
                result["statin_intensity"] = intensity
    if med_class == "ezetimibe" or med_class == "bempedoic_acid_ezetimibe":
        result["ezetimibe"] = True
    if med_class == "pcsk9":
        result["pcsk9"] = True
    if med_class in {"bempedoic_acid", "bempedoic_acid_ezetimibe"}:
        result["bempedoic_acid"] = True

    if med_class in {"sglt2", "sglt2_metformin_combo", "sglt2_dpp4_combo"}:
        result["sglt2"] = True
    if med_class in {"glp1_gip"}:
        result["glp1_gip"] = True
    if med_class in {"metformin", "sglt2_metformin_combo", "dpp4_metformin_combo"}:
        result["metformin"] = True

    if med_class in {
        "ace_inhibitor",
        "arb",
        "thiazide",
        "calcium_channel_blocker",
        "beta_blocker",
        "mra",
        "arni",
        "ccb_ace_combo",
        "arb_thiazide_combo",
    }:
        result["bpTreated"] = True
    if med_class in {"ace_inhibitor", "arb", "arni", "ccb_ace_combo", "arb_thiazide_combo"}:
        result["ace_arb"] = True
    if med_class == "mra":
        result["mra"] = True


def extract_medications_structured(raw: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "medications_raw": None,
        "medications_detected": [],
        "lipidLowering": None,
        "statin": None,
        "statin_intensity": None,
        "ezetimibe": None,
        "pcsk9": None,
        "bempedoic_acid": None,
        "sglt2": None,
        "glp1_gip": None,
        "metformin": None,
        "ace_arb": None,
        "bpTreated": None,
        "mra": None,
    }
    if not raw:
        return result

    detected_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for line in _line_fragments(raw):
        line_has_dose_or_frequency = bool(DOSE_RE.search(line) or FREQUENCY_RE.search(line))
        for entry in ALL_MEDICATIONS:
            for alias in entry.aliases:
                match = re.search(_alias_pattern(alias), line, re.IGNORECASE)
                if not match:
                    continue
                dose = _best_dose(line, match.end())
                frequency = _best_frequency(line, match.end())
                active = _line_active_state(line, bool(dose or frequency or line_has_dose_or_frequency))
                key = (entry.normalized_name.lower(), line.lower())
                detected_by_key[key] = {
                    "name": match.group(0),
                    "normalized_name": entry.normalized_name,
                    "class": entry.med_class,
                    "dose": dose,
                    "frequency": frequency,
                    "active": active,
                    "source_line": line,
                }
                break

    detected = list(detected_by_key.values())
    result["medications_detected"] = detected
    active_or_unknown = [m for m in detected if m.get("active") is not False]
    if active_or_unknown:
        names = [str(m["normalized_name"]) for m in active_or_unknown]
        result["medications_raw"] = ", ".join(dict.fromkeys(names))

    for med in detected:
        _apply_flags(result, med)

    return result
