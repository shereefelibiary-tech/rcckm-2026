from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Parseability = Literal["high", "medium", "low"]
ClinicalImpact = Literal["high", "medium", "low"]
Priority = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class WorksheetFieldMetadata:
    field_id: str
    label: str
    default_visible: bool
    parseable_from_smartphrase: Parseability
    clinical_impact: ClinicalImpact
    affects: tuple[str, ...]
    manual_review_priority: Priority
    advanced_only: bool = False
    remove_from_default_reason: str = ""


HIGH_IMPACT_AFFECTS = {
    "risk_level",
    "prevent",
    "ckm_stage",
    "plaque",
    "lipid_targets",
    "lipid_action",
    "kidney_action",
    "aspirin_action",
    "diagnosis_coding",
    "confidence",
    "roadmap",
    "emr",
}


def _field(
    field_id: str,
    label: str,
    *,
    default_visible: bool,
    parseable: Parseability,
    impact: ClinicalImpact,
    affects: tuple[str, ...],
    priority: Priority,
    advanced_only: bool = False,
    reason: str = "",
) -> WorksheetFieldMetadata:
    return WorksheetFieldMetadata(
        field_id=field_id,
        label=label,
        default_visible=default_visible,
        parseable_from_smartphrase=parseable,
        clinical_impact=impact,
        affects=affects,
        manual_review_priority=priority,
        advanced_only=advanced_only,
        remove_from_default_reason=reason,
    )


