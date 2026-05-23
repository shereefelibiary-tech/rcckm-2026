from core.enums import RiskLevel


def build_discordance_insight(patient, result):
    prevent_risk = result.prevent_10y_ascvd
    if prevent_risk is None:
        return None

    cac = getattr(patient, "cac", None)
    if cac is not None and cac >= 300 and result.prevent_risk_category in {
        RiskLevel.LOW,
        RiskLevel.BORDERLINE,
        RiskLevel.INTERMEDIATE,
    }:
        return {
            "status": "discordant",
            "type": "plaque_exceeds_population_risk",
            "headline": "Plaque burden exceeds estimated population risk.",
            "detail": (
                "High CAC suggests structural disease burden beyond the estimated 10-year PREVENT risk."
            ),
        }

    if prevent_risk >= 10 and cac == 0:
        return {
            "status": "discordant",
            "type": "risk_exceeds_plaque_burden",
            "headline": "Estimated risk exceeds measured plaque burden.",
            "detail": (
                "PREVENT risk may be driven by age, kidney, metabolic, or blood pressure factors despite CAC=0."
            ),
        }

    if prevent_risk >= 10 and cac is None:
        return {
            "status": "uncertain",
            "type": "high_population_risk_plaque_unmeasured",
            "headline": "High estimated risk with plaque unmeasured.",
            "detail": (
                "CAC may clarify whether estimated risk reflects structural plaque burden."
            ),
        }

    return {
        "status": "aligned",
        "type": "no_major_discordance",
        "headline": "No major PREVENT/plaque discordance detected.",
        "detail": "",
    }
