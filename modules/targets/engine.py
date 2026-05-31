from core.results import TargetResult
from modules.occult_risk import has_occult_lipid_discussion_path


LDL_TARGET_PRIMARY_PREVENTION_DEFAULT = 100
LDL_TARGET_HIGH_RISK_PRIMARY_PREVENTION = 70
LDL_TARGET_SECONDARY_PREVENTION_MINIMUM = 70
LDL_TARGET_VERY_HIGH_RISK_ASCVD = 55

NON_HDL_TARGET_PRIMARY_PREVENTION_DEFAULT = 130
NON_HDL_TARGET_HIGH_RISK_PRIMARY_PREVENTION = 100
NON_HDL_TARGET_SECONDARY_PREVENTION_MINIMUM = 100
NON_HDL_TARGET_VERY_HIGH_RISK_ASCVD = 85

APOB_TARGET_PRIMARY_PREVENTION_DEFAULT = 90
APOB_TARGET_HIGH_RISK_PRIMARY_PREVENTION = 80
APOB_TARGET_SECONDARY_PREVENTION_MINIMUM = 80
APOB_TARGET_VERY_HIGH_RISK_ASCVD = 65

LIPID_TARGET_MODE = "preferred_modern"


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _age_40_to_75(patient):
    age = _num(getattr(patient, "age", None))
    return bool(age is not None and 40 <= age <= 75)


def _has_diabetes(patient):
    a1c = _num(getattr(patient, "a1c", None))
    return bool(getattr(patient, "diabetes", False)) or (
        a1c is not None and a1c >= 6.5
    )


def _has_ckd_stage_3_or_higher(patient):
    egfr = _num(getattr(patient, "egfr", None))
    return bool(getattr(patient, "ckd", False)) or (
        egfr is not None and egfr < 60
    )


def _has_ckd_or_albuminuria(patient):
    egfr = _num(getattr(patient, "egfr", None))
    uacr = _num(getattr(patient, "uacr", None))
    return bool(getattr(patient, "ckd", False)) or (
        egfr is not None and egfr < 60
    ) or (
        uacr is not None and uacr >= 30
    )


def _has_diabetes_risk_enhancer(patient):
    diabetes_duration = _num(getattr(patient, "diabetes_duration_years", None))
    abi = _num(getattr(patient, "abi", None))
    uacr = _num(getattr(patient, "uacr", None))
    egfr = _num(getattr(patient, "egfr", None))
    sbp = _num(getattr(patient, "sbp", None))
    triglycerides = _num(getattr(patient, "triglycerides", None))
    prevent_10y_ascvd = _num(getattr(patient, "prevent_10y_ascvd", None))
    return (
        (uacr is not None and uacr >= 30)
        or (egfr is not None and egfr < 60)
        or (diabetes_duration is not None and diabetes_duration >= 10)
        or bool(getattr(patient, "diabetic_retinopathy", False))
        or bool(getattr(patient, "diabetic_neuropathy", False))
        or bool(getattr(patient, "abi_lt_0_9", False))
        or (abi is not None and abi < 0.9)
        or bool(getattr(patient, "smoker", False))
        or bool(getattr(patient, "smoking", False))
        or bool(getattr(patient, "hypertension", False))
        or bool(getattr(patient, "bp_treated", False))
        or (sbp is not None and sbp >= 130)
        or (triglycerides is not None and triglycerides >= 150)
        or (prevent_10y_ascvd is not None and prevent_10y_ascvd >= 10)
    )


def _cac_zero_can_defer(patient):
    ldl_c = _num(getattr(patient, "ldl_c", None))
    age = _num(getattr(patient, "age", None))
    return not (
        (ldl_c is not None and ldl_c >= 190)
        or (_has_diabetes(patient) and age is not None and age > 40)
        or bool(getattr(patient, "smoker", False))
        or bool(getattr(patient, "smoking", False))
        or bool(getattr(patient, "premature_fhx_ascvd", False))
        or bool(getattr(patient, "family_history_premature_ascvd", False))
    )


def _has_severe_hypercholesterolemia_high_risk_feature(patient):
    cac = _num(getattr(patient, "cac", None))
    apob = _num(getattr(patient, "apob", None))
    return (
        (apob is not None and apob >= 140)
        or (cac is not None and cac > 0)
        or bool(getattr(patient, "premature_fhx_ascvd", False))
        or bool(getattr(patient, "family_history_premature_ascvd", False))
        or _has_diabetes(patient)
        or _has_ckd_stage_3_or_higher(patient)
        or bool(getattr(patient, "smoker", False))
        or bool(getattr(patient, "smoking", False))
    )


def _has_elevated_lpa(patient):
    value = _num(getattr(patient, "lp_a_value", None))
    unit = str(getattr(patient, "lp_a_unit", "") or "").strip().lower()
    return bool(
        value is not None
        and (
            (unit in {"nmol/l", "nmol"} and value >= 125)
            or (unit in {"mg/dl", "mg"} and value >= 50)
            or (not unit and value >= 125)
        )
    )


