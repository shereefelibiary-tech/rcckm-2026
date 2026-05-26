from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceBasis:
    """Describe the evidence and wording posture behind a rule."""

    rule_id: str
    domain: str
    evidence_basis: str
    default_strength_language: str
    patient_facing_allowed: bool = True
    emr_allowed: bool = True


EVIDENCE_MAP: dict[str, EvidenceBasis] = {
    "lipid_clinical_ascvd_secondary_prevention": EvidenceBasis(
        rule_id="lipid_clinical_ascvd_secondary_prevention",
        domain="lipid",
        evidence_basis="Established ASCVD is treated using secondary-prevention lipid targets; PREVENT is not used to de-risk therapy.",
        default_strength_language="recommended",
    ),
    "lipid_ldl_ge_190_or_fh": EvidenceBasis(
        rule_id="lipid_ldl_ge_190_or_fh",
        domain="lipid",
        evidence_basis="LDL-C >=190 mg/dL or suspected FH follows severe hypercholesterolemia/FH treatment pathway independent of PREVENT de-risking.",
        default_strength_language="recommended",
    ),
    "lipid_prevent_ascvd_ge_20": EvidenceBasis(
        rule_id="lipid_prevent_ascvd_ge_20",
        domain="lipid",
        evidence_basis="PREVENT-ASCVD 10-year risk >=20% supports high-intensity statin discussion in primary prevention.",
        default_strength_language="recommended",
    ),
    "lipid_prevent_ascvd_7_5_to_20": EvidenceBasis(
        rule_id="lipid_prevent_ascvd_7_5_to_20",
        domain="lipid",
        evidence_basis="PREVENT-ASCVD 10-year risk 7.5% to <20% generally favors moderate-intensity statin therapy.",
        default_strength_language="reasonable",
    ),
    "lipid_prevent_ascvd_5_to_7_5_with_enhancers": EvidenceBasis(
        rule_id="lipid_prevent_ascvd_5_to_7_5_with_enhancers",
        domain="lipid",
        evidence_basis="PREVENT-ASCVD 10-year risk 5% to <7.5% supports moderate-intensity statin discussion when risk enhancers are present.",
        default_strength_language="reasonable",
    ),
    "lipid_prevent_ascvd_5_to_7_5_no_enhancers": EvidenceBasis(
        rule_id="lipid_prevent_ascvd_5_to_7_5_no_enhancers",
        domain="lipid",
        evidence_basis="PREVENT-ASCVD 10-year risk 5% to <7.5% without major enhancers is a preference-sensitive lipid discussion zone.",
        default_strength_language="consider",
    ),
    "lipid_prevent_ascvd_3_to_5_with_major_enhancers": EvidenceBasis(
        rule_id="lipid_prevent_ascvd_3_to_5_with_major_enhancers",
        domain="lipid",
        evidence_basis="PREVENT-ASCVD 10-year risk 3% to <5% is an early discussion band; lipid-lowering is conditional on longer-term risk and major risk enhancers.",
        default_strength_language="consider",
    ),
    "lipid_prevent_ascvd_3_to_5_no_enhancers": EvidenceBasis(
        rule_id="lipid_prevent_ascvd_3_to_5_no_enhancers",
        domain="lipid",
        evidence_basis="PREVENT-ASCVD 10-year risk 3% to <5% without meaningful enhancers remains lifestyle-focused with reassessment.",
        default_strength_language="defer",
    ),
    "lipid_prevent_ascvd_lt_3": EvidenceBasis(
        rule_id="lipid_prevent_ascvd_lt_3",
        domain="lipid",
        evidence_basis="PREVENT-ASCVD 10-year risk <3% is lifestyle-focused unless hard indications or major risk-enhancing features are present.",
        default_strength_language="defer",
    ),
    "prevent_lipid_10yr_ge20": EvidenceBasis(
        rule_id="prevent_lipid_10yr_ge20",
        domain="lipid",
        evidence_basis="10-year PREVENT-ASCVD risk >=20% supports high-intensity statin discussion in primary prevention.",
        default_strength_language="recommended",
    ),
    "prevent_lipid_10yr_7_5to20": EvidenceBasis(
        rule_id="prevent_lipid_10yr_7_5to20",
        domain="lipid",
        evidence_basis="10-year PREVENT-ASCVD risk 7.5% to <20% generally favors moderate-intensity statin therapy.",
        default_strength_language="reasonable",
    ),
    "prevent_lipid_10yr_5to7_5_with_enhancer": EvidenceBasis(
        rule_id="prevent_lipid_10yr_5to7_5_with_enhancer",
        domain="lipid",
        evidence_basis="10-year PREVENT-ASCVD risk 5% to <7.5% supports moderate-intensity statin discussion when risk enhancers are present.",
        default_strength_language="reasonable",
    ),
    "prevent_lipid_10yr_5to7_5_no_enhancer": EvidenceBasis(
        rule_id="prevent_lipid_10yr_5to7_5_no_enhancer",
        domain="lipid",
        evidence_basis="10-year PREVENT-ASCVD risk 5% to <7.5% without major enhancers is a preference-sensitive lipid discussion zone.",
        default_strength_language="consider",
    ),
    "prevent_lipid_10yr_3to5_30yr_elevated_with_enhancer": EvidenceBasis(
        rule_id="prevent_lipid_10yr_3to5_30yr_elevated_with_enhancer",
        domain="lipid",
        evidence_basis="Low short-term PREVENT-ASCVD risk with elevated 30-year risk and major enhancers supports shared decision-making; statin therapy is not automatic.",
        default_strength_language="consider",
    ),
    "prevent_lipid_10yr_3to5_30yr_high_with_enhancer": EvidenceBasis(
        rule_id="prevent_lipid_10yr_3to5_30yr_high_with_enhancer",
        domain="lipid",
        evidence_basis="Low short-term PREVENT-ASCVD risk with high 30-year risk and major enhancers supports a stronger shared decision about moderate-intensity statin therapy.",
        default_strength_language="reasonable",
    ),
    "prevent_lipid_10yr_3to5_30yr_high_no_enhancer": EvidenceBasis(
        rule_id="prevent_lipid_10yr_3to5_30yr_high_no_enhancer",
        domain="lipid",
        evidence_basis="Low short-term PREVENT-ASCVD risk with high 30-year risk but no major enhancers supports lifestyle intensity and risk-enhancer review, not automatic statin therapy.",
        default_strength_language="consider",
    ),
    "prevent_lipid_10yr_3to5_30yr_low_no_enhancer": EvidenceBasis(
        rule_id="prevent_lipid_10yr_3to5_30yr_low_no_enhancer",
        domain="lipid",
        evidence_basis="10-year PREVENT-ASCVD risk 3% to <5% without elevated 30-year risk or meaningful enhancers remains lifestyle-focused.",
        default_strength_language="defer",
    ),
    "prevent_lipid_10yr_lt3_30yr_low_lifestyle": EvidenceBasis(
        rule_id="prevent_lipid_10yr_lt3_30yr_low_lifestyle",
        domain="lipid",
        evidence_basis="10-year PREVENT-ASCVD risk <3% with low 30-year risk is lifestyle-focused unless hard indications exist.",
        default_strength_language="defer",
    ),
    "prevent_lipid_10yr_lt3_30yr_elevated_no_enhancer": EvidenceBasis(
        rule_id="prevent_lipid_10yr_lt3_30yr_elevated_no_enhancer",
        domain="lipid",
        evidence_basis="Very low 10-year PREVENT-ASCVD risk with elevated/high 30-year risk but no major enhancers supports lifestyle intensity and data completion, not automatic statin therapy.",
        default_strength_language="consider",
    ),
    "prevent_lipid_10yr_lt3_30yr_elevated_with_enhancer": EvidenceBasis(
        rule_id="prevent_lipid_10yr_lt3_30yr_elevated_with_enhancer",
        domain="lipid",
        evidence_basis="Very low 10-year PREVENT-ASCVD risk with elevated 30-year risk and major enhancers supports earlier prevention discussion; medication depends on enhancer severity.",
        default_strength_language="consider",
    ),
    "prevent_lipid_10yr_lt3_30yr_high_with_enhancer": EvidenceBasis(
        rule_id="prevent_lipid_10yr_lt3_30yr_high_with_enhancer",
        domain="lipid",
        evidence_basis="Very low 10-year PREVENT-ASCVD risk with high 30-year risk and major enhancers may support earlier moderate-intensity statin discussion.",
        default_strength_language="consider",
    ),
    "prevent_lipid_plaque_override": EvidenceBasis(
        rule_id="prevent_lipid_plaque_override",
        domain="lipid",
        evidence_basis="Plaque presence shifts decision-making beyond risk estimation alone; CAC/plaque supports lipid-lowering despite low calculated short-term risk.",
        default_strength_language="reasonable",
    ),
    "prevent_lipid_ldl_190_override": EvidenceBasis(
        rule_id="prevent_lipid_ldl_190_override",
        domain="lipid",
        evidence_basis="LDL-C >=190 mg/dL follows severe hypercholesterolemia treatment pathway independent of PREVENT de-risking.",
        default_strength_language="recommended",
    ),
    "prevent_lipid_diabetes_override": EvidenceBasis(
        rule_id="prevent_lipid_diabetes_override",
        domain="lipid",
        evidence_basis="Diabetes age 40-75 with LDL-C >=70 mg/dL supports statin therapy independent of low calculated PREVENT risk.",
        default_strength_language="recommended",
    ),
    "lipid_borderline_with_albuminuria": EvidenceBasis(
        rule_id="lipid_borderline_with_albuminuria",
        domain="lipid",
        evidence_basis="Borderline/intermediate PREVENT-ASCVD risk with albuminuria/CKM risk enhancers supports moderate-intensity statin discussion.",
        default_strength_language="reasonable",
    ),
    "lipid_lifetime_trajectory": EvidenceBasis(
        rule_id="lipid_lifetime_trajectory",
        domain="lipid",
        evidence_basis="Adults age 30-59 with elevated 30-year PREVENT-ASCVD risk and atherogenic burden may warrant earlier prevention discussion.",
        default_strength_language="reasonable",
    ),
    "cac_young_age_defer": EvidenceBasis(
        rule_id="cac_young_age_defer",
        domain="diagnostics",
        evidence_basis="CAC is not routinely used below usual age thresholds; use only when results would change management.",
        default_strength_language="consider",
    ),
    "cac_plaque_clarification": EvidenceBasis(
        rule_id="cac_plaque_clarification",
        domain="diagnostics",
        evidence_basis="CAC can reclassify plaque burden when treatment decision or intensity remains uncertain.",
        default_strength_language="consider",
    ),
    "cac_score_ge_100_plaque_burden": EvidenceBasis(
        rule_id="cac_score_ge_100_plaque_burden",
        domain="plaque",
        evidence_basis="CAC >=100 identifies plaque burden supporting LDL-C <70 and non-HDL-C <100 treatment targets.",
        default_strength_language="recommended",
    ),
    "kidney_albuminuria_confirm_persistence": EvidenceBasis(
        rule_id="kidney_albuminuria_confirm_persistence",
        domain="kidney",
        evidence_basis="UACR >=30 mg/g is an albuminuria signal; persistence should be confirmed unless already documented.",
        default_strength_language="recommended",
    ),
    "kidney_ace_arb_albuminuria_bp": EvidenceBasis(
        rule_id="kidney_ace_arb_albuminuria_bp",
        domain="kidney",
        evidence_basis="Albuminuria with hypertension supports ACEi/ARB and BP-directed kidney protection when tolerated.",
        default_strength_language="recommended",
    ),
    "kidney_sglt2_uacr_ge_200_egfr_ge_20": EvidenceBasis(
        rule_id="kidney_sglt2_uacr_ge_200_egfr_ge_20",
        domain="kidney",
        evidence_basis="eGFR >=20 with UACR >=200 mg/g, diabetes with CKD, or heart failure supports SGLT2 kidney/cardiovascular protection if no contraindication.",
        default_strength_language="recommended",
    ),
    "kidney_sglt2_albuminuria_conditional": EvidenceBasis(
        rule_id="kidney_sglt2_albuminuria_conditional",
        domain="kidney",
        evidence_basis="Albuminuria 30-199 mg/g without diabetes or HF supports confirmation and individualized SGLT2 consideration rather than automatic initiation.",
        default_strength_language="consider",
    ),
    "bp_albuminuria_goal_130_80": EvidenceBasis(
        rule_id="bp_albuminuria_goal_130_80",
        domain="BP",
        evidence_basis="Albuminuria/CKM risk with elevated or treated BP supports BP treatment toward <130/80 when tolerated.",
        default_strength_language="recommended",
    ),
    "glycemia_a1c_ge_7": EvidenceBasis(
        rule_id="glycemia_a1c_ge_7",
        domain="glycemia",
        evidence_basis="A1c >=7% or diabetes context supports glycemic optimization as part of CKM prevention.",
        default_strength_language="recommended",
    ),
    "tg_ge_500_pancreatitis": EvidenceBasis(
        rule_id="tg_ge_500_pancreatitis",
        domain="lipid",
        evidence_basis="Triglycerides >=500 mg/dL require pancreatitis-risk reduction and secondary-cause evaluation.",
        default_strength_language="recommended",
    ),
    "aspirin_primary_prevention_not_indicated": EvidenceBasis(
        rule_id="aspirin_primary_prevention_not_indicated",
        domain="aspirin",
        evidence_basis="Routine aspirin is generally not indicated for primary prevention without individualized benefit/bleeding risk review.",
        default_strength_language="defer",
    ),
    "diagnostic_completion": EvidenceBasis(
        rule_id="diagnostic_completion",
        domain="diagnostics",
        evidence_basis="Missing ApoB, Lp(a), UACR, CAC, or hsCRP may clarify risk when clinically relevant.",
        default_strength_language="consider",
    ),
}


def get_evidence_basis(rule_id: str) -> EvidenceBasis:
    """Return an evidence mapping, falling back to diagnostic completion."""
    return EVIDENCE_MAP.get(rule_id, EVIDENCE_MAP["diagnostic_completion"])
