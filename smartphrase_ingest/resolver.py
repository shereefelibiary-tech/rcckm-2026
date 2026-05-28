from __future__ import annotations

from core.patient import Patient
from smartphrase_ingest.models import ExtractedCandidate, ParsedPatientDraft


REQUIRED_REVIEW_FIELDS = (
    ("apob", "ApoB missing"),
    ("lp_a_value", "Lp(a) missing"),
    ("uacr", "UACR missing"),
    ("cac", "CAC missing"),
    ("premature_fhx_ascvd", "Family history unknown"),
)


def _best(candidates: list[ExtractedCandidate]) -> ExtractedCandidate | None:
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.confidence, reverse=True)[0]


def _resolve_bp(candidates: list[ExtractedCandidate], draft: ParsedPatientDraft) -> None:
    if not candidates:
        return
    dated = [item for item in candidates if item.date]
    selected = dated[0] if dated else _best(candidates)
    if not selected:
        return
    sbp, dbp = selected.value
    draft.resolved["sbp"] = sbp
    draft.resolved["dbp"] = dbp
    if len(candidates) > 1:
        draft.review_flags.append("Multiple BP readings detected; most recent selected")


def _resolve_diabetes_from_a1c(draft: ParsedPatientDraft) -> None:
    if "diabetes" in draft.resolved:
        return
    a1c = draft.resolved.get("a1c")
    if a1c is None:
        return
    try:
        value = float(a1c)
    except (TypeError, ValueError):
        return
    draft.resolved["diabetes"] = value >= 6.5
    if 5.7 <= value < 6.5:
        draft.resolved["prediabetes_context"] = True
        draft.review_flags.append("A1c reference table ignored")


def resolve_candidates(draft: ParsedPatientDraft, *, confidence_threshold: float = 0.8) -> ParsedPatientDraft:
    """Resolve extracted candidates into deterministic worksheet-ready fields."""
    for field, candidates in draft.candidates.items():
        if field == "bp_pair":
            continue
        selected = _best([item for item in candidates if item.confidence >= confidence_threshold])
        if selected:
            draft.resolved[field] = selected.value
            if field == "bmi" and "calculated" in selected.reason.lower():
                draft.review_flags.append("BMI parsed from calculated text")
        elif candidates:
            draft.review_flags.append(f"{field} uncertain")

    _resolve_bp(draft.candidates.get("bp_pair", []), draft)
    _resolve_diabetes_from_a1c(draft)

    for field, message in REQUIRED_REVIEW_FIELDS:
        if field not in draft.resolved:
            draft.missing_fields.append(field)
            draft.review_flags.append(message)

    return draft


def to_patient(parsed_draft: ParsedPatientDraft, *, confidence_threshold: float = 0.8) -> Patient:
    """Convert resolved high-confidence draft values to a Patient object."""
    values = parsed_draft.resolved
    return Patient(
        age=values.get("age"),
        sex=values.get("sex"),
        sbp=values.get("sbp"),
        dbp=values.get("dbp"),
        bp_treated=values.get("bp_treated", False),
        tc=values.get("tc"),
        ldl_c=values.get("ldl_c"),
        hdl_c=values.get("hdl_c"),
        triglycerides=values.get("triglycerides"),
        apob=values.get("apob"),
        lp_a_value=values.get("lp_a_value"),
        a1c=values.get("a1c"),
        diabetes=values.get("diabetes", False),
        bmi=values.get("bmi"),
        egfr=values.get("egfr"),
        uacr=values.get("uacr"),
        cac=values.get("cac"),
        smoker=values.get("smoker", False),
        smoking=values.get("smoker", False),
        family_history_premature_ascvd=values.get("premature_fhx_ascvd"),
        premature_fhx_ascvd=values.get("premature_fhx_ascvd"),
        ace_arb=values.get("ace_arb", False),
        lipid_lowering=values.get("lipid_lowering", False),
        sglt2=values.get("sglt2", False),
        glp1=values.get("glp1", False),
    )
