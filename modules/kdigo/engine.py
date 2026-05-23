def classify_egfr_stage(egfr):
    if egfr is None:
        return None

    if egfr >= 90:
        return "G1"

    if 60 <= egfr <= 89:
        return "G2"

    if 45 <= egfr <= 59:
        return "G3a"

    if 30 <= egfr <= 44:
        return "G3b"

    if 15 <= egfr <= 29:
        return "G4"

    return "G5"


def classify_albuminuria_stage(uacr):
    if uacr is None:
        return None

    if uacr < 30:
        return "A1"

    if 30 <= uacr <= 299:
        return "A2"

    return "A3"


def build_kdigo_stage(patient):
    egfr_stage = classify_egfr_stage(getattr(patient, "egfr", None))
    albuminuria_stage = classify_albuminuria_stage(getattr(patient, "uacr", None))

    if egfr_stage is None and albuminuria_stage is None:
        return None

    if albuminuria_stage is None:
        return egfr_stage

    if egfr_stage is None:
        return albuminuria_stage

    return f"{egfr_stage}{albuminuria_stage}"