WORKSHEET_FIELD_REGISTRY: dict[str, WorksheetFieldMetadata] = {
    "age": _field("age", "Age", default_visible=True, parseable="high", impact="high", affects=("prevent", "risk_level", "aspirin_action", "roadmap", "emr"), priority="high"),
    "sex": _field("sex", "Sex", default_visible=True, parseable="high", impact="high", affects=("prevent", "plaque", "risk_level", "roadmap", "emr"), priority="high"),
    "sbp": _field("sbp", "SBP", default_visible=True, parseable="high", impact="high", affects=("prevent", "kidney_action", "risk_level", "roadmap", "emr"), priority="high"),
    "dbp": _field("dbp", "DBP", default_visible=True, parseable="high", impact="high", affects=("kidney_action", "risk_level", "roadmap", "emr"), priority="high"),
    "bp_treated": _field("bp_treated", "BP treated", default_visible=True, parseable="medium", impact="medium", affects=("prevent", "kidney_action", "emr"), priority="medium"),
    "smoker": _field("smoker", "Smoking", default_visible=True, parseable="high", impact="high", affects=("prevent", "risk_level", "lipid_action", "roadmap", "emr"), priority="high"),
    "tc": _field("tc", "Total cholesterol", default_visible=True, parseable="high", impact="high", affects=("prevent", "lipid_targets", "confidence"), priority="high"),
    "ldl_c": _field("ldl_c", "LDL-C", default_visible=True, parseable="high", impact="high", affects=("lipid_targets", "lipid_action", "diagnosis_coding", "roadmap", "emr"), priority="high"),
    "hdl_c": _field("hdl_c", "HDL-C", default_visible=True, parseable="high", impact="high", affects=("prevent", "lipid_targets", "confidence"), priority="high"),
    "triglycerides": _field("triglycerides", "Triglycerides", default_visible=True, parseable="high", impact="high", affects=("lipid_action", "diagnosis_coding", "roadmap", "emr"), priority="high"),
    "apob": _field("apob", "ApoB", default_visible=True, parseable="medium", impact="high", affects=("risk_level", "lipid_targets", "lipid_action", "confidence", "roadmap", "emr"), priority="high"),
    "lp_a_value": _field("lp_a_value", "Lp(a)", default_visible=True, parseable="medium", impact="high", affects=("risk_level", "lipid_action", "confidence", "roadmap", "emr"), priority="high"),
    "lp_a_unit": _field("lp_a_unit", "Lp(a) unit", default_visible=True, parseable="medium", impact="medium", affects=("lipid_action", "confidence"), priority="medium"),
    "height_in": _field("height_in", "Height", default_visible=False, parseable="medium", impact="medium", affects=("confidence",), priority="medium", advanced_only=True, reason="Source measurement used to calculate BMI when BMI is missing; BMI is the default interpreted field."),
    "weight_lb": _field("weight_lb", "Weight", default_visible=False, parseable="medium", impact="medium", affects=("confidence",), priority="medium", advanced_only=True, reason="Source measurement used to calculate BMI when BMI is missing; BMI is the default interpreted field."),
    "bmi": _field("bmi", "BMI", default_visible=True, parseable="high", impact="medium", affects=("risk_level", "roadmap", "emr"), priority="medium"),
    "a1c": _field("a1c", "A1c", default_visible=True, parseable="high", impact="high", affects=("ckm_stage", "risk_level", "lipid_action", "diagnosis_coding", "roadmap", "emr"), priority="high"),
    "diabetes": _field("diabetes", "Diabetes", default_visible=True, parseable="high", impact="high", affects=("prevent", "ckm_stage", "lipid_action", "kidney_action", "diagnosis_coding", "roadmap", "emr"), priority="high"),
    "creatinine": _field("creatinine", "Creatinine", default_visible=False, parseable="medium", impact="medium", affects=("confidence",), priority="medium", advanced_only=True, reason="Creatinine is retained as parsed source data; default kidney interpretation uses eGFR and UACR."),
    "egfr": _field("egfr", "eGFR", default_visible=True, parseable="high", impact="high", affects=("ckm_stage", "risk_level", "kidney_action", "diagnosis_coding", "roadmap", "emr"), priority="high"),
    "uacr": _field("uacr", "UACR", default_visible=True, parseable="high", impact="high", affects=("ckm_stage", "risk_level", "kidney_action", "lipid_action", "diagnosis_coding", "roadmap", "emr"), priority="high"),
    "diabetes_duration_years": _field("diabetes_duration_years", "Diabetes duration", default_visible=False, parseable="medium", impact="medium", affects=("lipid_targets", "lipid_action", "confidence"), priority="medium", advanced_only=True, reason="Diabetes-specific enhancer; useful when present but not needed in main worksheet."),
    "diabetic_retinopathy": _field("diabetic_retinopathy", "Retinopathy", default_visible=False, parseable="medium", impact="medium", affects=("lipid_targets", "lipid_action", "confidence"), priority="medium", advanced_only=True, reason="Diabetes-specific enhancer; useful when present but not needed in main worksheet."),
    "diabetic_neuropathy": _field("diabetic_neuropathy", "Neuropathy", default_visible=False, parseable="medium", impact="medium", affects=("lipid_targets", "lipid_action", "confidence"), priority="medium", advanced_only=True, reason="Diabetes-specific enhancer; useful when present but not needed in main worksheet."),
    "abi": _field("abi", "ABI", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "confidence"), priority="medium", advanced_only=True, reason="Specialized vascular data; keep available but not in default worksheet."),
    "abi_lt_0_9": _field("abi_lt_0_9", "ABI <0.9 / PAD evidence", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "confidence"), priority="medium", advanced_only=True, reason="Diabetes/PAD-context vascular data; keep available only when diabetes context is present."),
    "cac": _field("cac", "CAC score", default_visible=True, parseable="high", impact="high", affects=("risk_level", "plaque", "lipid_targets", "lipid_action", "aspirin_action", "roadmap", "emr"), priority="high"),
    "cac_not_done": _field("cac_not_done", "CAC not performed", default_visible=True, parseable="medium", impact="medium", affects=("plaque", "confidence", "roadmap", "emr"), priority="medium"),
    "clinical_ascvd": _field("clinical_ascvd", "Clinical ASCVD", default_visible=True, parseable="medium", impact="high", affects=("risk_level", "lipid_targets", "lipid_action", "aspirin_action", "diagnosis_coding", "roadmap", "emr"), priority="high"),
    "clinical_ascvd_context": _field("clinical_ascvd_context", "Clinical ASCVD context", default_visible=False, parseable="medium", impact="high", affects=("risk_level", "lipid_targets", "aspirin_action", "diagnosis_coding", "emr"), priority="high", advanced_only=True, reason="Context supports secondary-prevention classification but is not a compact default control."),
    "family_history_premature_ascvd": _field("family_history_premature_ascvd", "Premature family history", default_visible=True, parseable="medium", impact="high", affects=("risk_level", "lipid_action", "roadmap", "emr"), priority="high"),
    "family_history_relationship": _field("family_history_relationship", "Family history relationship", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "emr"), priority="medium", advanced_only=True, reason="Shown only after a family-history signal is selected."),
    "family_history_event_type": _field("family_history_event_type", "Family history event", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "emr"), priority="medium", advanced_only=True, reason="Shown only after a family-history signal is selected."),
    "family_history_age_at_event": _field("family_history_age_at_event", "Family history age at event", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "emr"), priority="medium", advanced_only=True, reason="Shown only after a family-history signal is selected."),
    "hscrp": _field("hscrp", "hsCRP", default_visible=True, parseable="high", impact="medium", affects=("risk_level", "confidence", "roadmap", "emr"), priority="medium"),
    "osa": _field("osa", "OSA", default_visible=True, parseable="medium", impact="medium", affects=("risk_level", "roadmap", "emr"), priority="medium"),
    "masld": _field("masld", "MASLD", default_visible=True, parseable="medium", impact="medium", affects=("risk_level", "roadmap", "emr"), priority="medium"),
    "inflammatory_disease": _field("inflammatory_disease", "Other chronic inflammatory disease", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "confidence", "roadmap", "emr"), priority="medium", advanced_only=True, reason="Generic inflammatory capture overlaps with specific fields and belongs in advanced context."),
    "incidental_cac": _field("incidental_cac", "Incidental CAC on CT", default_visible=True, parseable="medium", impact="high", affects=("risk_level", "plaque", "lipid_action", "roadmap", "emr"), priority="high"),
    "incidental_cac_severity": _field("incidental_cac_severity", "Incidental CAC severity", default_visible=True, parseable="medium", impact="high", affects=("risk_level", "plaque", "lipid_action", "roadmap", "emr"), priority="high"),
    "inflammatory_arthritis": _field("inflammatory_arthritis", "Inflammatory arthritis", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "roadmap", "emr"), priority="medium", advanced_only=True, reason="Overlaps with specific inflammatory condition fields in the advanced inflammatory group."),
    "south_asian_ancestry": _field("south_asian_ancestry", "South Asian ancestry", default_visible=True, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "roadmap", "emr"), priority="medium"),
    "hiv": _field("hiv", "HIV", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "roadmap", "emr"), priority="medium", advanced_only=True, reason="Mapped risk enhancer, but lower-frequency and better kept in advanced context."),
    "stable_art": _field("stable_art", "Stable ART", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "emr"), priority="medium", advanced_only=True, reason="HIV treatment context; only meaningful when HIV is present."),
    "rheumatoid_arthritis": _field("rheumatoid_arthritis", "Rheumatoid arthritis", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "roadmap", "emr"), priority="medium", advanced_only=True, reason="Specific inflammatory condition; generic inflammatory disease remains visible."),
    "sle": _field("sle", "SLE", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "roadmap", "emr"), priority="medium", advanced_only=True, reason="Specific inflammatory condition; generic inflammatory disease remains visible."),
    "psoriasis": _field("psoriasis", "Psoriasis", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "roadmap", "emr"), priority="medium", advanced_only=True, reason="Specific inflammatory condition; generic inflammatory disease remains visible."),
    "ibd": _field("ibd", "IBD", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "roadmap", "emr"), priority="medium", advanced_only=True, reason="Specific inflammatory condition; generic inflammatory disease remains visible."),
    "filipino_ancestry": _field("filipino_ancestry", "Filipino ancestry", default_visible=True, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "roadmap", "emr"), priority="medium"),
    "higher_risk_ancestry_context": _field("higher_risk_ancestry_context", "Other ancestry/context", default_visible=False, parseable="low", impact="medium", affects=("risk_level", "lipid_action", "emr"), priority="low", advanced_only=True, reason="Free-text context is manual and should not clutter the default worksheet."),
    "suspected_fh_hefh": _field("suspected_fh_hefh", "Suspected FH / HeFH", default_visible=False, parseable="medium", impact="high", affects=("risk_level", "lipid_targets", "lipid_action", "diagnosis_coding", "emr"), priority="high", advanced_only=True, reason="High-impact context, but LDL-C >=190 remains the default severe hypercholesterolemia trigger."),
    "active_cancer": _field("active_cancer", "Active cancer", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "roadmap", "emr"), priority="low", advanced_only=True, reason="Contextual risk marker; keep optional rather than default."),
    "cancer_survivor": _field("cancer_survivor", "Cancer survivor", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "roadmap", "emr"), priority="low", advanced_only=True, reason="Contextual risk marker; keep optional rather than default."),
    "cancer_life_expectancy_gt_2y": _field("cancer_life_expectancy_gt_2y", "Life expectancy >2y", default_visible=False, parseable="low", impact="medium", affects=("risk_level", "emr"), priority="low", advanced_only=True, reason="Manual cancer-context qualifier; not a default worksheet item."),
    "breast_arterial_calcification": _field("breast_arterial_calcification", "Breast arterial calcification", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "plaque", "lipid_action", "roadmap", "emr"), priority="medium", advanced_only=True, reason="Contextual imaging risk marker; CAC remains the primary default plaque input."),
    "cac_percentile": _field("cac_percentile", "CAC percentile", default_visible=False, parseable="medium", impact="medium", affects=("plaque", "confidence", "emr"), priority="medium", advanced_only=True, reason="Contextual only; absolute CAC score drives default plaque interpretation."),
    "zip_code": _field("zip_code", "ZIP / SDOH support", default_visible=False, parseable="low", impact="low", affects=("confidence",), priority="low", advanced_only=True, reason="Manual SDOH support field; does not drive core RCCKM logic."),
    "neighborhood_sdoh_context": _field("neighborhood_sdoh_context", "Neighborhood context", default_visible=False, parseable="low", impact="low", affects=("confidence",), priority="low", advanced_only=True, reason="Manual context field; does not drive core RCCKM logic."),
    "early_menopause": _field("early_menopause", "Early menopause", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "roadmap", "emr"), priority="medium", advanced_only=True, reason="Actionable reproductive enhancer, but shown only for applicable patients in an expander."),
    "menopause_age": _field("menopause_age", "Menopause age", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "emr"), priority="medium", advanced_only=True, reason="Actionable reproductive enhancer, but shown only for applicable patients in an expander."),
    "premature_menopause": _field("premature_menopause", "Premature menopause", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "emr"), priority="medium", advanced_only=True, reason="Derived from menopause age when available."),
    "preeclampsia": _field("preeclampsia", "Preeclampsia", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "roadmap", "emr"), priority="medium", advanced_only=True, reason="Actionable reproductive enhancer, but shown only for applicable patients in an expander."),
    "gestational_hypertension": _field("gestational_hypertension", "Gestational HTN", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "roadmap", "emr"), priority="medium", advanced_only=True, reason="Actionable reproductive enhancer, but shown only for applicable patients in an expander."),
    "gestational_diabetes": _field("gestational_diabetes", "Gestational diabetes", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "roadmap", "emr"), priority="medium", advanced_only=True, reason="Actionable reproductive enhancer, but shown only for applicable patients in an expander."),
    "preterm_delivery": _field("preterm_delivery", "Preterm delivery", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "roadmap", "emr"), priority="medium", advanced_only=True, reason="Actionable reproductive enhancer, but shown only for applicable patients in an expander."),
    "small_for_gestational_age": _field("small_for_gestational_age", "SGA infant", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "roadmap", "emr"), priority="medium", advanced_only=True, reason="Actionable reproductive enhancer, but shown only for applicable patients in an expander."),
    "recurrent_pregnancy_loss": _field("recurrent_pregnancy_loss", "Recurrent loss", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "roadmap", "emr"), priority="medium", advanced_only=True, reason="Actionable reproductive enhancer, but shown only for applicable patients in an expander."),
    "pcos_or_irregular_menses": _field("pcos_or_irregular_menses", "PCOS / irregular menses", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "roadmap", "emr"), priority="medium", advanced_only=True, reason="Actionable reproductive enhancer, but shown only for applicable patients in an expander."),
    "early_menarche": _field("early_menarche", "Early menarche", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "roadmap", "emr"), priority="medium", advanced_only=True, reason="Actionable reproductive enhancer, but shown only for applicable patients in an expander."),
    "menarche_age": _field("menarche_age", "Menarche age", default_visible=False, parseable="medium", impact="medium", affects=("risk_level", "lipid_action", "emr"), priority="medium", advanced_only=True, reason="Actionable reproductive enhancer, but shown only for applicable patients in an expander."),
    "lipid_lowering": _field("lipid_lowering", "Prescription lipid-lowering therapy", default_visible=True, parseable="high", impact="high", affects=("lipid_action", "lipid_targets", "emr"), priority="high"),
    "medications_raw": _field("medications_raw", "Medication list", default_visible=True, parseable="high", impact="high", affects=("lipid_action", "kidney_action", "aspirin_action", "confidence", "emr"), priority="high"),
    "dm_meds_raw": _field("dm_meds_raw", "Diabetes meds", default_visible=True, parseable="high", impact="medium", affects=("kidney_action", "roadmap", "emr"), priority="medium"),
    "statin_intensity": _field("statin_intensity", "Statin intensity", default_visible=True, parseable="medium", impact="high", affects=("lipid_action", "lipid_targets", "emr"), priority="high"),
    "statin_intolerance": _field("statin_intolerance", "Statin intolerance", default_visible=True, parseable="medium", impact="high", affects=("lipid_action", "emr"), priority="high"),
    "sglt2": _field("sglt2", "SGLT2", default_visible=True, parseable="high", impact="high", affects=("kidney_action", "roadmap", "emr"), priority="high"),
    "glp1": _field("glp1", "GLP1", default_visible=True, parseable="high", impact="medium", affects=("roadmap", "emr"), priority="medium"),
    "ace_arb": _field("ace_arb", "ACE/ARB", default_visible=True, parseable="high", impact="high", affects=("kidney_action", "roadmap", "emr"), priority="high"),
}


