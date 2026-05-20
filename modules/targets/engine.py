from core.results import TargetResult


def build_target_result(patient):
    if patient.clinical_ascvd:
        return TargetResult(
            ldl_c_target=55,
            non_hdl_c_target=85,
            rationale="Clinical ASCVD: intensive secondary prevention target pathway.",
        )

    if patient.cac is not None and patient.cac >= 300:
        return TargetResult(
            ldl_c_target=70,
            non_hdl_c_target=100,
            rationale="Extensive CAC: high plaque burden target pathway.",
        )

    if patient.cac is not None and patient.cac >= 100:
        return TargetResult(
            ldl_c_target=100,
            non_hdl_c_target=130,
            rationale="CAC >=100: elevated plaque burden target pathway.",
        )

    return TargetResult(
        ldl_c_target=None,
        non_hdl_c_target=None,
        rationale="No target pathway assigned yet.",
    )
