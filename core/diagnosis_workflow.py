from __future__ import annotations

"""Diagnosis normalization and review helpers for RCCKM report output."""

from typing import Any
import re


def _as_float(x: Any) -> float | None:
    try:
        if x is None:
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def _glp1_comorbidity_present(patient_input: dict[str, Any], dx_list: list[dict[str, Any]]) -> bool:
    a1c = _as_float((patient_input or {}).get("a1c"))
    triglycerides = _as_float((patient_input or {}).get("triglycerides"))
    if triglycerides is None:
        triglycerides = _as_float((patient_input or {}).get("tg"))
    sbp = _as_float((patient_input or {}).get("sbp"))
    ldl = _as_float((patient_input or {}).get("ldl"))
    uacr = _as_float((patient_input or {}).get("uacr"))

    if bool((patient_input or {}).get("diabetes")):
        return True
    if a1c is not None and a1c >= 5.7:
        return True
    if triglycerides is not None and triglycerides >= 150:
        return True
    if bool((patient_input or {}).get("bp_treated")):
        return True
    if sbp is not None and sbp >= 130:
        return True
    if ldl is not None and ldl >= 130:
        return True
    if uacr is not None and uacr >= 30:
        return True

    keywords = (
        "metabolic syndrome",
        "hypertension",
        "diabetes",
        "dyslipidemia",
        "ckd",
        "chronic kidney disease",
    )
    for dx in dx_list:
        if not isinstance(dx, dict):
            continue
        hay = " ".join(
            [
                str(dx.get("dx_id") or "").strip().lower(),
                str(dx.get("label_display") or "").strip().lower(),
                str(dx.get("label") or "").strip().lower(),
            ]
        )
        if any(k in hay for k in keywords):
            return True
    return False


def augment_diagnoses_with_bmi_glp1(
    all_dx: list[dict[str, Any]],
    patient_input: dict[str, Any],
) -> list[dict[str, Any]]:
    """Add BMI-related diagnosis candidates when worksheet inputs support them.

    Returns a normalized copy of the diagnosis list without changing upstream
    clinical engine thresholds.
    """
    bmi = _as_float((patient_input or {}).get("bmi"))
    if bmi is None:
        return list(all_dx)

    rows = [d for d in (all_dx or []) if isinstance(d, dict)]
    has_obesity = any(str(d.get("dx_id") or "").strip() == "dx_obesity" for d in rows)
    has_overweight = any(str(d.get("dx_id") or "").strip() == "dx_overweight" for d in rows)

    if bmi >= 30.0:
        rows = [d for d in rows if str(d.get("dx_id") or "").strip() != "dx_overweight"]
        if not has_obesity:
            rows.append(
                {
                    "dx_id": "dx_obesity",
                    "label": "Obesity",
                    "label_display": "Obesity",
                    "status": "confirmed",
                    "icd10_suggested": ["E66.9"],
                    "icd10_confirmed": ["E66.9"],
                    "hcc_suggested": [],
                    "hcc_confirmed": [],
                    "ev": [{"key": "bmi", "value": bmi, "unit": "kg/m2"}],
                    "glp1_support": {
                        "eligible_by_bmi": True,
                        "eligible_by_bmi_and_comorbidity": True,
                    },
                }
            )
        return rows

    if 27.0 <= bmi < 30.0:
        overweight_gate_passes = _glp1_comorbidity_present(patient_input or {}, rows)
        if overweight_gate_passes:
            if not has_overweight:
                rows.append(
                    {
                        "dx_id": "dx_overweight",
                        "label": "Overweight",
                        "label_display": "Overweight",
                        "status": "confirmed",
                        "icd10_suggested": ["E66.3"],
                        "icd10_confirmed": ["E66.3"],
                        "hcc_suggested": [],
                        "hcc_confirmed": [],
                        "ev": [{"key": "bmi", "value": bmi, "unit": "kg/m2"}],
                        "glp1_support": {
                            "eligible_by_bmi": False,
                            "eligible_by_bmi_and_comorbidity": True,
                        },
                    }
                )
        else:
            rows = [d for d in rows if str(d.get("dx_id") or "").strip() != "dx_overweight"]
    return rows


