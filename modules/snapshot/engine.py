def build_snapshot_lines(result):
    lines = []

    if result.risk_level:
        lines.append(f"Risk level: {result.risk_level.value}")

    if result.plaque_category:
        lines.append(f"Plaque category: {result.plaque_category.value}")

    if result.decision_stability:
        lines.append(f"Decision stability: {result.decision_stability.value}")

    if result.targets:
        for target in result.targets:
            if target.ldl_c_target is not None:
                lines.append(f"LDL-C target: <{target.ldl_c_target} mg/dL")
            if target.non_hdl_c_target is not None:
                lines.append(f"Non-HDL-C target: <{target.non_hdl_c_target} mg/dL")

    if result.diagnosis_candidates:
        diagnosis_names = [c.name for c in result.diagnosis_candidates]
        diagnosis_string = ", ".join(diagnosis_names)
        lines.append(f"Diagnosis candidates: {diagnosis_string}")

    return lines
