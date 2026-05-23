def _has_ckd_by_kdigo(result):
    egfr_stage = getattr(result, "egfr_stage", None)
    albuminuria_stage = getattr(result, "albuminuria_stage", None)

    if egfr_stage in {"G3a", "G3b", "G4", "G5"}:
        return True

    return albuminuria_stage in {"A2", "A3"}


def classify_ckm_stage(patient, result):
    drivers = []

    if getattr(patient, "clinical_ascvd", False):
        drivers.append("Clinical ASCVD")
        return {
            "stage": 4,
            "drivers": drivers,
            "headline": "Clinical cardiovascular disease present.",
        }

    if getattr(patient, "cac", None) is not None and patient.cac > 0:
        drivers.append(f"CAC {patient.cac:g}")

    if getattr(result, "kdigo_stage", None) and _has_ckd_by_kdigo(result):
        drivers.append(f"CKD {result.kdigo_stage}")

    if drivers:
        return {
            "stage": 3,
            "drivers": drivers,
            "headline": "Subclinical cardiovascular or kidney disease present.",
        }

    a1c = getattr(patient, "a1c", None)
    triglycerides = getattr(patient, "triglycerides", None)
    hdl = getattr(patient, "hdl_c", None)

    if getattr(patient, "diabetes", False):
        drivers.append("Diabetes")
    elif a1c is not None and a1c >= 6.5:
        drivers.append(f"A1c {a1c:g}%")

    if getattr(patient, "hypertension", False):
        drivers.append("Hypertension")

    if getattr(patient, "bp_treated", False):
        drivers.append("Treated BP")

    if triglycerides is not None and triglycerides >= 150:
        drivers.append(f"TG {triglycerides:g}")

    if hdl is not None:
        sex = str(getattr(patient, "sex", "")).lower()
        low_hdl_threshold = 50 if sex in ("female", "f") else 40
        if hdl < low_hdl_threshold:
            drivers.append(f"Low HDL {hdl:g}")

    if getattr(patient, "uacr", None) is not None and patient.uacr >= 30:
        drivers.append(f"UACR {patient.uacr:g}")

    if drivers:
        return {
            "stage": 2,
            "drivers": drivers,
            "headline": "Metabolic risk factors present.",
        }

    if getattr(patient, "bmi", None) is not None and patient.bmi >= 30:
        drivers.append(f"BMI {patient.bmi:g}")

    if a1c is not None and 5.7 <= a1c <= 6.4:
        drivers.append(f"A1c {a1c:g}%")

    if getattr(patient, "elevated_bp", False):
        drivers.append("Elevated BP")

    if drivers:
        return {
            "stage": 1,
            "drivers": drivers,
            "headline": "Early metabolic risk signals present.",
        }

    return {
        "stage": 0,
        "drivers": [],
        "headline": "No CKM risk signals detected.",
    }