def _has_hypertension_context(patient):
    sbp = _num(getattr(patient, "sbp", None))
    dbp = _num(getattr(patient, "dbp", None))
    return bool(
        getattr(patient, "hypertension", False)
        or getattr(patient, "bp_treated", False)
        or (sbp is not None and sbp >= 130)
        or (dbp is not None and dbp >= 80)
    )


def _has_high_plaque_burden_context(patient):
    cac = _num(getattr(patient, "cac", None))
    return bool(cac is not None and cac >= 300)


def _has_recurrent_or_polyvascular_ascvd(patient):
    context = str(getattr(patient, "clinical_ascvd_context", "") or "").lower()
    vascular_beds = {
        "coronary": any(token in context for token in ("mi", "stemi", "nstemi", "acs", "pci", "cabg", "coronary")),
        "cerebrovascular": any(token in context for token in ("stroke", "tia", "cva", "carotid")),
        "peripheral": any(token in context for token in ("pad", "peripheral", "claudication")),
    }
    return bool(
        "recurrent" in context
        or "polyvascular" in context
        or "recent acs" in context
        or sum(1 for present in vascular_beds.values() if present) >= 2
    )


def is_very_high_risk_ascvd(patient, engine_context=None):
    """Return True for clinical ASCVD with at least one major high-risk feature."""
    if not bool(getattr(patient, "clinical_ascvd", False)):
        return False

    age = _num(getattr(patient, "age", None))
    ldl_c = _num(getattr(patient, "ldl_c", None))
    apob = _num(getattr(patient, "apob", None))
    high_risk_features = (
        _has_recurrent_or_polyvascular_ascvd(patient),
        _has_diabetes(patient),
        _has_ckd_or_albuminuria(patient),
        bool(ldl_c is not None and ldl_c >= 190),
        bool(getattr(patient, "suspected_fh_hefh", False)),
        bool(apob is not None and apob >= 130),
        _has_elevated_lpa(patient),
        _has_high_plaque_burden_context(patient),
        bool(getattr(patient, "smoker", False)) or bool(getattr(patient, "smoking", False)),
        _has_hypertension_context(patient),
        bool(age is not None and age >= 65),
        bool(getattr(patient, "heart_failure", False)),
        bool(getattr(patient, "inflammatory_disease", False)),
        bool(getattr(patient, "rheumatoid_arthritis", False)),
    )
    return any(high_risk_features)


def _secondary_prevention_target():
    return TargetResult(
        ldl_c_target=LDL_TARGET_SECONDARY_PREVENTION_MINIMUM,
        non_hdl_c_target=NON_HDL_TARGET_SECONDARY_PREVENTION_MINIMUM,
        apob_target=APOB_TARGET_SECONDARY_PREVENTION_MINIMUM,
        rationale=(
            "Clinical ASCVD: minimum secondary-prevention target. "
            "PREVENT should not be used to de-risk treatment in established ASCVD."
        ),
    )


def _very_high_risk_ascvd_target():
    if LIPID_TARGET_MODE == "conservative_us":
        return TargetResult(
            ldl_c_target=LDL_TARGET_SECONDARY_PREVENTION_MINIMUM,
            non_hdl_c_target=NON_HDL_TARGET_SECONDARY_PREVENTION_MINIMUM,
            apob_target=APOB_TARGET_SECONDARY_PREVENTION_MINIMUM,
            rationale=(
                "Secondary-prevention minimum target. Consider LDL-C <55 mg/dL "
                "given very-high-risk ASCVD features."
            ),
        )
    return TargetResult(
        ldl_c_target=LDL_TARGET_VERY_HIGH_RISK_ASCVD,
        non_hdl_c_target=NON_HDL_TARGET_VERY_HIGH_RISK_ASCVD,
        apob_target=APOB_TARGET_VERY_HIGH_RISK_ASCVD,
        rationale=(
            "Very-high-risk ASCVD target range. LDL-C <70 mg/dL is the minimum "
            "secondary-prevention threshold; <55 mg/dL is preferred given "
            "very-high-risk features."
        ),
    )


def _high_risk_primary_prevention_target(rationale):
    return TargetResult(
        ldl_c_target=LDL_TARGET_HIGH_RISK_PRIMARY_PREVENTION,
        non_hdl_c_target=NON_HDL_TARGET_HIGH_RISK_PRIMARY_PREVENTION,
        apob_target=APOB_TARGET_HIGH_RISK_PRIMARY_PREVENTION,
        rationale=rationale,
    )


