def _format_value(prefix, value, suffix=""):
    return f"{prefix} {value:g}{suffix}"


def _has_ckd(result, patient):
    egfr_stage = getattr(result, "egfr_stage", None)
    albuminuria_stage = getattr(result, "albuminuria_stage", None)

    if egfr_stage in {"G3a", "G3b", "G4", "G5"}:
        return True

    if albuminuria_stage in {"A2", "A3"}:
        return True

    egfr = getattr(patient, "egfr", None)
    uacr = getattr(patient, "uacr", None)
    return (egfr is not None and egfr < 60) or (uacr is not None and uacr >= 30)


def _has_albuminuria(result, patient):
    albuminuria_stage = getattr(result, "albuminuria_stage", None)
    uacr = getattr(patient, "uacr", None)
    return albuminuria_stage in {"A2", "A3"} or (
        uacr is not None and uacr >= 30
    )


def _has_diabetes(patient):
    a1c = getattr(patient, "a1c", None)
    return bool(getattr(patient, "diabetes", False)) or (
        a1c is not None and a1c >= 6.5
    )


def _diabetes_driver(patient):
    a1c = getattr(patient, "a1c", None)
    if a1c is not None and a1c >= 6.5:
        return _format_value("A1c", a1c, "%")
    return "T2DM"


def _is_smoking(patient):
    return bool(getattr(patient, "smoker", False)) or bool(
        getattr(patient, "smoking", False)
    )


def _lpa_is_major(patient):
    lpa = getattr(patient, "lp_a_value", None)
    unit = getattr(patient, "lp_a_unit", None)
    return (unit == "nmol/L" and lpa is not None and lpa >= 125) or (
        unit == "mg/dL" and lpa is not None and lpa >= 50
    )


def _has_supportive_hscrp_context(patient, result):
    if _has_diabetes(patient) or _has_ckd(result, patient):
        return True
    if getattr(patient, "inflammatory_disease", False):
        return True
    return any(
        bool(getattr(patient, field, False))
        for field in (
            "rheumatoid_arthritis",
            "sle",
            "psoriasis",
            "ibd",
            "hiv",
        )
    )


def build_top_drivers(patient, result):
    drivers = []
    diabetes = _has_diabetes(patient)
    ckd = _has_ckd(result, patient)
    albuminuria = _has_albuminuria(result, patient)
    compressed_diabetes_ckd = diabetes and ckd and albuminuria

    if getattr(patient, "clinical_ascvd", False):
        drivers.append("Clinical ASCVD")

    cac = getattr(patient, "cac", None)
    if cac is not None and cac > 0:
        cac_driver = _format_value("CAC", cac)
        if cac >= 300 and not getattr(patient, "clinical_ascvd", False):
            drivers.insert(0, cac_driver)
        else:
            drivers.append(cac_driver)

    apob = getattr(patient, "apob", None)
    if apob is not None and apob >= 100:
        drivers.append(_format_value("ApoB", apob, " mg/dL"))

    ldl_c = getattr(patient, "ldl_c", None)
    if ldl_c is not None and ldl_c >= 160 and apob is not None and apob < 100:
        drivers.append("LDL/ApoB discordance")

    if ldl_c is not None and ldl_c >= 190:
        drivers.append(_format_value("LDL-C", ldl_c, " mg/dL"))

    if compressed_diabetes_ckd:
        kdigo_stage = getattr(result, "kdigo_stage", None)
        drivers.append(
            f"T2DM with CKD {kdigo_stage}" if kdigo_stage else "T2DM with CKD"
        )
    elif diabetes:
        drivers.append(_diabetes_driver(patient))

    if ckd and not compressed_diabetes_ckd:
        kdigo_stage = getattr(result, "kdigo_stage", None)
        drivers.append(f"CKD {kdigo_stage}" if kdigo_stage else "CKD")

    if albuminuria and not compressed_diabetes_ckd:
        uacr = getattr(patient, "uacr", None)
        drivers.append(
            _format_value("UACR", uacr, " mg/g")
            if uacr is not None
            else "Albuminuria"
        )

    lpa = getattr(patient, "lp_a_value", None)
    if _lpa_is_major(patient):
        unit = getattr(patient, "lp_a_unit", None)
        suffix = f" {unit}" if unit else ""
        drivers.append(_format_value("Lp(a)", lpa, suffix))

    if _is_smoking(patient):
        drivers.append("Smoking")

    if getattr(patient, "inflammatory_disease", False):
        drivers.append("Inflammatory disease")

    hscrp = getattr(patient, "hscrp", None)
    if (
        hscrp is not None
        and hscrp >= 2
        and _has_supportive_hscrp_context(patient, result)
    ):
        drivers.append(_format_value("hsCRP", hscrp, " mg/L"))

    triglycerides = getattr(patient, "triglycerides", None)
    if triglycerides is not None and triglycerides >= 500:
        drivers.append(_format_value("TG", triglycerides, " mg/dL"))

    if bool(getattr(patient, "premature_fhx_ascvd", False)) or bool(
        getattr(patient, "family_history_premature_ascvd", False)
    ):
        drivers.append(
            getattr(patient, "family_history_summary", None)
            or "Family history premature ASCVD"
        )

    return drivers[:4]
