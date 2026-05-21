from core.results import TargetResult


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
                "CAC 300-999: severe subclinical plaque burden; treat toward high-risk target."
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

    if patient.cac is not None and 1 <= patient.cac <= 99:
        return TargetResult(
            ldl_c_target=100,
            non_hdl_c_target=130,
            apob_target=90,
            rationale=(
                "CAC 1-99: mild subclinical plaque burden; treat toward primary prevention goal."
            ),
        )

    if patient.cac == 0:
        return TargetResult(
            ldl_c_target=None,
            non_hdl_c_target=None,
            apob_target=None,
            rationale="CAC 0: no target assigned from plaque burden alone.",
        )

    return TargetResult(
        ldl_c_target=None,
        non_hdl_c_target=None,
        rationale="No target pathway assigned yet.",
    )