def _primary_prevention_target(rationale):
    return TargetResult(
        ldl_c_target=LDL_TARGET_PRIMARY_PREVENTION_DEFAULT,
        non_hdl_c_target=NON_HDL_TARGET_PRIMARY_PREVENTION_DEFAULT,
        apob_target=APOB_TARGET_PRIMARY_PREVENTION_DEFAULT,
        rationale=rationale,
    )


def assign_lipid_targets(patient, engine_context=None):
    if patient.clinical_ascvd:
        if is_very_high_risk_ascvd(patient, engine_context):
            return _very_high_risk_ascvd_target()
        return _secondary_prevention_target()

    if patient.cac is not None and patient.cac >= 1000:
        return TargetResult(
            ldl_c_target=LDL_TARGET_VERY_HIGH_RISK_ASCVD,
            non_hdl_c_target=NON_HDL_TARGET_VERY_HIGH_RISK_ASCVD,
            apob_target=APOB_TARGET_VERY_HIGH_RISK_ASCVD,
            rationale=(
                "CAC >=1000: extreme subclinical plaque burden; treat toward very-high-risk target."
            ),
        )

    if patient.cac is not None and patient.cac >= 300:
        return _high_risk_primary_prevention_target(
            "CAC 300-999: severe subclinical plaque burden; treat toward high-risk target. Consider very-high-risk targets only when overall context supports intensification."
        )

    if patient.cac is not None and patient.cac >= 100:
        return _high_risk_primary_prevention_target(
            "CAC 100-299: significant subclinical plaque burden; treat toward high-risk target."
        )

    if (patient.ldl_c is not None and patient.ldl_c >= 190) or bool(getattr(patient, "suspected_fh_hefh", False)):
        if bool(getattr(patient, "suspected_fh_hefh", False)) or _has_severe_hypercholesterolemia_high_risk_feature(patient):
            return _high_risk_primary_prevention_target(
                "LDL-C >=190 / possible FH pathway with additional high-risk features: use high-risk lipid targets; CAC 0 should not de-risk therapy."
            )
        return _primary_prevention_target(
            "LDL-C >=190 severe hypercholesterolemia pathway: high-intensity therapy indicated; CAC 0 should not de-risk therapy."
        )

    if patient.cac is not None and 1 <= patient.cac <= 99:
        return _primary_prevention_target(
            "CAC 1-99: mild subclinical plaque burden; treat toward primary prevention goal."
        )

    if patient.cac == 0 and _cac_zero_can_defer(patient):
        return TargetResult(
            ldl_c_target=None,
            non_hdl_c_target=None,
            apob_target=None,
            rationale="CAC 0: no target assigned from plaque burden alone.",
        )

    if has_occult_lipid_discussion_path(patient, engine_context):
        return _primary_prevention_target(
            "Low 10-year PREVENT risk with clustered atherogenic and risk-enhancer burden: lipid-lowering discussion target range."
        )

    if _has_diabetes(patient) and _age_40_to_75(patient):
        if _has_diabetes_risk_enhancer(patient):
            return _high_risk_primary_prevention_target(
                "Diabetes age 40-75 with additional risk factors: high-intensity statin pathway; high-risk targets."
            )
        return _primary_prevention_target(
            "Diabetes age 40-75: moderate-intensity statin target range."
        )

    if _has_ckd_stage_3_or_higher(patient) and _age_40_to_75(patient):
        return _primary_prevention_target(
            "CKD stage 3 or higher age 40-75: moderate-intensity statin or statin plus ezetimibe pathway."
        )

    if patient.cac is None and patient.prevent_10y_ascvd is not None:
        prevent_value = float(patient.prevent_10y_ascvd)

        if prevent_value >= 10:
            return _high_risk_primary_prevention_target(
                "PREVENT 10-year ASCVD risk >=10% without CAC: treat toward high-risk primary prevention target."
            )

        if prevent_value >= 3:
            return _primary_prevention_target(
                "PREVENT 10-year ASCVD risk 3-<10% without CAC: treat toward primary prevention lipid target."
            )

        ldl_c = getattr(patient, "ldl_c", None)
        prevent_30y = getattr(patient, "prevent_30y_ascvd", None)
        if (ldl_c is not None and 160 <= ldl_c <= 189) or (
            prevent_30y is not None and prevent_30y >= 10
        ):
            return _primary_prevention_target(
                "Low 10-year PREVENT risk with LDL-C 160-189 or 30-year risk >=10%: moderate-intensity statin discussion pathway."
            )

        return TargetResult(
            ldl_c_target=None,
            non_hdl_c_target=None,
            apob_target=None,
            rationale=(
                "PREVENT 10-year ASCVD risk <3% without CAC: no formal lipid target assigned from PREVENT alone."
            ),
        )

    return TargetResult(
        ldl_c_target=None,
        non_hdl_c_target=None,
        rationale="No target pathway assigned yet.",
    )


def build_target_result(patient):
    return assign_lipid_targets(patient)