def _extract_code_list(value: Any) -> list[str]:
    codes: list[str] = []
    if isinstance(value, list):
        for ent in value:
            if isinstance(ent, dict):
                code = str(ent.get("code") or "").strip()
            else:
                code = str(ent or "").strip()
            if code:
                codes.append(code)
    elif isinstance(value, str):
        for part in value.split("|"):
            code = part.strip()
            if code:
                codes.append(code)
    return codes


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _object_diagnosis_to_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    label = str(
        getattr(item, "label", None)
        or getattr(item, "name", None)
        or getattr(item, "text", None)
        or ""
    ).strip()
    return {
        "dx_id": getattr(item, "dx_id", None) or getattr(item, "id", None) or label,
        "label": label,
        "diagnosis": getattr(item, "diagnosis", None) or label,
        "status": getattr(item, "status", None) or getattr(item, "bucket", None),
        "source": getattr(item, "source", None),
        "icd10": getattr(item, "icd10", None),
        "icd10_suggested": getattr(item, "icd10_suggested", None),
        "icd10_candidates": getattr(item, "icd10_candidates", None),
        "icd10_confirmed": getattr(item, "icd10_confirmed", None),
        "icd": getattr(item, "icd", None),
        "icd10_code": getattr(item, "icd10_code", None),
        "hcc": getattr(item, "hcc", None),
        "hcc_suggested": getattr(item, "hcc_suggested", None),
        "hcc_confirmed": getattr(item, "hcc_confirmed", None),
        "hcc_relevant": getattr(item, "hcc_relevant", None),
        "hcc_supported": getattr(item, "hcc_supported", None),
        "hcc_label": getattr(item, "hcc_label", None),
        "confidence": getattr(item, "confidence", None),
        "review_status": getattr(item, "review_status", None),
        "evidence": getattr(item, "evidence", None),
        "ev": getattr(item, "ev", None),
        "why": getattr(item, "why", None),
        "reason": getattr(item, "reason", None),
        "rationale": getattr(item, "rationale", None),
    }


def _raw_diagnosis_sources(out: Any) -> list[Any]:
    if out is None:
        return []

    if hasattr(out, "diagnosis_candidates"):
        candidates = getattr(out, "diagnosis_candidates") or []
        if candidates:
            return [_object_diagnosis_to_dict(x) for x in candidates]

    if not isinstance(out, dict):
        return []

    diagnosis_synthesis = (out or {}).get("diagnosisSynthesis")
    diagnosis_synthesis_diagnoses = (
        diagnosis_synthesis
        if isinstance(diagnosis_synthesis, list)
        else (diagnosis_synthesis or {}).get("diagnoses")
    )

    for candidate in (
        diagnosis_synthesis_diagnoses,
        (out or {}).get("diagnosis_candidates"),
        (out or {}).get("emr_dx"),
        (out or {}).get("diagnoses"),
        ((out or {}).get("insights") or {}).get("emr_dx"),
    ):
        if isinstance(candidate, list) and candidate:
            return [_object_diagnosis_to_dict(x) for x in candidate]

    return []


