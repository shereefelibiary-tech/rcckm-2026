from core.results import TargetResult


def _age_40_to_75(patient):
    try:
        age = float(patient.age)
    except (TypeError, ValueError):
        return False
    return 40 <= age <= 75


def _has_diabetes(patient):
    a1c = getattr(patient, "a1c", None)
    return bool(getattr(patient, "diabetes", False)) or (
        a1c is not None and a1c >= 6.5
    )


def _has_ckd_stage_3_or_higher(patient):
    egfr = getattr(patient, "egfr", None)
    return bool(getattr(patient, "ckd", False)) or (
        egfr is not None and egfr < 60
    )


def _has_diabetes_risk_enhancer(patient):
    diabetes_duration = getattr(patient, "diabetes_duration_years", None)
    abi = getattr(patient, "abi", None)
    return (
        (getattr(patient, "uacr", None) is not None and patient.uacr >= 30)
        or (getattr(patient, "egfr", None) is not None and patient.egfr < 60)
        or (diabetes_duration is not None and diabetes_duration >= 10)
        or bool(getattr(patient, "diabetic_retinopathy", False))
        or bool(getattr(patient, "diabetic_neuropathy", False))
        or bool(getattr(patient, "abi_lt_0_9", False))
        or (abi is not None and abi < 0.9)
        or bool(getattr(patient, "smoker", False))
        or bool(getattr(patient, "smoking", False))
        or bool(getattr(patient, "hypertension", False))
        or bool(getattr(patient, "bp_treated", False))
        or (getattr(patient, "sbp", None) is not None and patient.sbp >= 130)
        or (getattr(patient, "triglycerides", None) is not None and patient.triglycerides >= 150)
        or (getattr(patient, "prevent_10y_ascvd", None) is not None and patient.prevent_10y_ascvd >= 10)
    )


def _cac_zero_can_defer(patient):
    ldl_c = getattr(patient, "ldl_c", None)
    age = getattr(patient, "age", None)
    return not (
        (ldl_c is not None and ldl_c >= 190)
        or (_has_diabetes(patient) and age is not None and age > 40)
        or bool(getattr(patient, "smoker", False))
        or bool(getattr(patient, "smoking", False))
        or bool(getattr(patient, "premature_fhx_ascvd", False))
        or bool(getattr(patient, "family_history_premature_ascvd", False))
    )


def _has_severe_hypercholesterolemia_high_risk_feature(patient):
    cac = getattr(patient, "cac", None)
    apob = getattr(patient, "apob", None)
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


def build_target_result(patient):
    if patient.clinical_ascvd:
        return TargetResult(
            ldl_c_target=55,
            non_hdl_c_target=85,
            apob_target=60,
            rationale="Clinical ASCVD: very-high-risk secondary prevention target.",
        )

    if patient.cac is not None and patient.cac >= 1000:
        return TargetResult(
            ldl_c_target=55,
            non_hdl_c_target=85,
            apob_target=60,
            rationale=(
                "CAC >=1000: extreme subclinical plaque burden; treat toward very-high-risk target."
            ),
        )

    if patient.cac is not None and patient.cac >= 300:
        return TargetResult(
            ldl_c_target=70,
            non_hdl_c_target=100,
            apob_target=80,
            rationale=(
                "CAC 300-999: severe subclinical plaque burden; treat toward high-risk target. Intensification to very-high-risk targets may be reasonable."
            ),
        )

    if patient.cac is not None and patient.cac >= 100:
        return TargetResult(
            ldl_c_target=70,
            non_hdl_c_target=100,
            apob_target=80,
            rationale=(
                "CAC 100-299: significant subclinical plaque burden; treat toward high-risk target."
            ),
        )

    if patient.ldl_c is not None and patient.ldl_c >= 190:
        if _has_severe_hypercholesterolemia_high_risk_feature(patient):
            return TargetResult(
                ldl_c_target=70,
                non_hdl_c_target=100,
                apob_target=80,
                rationale=(
                    "LDL-C >=190 with additional high-risk features or possible FH pathway: use high-risk lipid targets; CAC 0 should not de-risk therapy."
                ),
            )
        return TargetResult(
            ldl_c_target=100,
            non_hdl_c_target=130,
            apob_target=90,
            rationale=(
                "LDL-C >=190 severe hypercholesterolemia pathway: high-intensity therapy indicated; CAC 0 should not de-risk therapy."
            ),
        )

    if patient.cac is not None and 1 <= patient.cac <= 99:
        return TargetResult(
            ldl_c_target=100,
            non_hdl_c_target=130,
            apob_target=90,
            rationale=(
                "CAC 1-99: mild subclinical plaque burden; treat toward primary prevention goal."
            ),
        )

    if patient.cac == 0 and _cac_zero_can_defer(patient):
        return TargetResult(
            ldl_c_target=None,
            non_hdl_c_target=None,
            apob_target=None,
            rationale="CAC 0: no target assigned from plaque burden alone.",
        )

    if _has_diabetes(patient) and _age_40_to_75(patient):
        if _has_diabetes_risk_enhancer(patient):
            return TargetResult(
                ldl_c_target=70,
                non_hdl_c_target=100,
                apob_target=80,
                rationale=(
                    "Diabetes age 40-75 with additional risk factors: high-intensity statin reasonable; high-risk targets."
                ),
            )
        return TargetResult(
            ldl_c_target=100,
            non_hdl_c_target=130,
            apob_target=90,
            rationale="Diabetes age 40-75: moderate-intensity statin target range.",
        )

    if _has_ckd_stage_3_or_higher(patient) and _age_40_to_75(patient):
        return TargetResult(
            ldl_c_target=100,
            non_hdl_c_target=130,
            apob_target=90,
            rationale="CKD stage 3 or higher age 40-75: moderate-intensity statin or statin plus ezetimibe pathway.",
        )

    if patient.cac is None and patient.prevent_10y_ascvd is not None:
        prevent_value = float(patient.prevent_10y_ascvd)

        if prevent_value >= 10:
            return TargetResult(
                ldl_c_target=70,
                non_hdl_c_target=100,
                apob_target=80,
                rationale=(
                    "PREVENT 10-year ASCVD risk >=10% without CAC: treat toward high-risk primary prevention target."
                ),
            )

        if prevent_value >= 3:
            return TargetResult(
                ldl_c_target=100,
                non_hdl_c_target=130,
                apob_target=90,
                rationale=(
                    "PREVENT 10-year ASCVD risk 3-<10% without CAC: treat toward primary prevention lipid target."
                ),
            )

        ldl_c = getattr(patient, "ldl_c", None)
        prevent_30y = getattr(patient, "prevent_30y_ascvd", None)
        if (ldl_c is not None and 160 <= ldl_c <= 189) or (
            prevent_30y is not None and prevent_30y >= 10
        ):
            return TargetResult(
                ldl_c_target=100,
                non_hdl_c_target=130,
                apob_target=90,
                rationale=(
                    "Low 10-year PREVENT risk with LDL-C 160-189 or 30-year risk >=10%: moderate statin reasonable if chosen."
                ),
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