def should_show_field_in_default_worksheet(field_metadata: WorksheetFieldMetadata) -> bool:
    if field_metadata.advanced_only:
        return False
    if field_metadata.clinical_impact == "high":
        return True
    return (
        field_metadata.parseable_from_smartphrase in {"high", "medium"}
        and field_metadata.clinical_impact in {"medium", "high"}
    )


def audit_worksheet_fields() -> dict[str, list[str]]:
    default_low_impact: list[str] = []
    hidden_high_impact: list[str] = []
    manual_only_no_output: list[str] = []
    parseable_not_shown: list[str] = []
    visibility_mismatches: list[str] = []

    for field_id, metadata in WORKSHEET_FIELD_REGISTRY.items():
        expected_default = should_show_field_in_default_worksheet(metadata)
        if metadata.default_visible and metadata.clinical_impact == "low":
            default_low_impact.append(field_id)
        if not metadata.default_visible and metadata.clinical_impact == "high" and not metadata.advanced_only:
            hidden_high_impact.append(field_id)
        if metadata.parseable_from_smartphrase == "low" and metadata.clinical_impact == "low" and not metadata.affects:
            manual_only_no_output.append(field_id)
        if metadata.parseable_from_smartphrase in {"high", "medium"} and not metadata.default_visible and not metadata.advanced_only:
            parseable_not_shown.append(field_id)
        if metadata.default_visible != expected_default:
            visibility_mismatches.append(field_id)

    return {
        "default_low_impact": default_low_impact,
        "hidden_high_impact": hidden_high_impact,
        "missing_metadata": [],
        "manual_only_no_output": manual_only_no_output,
        "parseable_not_shown": parseable_not_shown,
        "visibility_mismatches": visibility_mismatches,
    }