def normalize_diagnosis_entries(out: Any) -> list[dict[str, Any]]:
    """Convert engine diagnosis candidates into a uniform display/export shape."""
    raw = [x for x in _raw_diagnosis_sources(out) if isinstance(x, dict)]

    diagnoses: list[dict[str, Any]] = []
    for item in raw:
        dx_id = str(item.get("dx_id") or item.get("id") or "").strip()
        label = str(item.get("label") or item.get("name") or item.get("text") or "").strip()
        if not label:
            continue
        if "family history" in label.lower():
            continue
        if not dx_id:
            dx_id = label

        status_raw = str(item.get("status") or item.get("bucket") or "confirmed").strip().lower()
        source = str(item.get("source") or "").strip()
        status = _normalize_status(status_raw, label, source)

        label_display = re.sub(r"\s*—\s*confirm.*$", "", label, flags=re.I).strip()

        icd10_suggested = _extract_code_list(item.get("icd10_suggested"))
        if not icd10_suggested:
            icd10_suggested = _extract_code_list(item.get("icd10_candidates"))
        if not icd10_suggested:
            icd10_suggested = _extract_code_list(item.get("icd10"))
        if not icd10_suggested:
            icd10_suggested = _extract_code_list(item.get("icd"))
        if not icd10_suggested:
            icd10_suggested = _extract_code_list(item.get("icd10_code"))

        icd10_confirmed = _extract_code_list(item.get("icd10_confirmed"))
        if status in {"confirmed", "clinician_confirmed", "confirmed_by_data"} and not icd10_confirmed:
            icd10_confirmed = list(icd10_suggested)
        if status in {"suspected", "review_suggested"}:
            icd10_confirmed = []

        hcc_suggested = _extract_code_list(item.get("hcc_suggested"))
        hcc_confirmed = _extract_code_list(item.get("hcc_confirmed"))
        hcc = item.get("hcc")
        if not hcc_suggested and isinstance(hcc, dict) and bool(hcc.get("is_hcc")):
            hcc_suggested = ["HCC"]
        if not hcc_suggested and isinstance(hcc, str) and hcc.strip():
            hcc_suggested = [hcc.strip()]
        hcc_label = str(item.get("hcc_label") or "").strip()
        if not hcc_suggested and bool(item.get("hcc_supported")):
            hcc_suggested = [hcc_label or "HCC-supported"]
        if status in {"confirmed", "clinician_confirmed", "confirmed_by_data"} and not hcc_confirmed:
            hcc_confirmed = list(hcc_suggested)
        if status in {"suspected", "review_suggested"}:
            hcc_confirmed = []

        diagnoses.append(
            {
                "dx_id": dx_id,
                "label": label,
                "diagnosis": str(item.get("diagnosis") or label).strip(),
                "label_display": label_display,
                "status": status,
                "icd10_suggested": _dedupe(icd10_suggested),
                "icd10_confirmed": _dedupe(icd10_confirmed),
                "hcc_suggested": _dedupe(hcc_suggested),
                "hcc_confirmed": _dedupe(hcc_confirmed),
                **{
                    k: item[k]
                    for k in ("evidence", "ev", "why", "reason", "rationale", "source")
                    if k in item and item[k]
                },
                "hcc_supported": bool(item.get("hcc_supported")) or bool(hcc_suggested),
                "hcc_label": hcc_label or (hcc_suggested[0] if hcc_suggested else None),
                "confidence": item.get("confidence") or status,
                "review_status": item.get("review_status") or status,
            }
        )

    return diagnoses


def _normalize_status(status_raw: str, label: str, source: str = "") -> str:
    status = str(status_raw or "").strip().lower().replace("-", "_")
    label_l = str(label or "").strip().lower()
    source_l = str(source or "").strip().lower()

    if status in {"confirmed", "clinician_confirmed", "reported"}:
        return "clinician_confirmed"
    if status.startswith("sus") or status in {"review", "review_suggested"}:
        return "review_suggested"

    if "confirm" in label_l or "confirm" in source_l or "incomplete" in source_l:
        return "review_suggested"

    if status in {"data_derived", "data-derived", ""}:
        return "confirmed_by_data"

    return "confirmed_by_data"


