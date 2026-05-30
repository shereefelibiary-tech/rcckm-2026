from core.enums import PlaqueCategory


def build_dominant_action(patient, result):
    category = result.plaque_category

    if category == PlaqueCategory.EXTENSIVE:
        return (
            "Very high plaque burden present. Intensify lipid-lowering therapy toward "
            "aggressive ApoB/LDL-C targets."
        )

    if category == PlaqueCategory.SEVERE:
        return "High plaque burden present. Lipid-lowering intensification is recommended."

    if category == PlaqueCategory.MODERATE:
        return (
            "Moderate plaque burden present. Lipid-lowering therapy should target "
            "high-risk prevention goals."
        )

    if category == PlaqueCategory.MILD:
        return "Mild plaque burden present. Review lipid targets."

    if category == PlaqueCategory.NONE:
        return "No plaque identified. Continue risk-factor optimization and reassess over time."

    return (
        "Plaque status not available. Add plaque data only if results would change management."
    )