def normalize_diagnosis_pipeline(out: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize diagnoses and update the in-flight pipeline source of truth."""
    diagnoses = normalize_diagnosis_entries(out)
    out["diagnosisSynthesis"] = diagnoses
    return diagnoses


def _diagnosis_key(dx: Any) -> str:
    if isinstance(dx, dict):
        label = dx.get("label_display") or dx.get("label") or dx.get("name") or ""
    else:
        label = getattr(dx, "label_display", None) or getattr(dx, "label", None) or getattr(dx, "name", None) or ""
    return str(label).strip().lower()


def prioritize_linked_diagnoses(candidates: list[Any]) -> list[Any]:
    """Display-level dedupe: keep linked/composite diagnoses ahead of fragments."""
    rows = list(candidates or [])
    keys = {_diagnosis_key(candidate) for candidate in rows}

    has_diabetic_ckd = "type 2 diabetes mellitus with diabetic chronic kidney disease" in keys
    has_diabetic_albuminuria = "type 2 diabetes mellitus with albuminuria" in keys
    has_staged_ckd = any(key.startswith("chronic kidney disease, stage") for key in keys)
    has_severe_albuminuria = "severely increased albuminuria" in keys
    has_severe_cac = "severe subclinical coronary atherosclerosis" in keys
    has_severe_tg = "severe hypertriglyceridemia" in keys
    has_prediabetes = "prediabetes" in keys

    suppressed = set()
    if has_diabetic_ckd or has_diabetic_albuminuria:
        suppressed.add("type 2 diabetes mellitus")
    if has_diabetic_ckd:
        suppressed.add("type 2 diabetes mellitus with albuminuria")
        suppressed.add("albuminuria")
    if has_staged_ckd:
        suppressed.add("chronic kidney disease")
    if has_severe_albuminuria:
        suppressed.add("albuminuria")
    if has_severe_cac:
        suppressed.add("subclinical coronary atherosclerosis")
    if has_severe_tg:
        suppressed.add("hypertriglyceridemia")
    if has_prediabetes:
        suppressed.add("hyperglycemia")

    order = {
        "clinical ascvd": 0,
        "severe subclinical coronary atherosclerosis": 1,
        "subclinical coronary atherosclerosis": 2,
        "type 2 diabetes mellitus with diabetic chronic kidney disease": 3,
        "type 2 diabetes mellitus with albuminuria": 4,
        "chronic kidney disease, stage 5": 5,
        "chronic kidney disease, stage 4": 6,
        "chronic kidney disease, stage 3b": 7,
        "chronic kidney disease, stage 3a": 8,
        "severely increased albuminuria": 9,
        "albuminuria": 10,
        "type 2 diabetes mellitus": 11,
        "severe hypercholesterolemia": 12,
        "elevated apob": 13,
        "severe hypertriglyceridemia": 14,
        "hypertriglyceridemia": 15,
    }

    visible = [candidate for candidate in rows if _diagnosis_key(candidate) not in suppressed]
    return sorted(visible, key=lambda candidate: order.get(_diagnosis_key(candidate), 50))


def _result_kdigo_stage(out: Any) -> str:
    if hasattr(out, "kdigo_stage"):
        return str(getattr(out, "kdigo_stage") or "").strip()
    if isinstance(out, dict):
        return str(out.get("kdigo_stage") or out.get("kdigoStage") or "").strip()
    return ""


def _result_albuminuria_stage(out: Any) -> str:
    if hasattr(out, "albuminuria_stage"):
        return str(getattr(out, "albuminuria_stage") or "").strip()
    if isinstance(out, dict):
        return str(out.get("albuminuria_stage") or out.get("albuminuriaStage") or "").strip()
    return ""


def _compact_display_label(label: str, out: Any) -> str:
    key = str(label or "").strip().lower()
    kdigo_stage = _result_kdigo_stage(out)
    albuminuria_stage = _result_albuminuria_stage(out)
    has_albuminuria = albuminuria_stage in {"A2", "A3"}

    if key == "severe subclinical coronary atherosclerosis":
        return "Severe subclinical coronary atherosclerosis / high CAC burden"

    if key == "type 2 diabetes mellitus with diabetic chronic kidney disease":
        if kdigo_stage:
            suffix = " and albuminuria" if has_albuminuria else ""
            return f"Type 2 diabetes mellitus with CKD {kdigo_stage}{suffix}"
        return (
            "Type 2 diabetes mellitus with CKD and albuminuria"
            if has_albuminuria
            else "Type 2 diabetes mellitus with CKD"
        )

    if key == "elevated apob":
        return "Elevated ApoB / atherogenic particle burden"

    return str(label or "").strip()


def prepare_diagnosis_display_entries(out: Any) -> list[dict[str, Any]]:
    """Normalize, dedupe, and compact diagnosis labels for UI/EMR display only."""
    entries = prioritize_linked_diagnoses(normalize_diagnosis_entries(out))
    display_entries: list[dict[str, Any]] = []

    for entry in entries:
        if not isinstance(entry, dict):
            display_entries.append(entry)
            continue
        row = dict(entry)
        label = str(row.get("label_display") or row.get("label") or "").strip()
        compact_label = _compact_display_label(label, out)
        if compact_label:
            row["label_display"] = compact_label
        display_entries.append(row)

    return display_entries


def apply_confirmations(all_dx: list[dict[str, Any]], confirmed_ids: set[str] | list[str]) -> list[dict[str, Any]]:
    """Mark selected normalized diagnoses as clinician-confirmed for export."""
    confirmed_ids_set = {str(x) for x in (confirmed_ids or [])}
    upgraded: list[dict[str, Any]] = []
    for row in all_dx:
        if not isinstance(row, dict):
            continue
        d = dict(row)
        dx_id = str(d.get("dx_id") or "").strip()
        if dx_id and dx_id in confirmed_ids_set:
            d["status"] = "clinician_confirmed"
            d["icd10_confirmed"] = list(d.get("icd10_suggested") or [])
            d["hcc_confirmed"] = list(d.get("hcc_suggested") or [])
        elif str(d.get("status") or "") in {"suspected", "review_suggested"}:
            d["icd10_confirmed"] = []
            d["hcc_confirmed"] = []
        upgraded.append(d)
    return upgraded


def diagnosis_entry_id(dx: dict[str, Any]) -> str:
    """Return the stable UI identifier for a normalized diagnosis row."""
    return str(dx.get("dx_id") or dx.get("label_display") or dx.get("label") or "").strip()


def apply_diagnosis_review_overrides(
    all_dx: list[dict[str, Any]],
    *,
    accepted_ids: set[str] | list[str] | None = None,
    suppressed_ids: set[str] | list[str] | None = None,
    review_ids: set[str] | list[str] | None = None,
    include_suppressed: bool = False,
) -> list[dict[str, Any]]:
    """Apply UI-only diagnosis accept/review/suppress state.

    This does not change diagnostic thresholds; it only changes which normalized
    candidates are displayed/exported for the current clinician review session.
    """
    accepted = {str(x) for x in (accepted_ids or []) if str(x).strip()}
    suppressed = {str(x) for x in (suppressed_ids or []) if str(x).strip()}
    review = {str(x) for x in (review_ids or []) if str(x).strip()}

    rows: list[dict[str, Any]] = []
    for row in all_dx or []:
        if not isinstance(row, dict):
            continue
        dx_id = diagnosis_entry_id(row)
        d = dict(row)

        if dx_id in suppressed:
            d["status"] = "manually_suppressed"
            d["icd10_confirmed"] = []
            d["hcc_confirmed"] = []
            if include_suppressed:
                rows.append(d)
            continue

        if dx_id in accepted:
            d["status"] = "clinician_confirmed"
            d["icd10_confirmed"] = list(d.get("icd10_suggested") or d.get("icd10_confirmed") or [])
            d["hcc_confirmed"] = list(d.get("hcc_suggested") or d.get("hcc_confirmed") or [])
        elif dx_id in review:
            d["status"] = "review_suggested"
            d["icd10_confirmed"] = []
            d["hcc_confirmed"] = []

        rows.append(d)

    return rows


def split_diagnoses(all_dx: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split normalized diagnoses into confirmed and review-suggested groups."""
    confirmed_dx = [
        d
        for d in all_dx
        if str(d.get("status") or "") in {"confirmed", "clinician_confirmed", "confirmed_by_data"}
    ]
    suspected_dx = [
        d
        for d in all_dx
        if str(d.get("status") or "") in {"suspected", "review_suggested"}
    ]
    return confirmed_dx, suspected_dx


def build_confirmed_code_exports(confirmed_dx: list[dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    """Build ICD/HCC export payloads from confirmed diagnosis rows."""
    icd: list[str] = []
    hcc: list[str] = []
    for d in confirmed_dx:
        icd.extend(_extract_code_list(d.get("icd10_confirmed")))
        hcc.extend(_extract_code_list(d.get("hcc_confirmed")))
    return {
        "codes": {
            "icd10_confirmed": _dedupe(icd),
            "hcc_confirmed": _dedupe(hcc),
        }
    }


def build_assessment_section(
    confirmed_dx: list[dict[str, Any]],
    suspected_dx: list[dict[str, Any]],
    include_icd_confirmed: bool = False,
) -> str:
    """Render a plain-text assessment section from confirmed/review diagnoses."""
    section: list[str] = ["Assessment:"]
    if confirmed_dx:
        section.append("- Confirmed by data:")
        for d in confirmed_dx:
            label = str(d.get("label_display") or d.get("label") or "").strip()
            if not label:
                continue
            line = f"  - {label}"
            icd = " | ".join(_extract_code_list(d.get("icd10_confirmed")))
            if include_icd_confirmed and icd:
                line += f" (ICD: {icd})"
            section.append(line)
    if suspected_dx:
        section.append("- Review suggested:")
        for d in suspected_dx:
            label = str(d.get("label_display") or d.get("label") or "").strip()
            if label:
                section.append(f"  - {label}")
    return "\n".join(section)


def _diagnosis_context_keys(dx: dict[str, Any]) -> list[str]:
    dx_id = str(dx.get("dx_id") or "").strip().lower()
    label = str(dx.get("label_display") or dx.get("label") or "").strip().lower()

    if "dyslipidemia" in dx_id or any(x in label for x in ("hyperlipidemia", "hypercholesterolem", "hypertriglyceridem")):
        return ["ldl", "triglycerides", "tg", "hdl"]
    if "obesity" in dx_id or "overweight" in dx_id or "obesity" in label or "overweight" in label:
        return ["bmi"]
    if "ckd" in dx_id or "chronic kidney disease" in label:
        return ["egfr", "uacr"]
    return []


def _format_evidence_item(key: str, value: Any, unit: str = "") -> str:
    key_display = {
        "ldl": "LDL",
        "triglycerides": "TG",
        "tg": "TG",
        "hdl": "HDL",
        "bmi": "BMI",
        "egfr": "eGFR",
        "uacr": "UACR",
    }.get(str(key).strip().lower(), str(key).strip())
    value_s = str(value).strip()
    unit_s = str(unit).strip()
    return f"{key_display} {value_s}" + (f" {unit_s}" if unit_s else "")


def diagnosis_context_line(dx: dict[str, Any]) -> str:
    """Return a short evidence/context line for a normalized diagnosis row."""
    evidence = dx.get("evidence")
    if isinstance(evidence, dict):
        criteria_met = evidence.get("criteria_met")
        if isinstance(criteria_met, list) and criteria_met:
            parts: list[str] = []
            for item in criteria_met[:3]:
                if isinstance(item, dict):
                    key = str(item.get("label") or item.get("key") or item.get("criterion") or "").strip()
                    val = item.get("value")
                    unit = str(item.get("unit") or "").strip()
                    if key and val is not None:
                        parts.append(f"{key} {val}" + (f" {unit}" if unit else ""))
                    elif key:
                        parts.append(key)
                else:
                    txt = str(item).strip()
                    if txt:
                        parts.append(txt)
            if parts:
                return "Criteria: " + "; ".join(parts)

    ev = dx.get("ev")
    if isinstance(ev, list) and ev:
        wanted = set(_diagnosis_context_keys(dx))
        if wanted:
            parts: list[str] = []
            for item in ev:
                if not isinstance(item, dict):
                    continue
                key = str(item.get("key") or "").strip().lower()
                if key not in wanted:
                    continue
                value = item.get("value")
                if value is None or str(value).strip() == "":
                    continue
                parts.append(_format_evidence_item(key, value, str(item.get("unit") or "")))
                if len(parts) >= 2:
                    break
            if parts:
                return "; ".join(parts)

    for k in ("why", "reason", "rationale", "source"):
        txt = str(dx.get(k) or "").strip()
        if txt:
            return txt

    return ""
