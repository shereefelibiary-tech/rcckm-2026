def _first_cac_driver(result):
    for driver in getattr(result, "top_drivers", []):
        if driver.startswith("CAC "):
            return driver

    ckm_stage = getattr(result, "ckm_stage", None)
    if not ckm_stage:
        return None

    for driver in ckm_stage.get("drivers", []):
        if driver.startswith("CAC "):
            return driver

    return None


def _rss_category(rss_total):
    if rss_total >= 75:
        return "Severe"
    if rss_total >= 50:
        return "High"
    if rss_total >= 25:
        return "Moderate"
    return "Low"


def build_snapshot_lines(result):
    lines = []

    if result.risk_level:
        lines.append(f"Risk level: {result.risk_level.value}")

    if result.ckm_stage:
        drivers = result.ckm_stage.get("drivers", [])
        line = f"CKM stage: Stage {result.ckm_stage.get('stage')}"
        if drivers:
            line = f"{line} — {'; '.join(drivers)}"
        lines.append(line)

    if result.prevent_10y_ascvd is not None:
        lines.append(f"PREVENT 10-year ASCVD risk: {result.prevent_10y_ascvd:g}%")

    if getattr(result, "prevent_30y_ascvd", None) is not None:
        lines.append(
            f"PREVENT 30-year ASCVD risk: {result.prevent_30y_ascvd:g}%"
        )

    cac_driver = _first_cac_driver(result)
    if cac_driver:
        lines.append(f"Plaque: {cac_driver}")

    if result.kdigo_stage:
        lines.append(f"Kidney: {result.kdigo_stage}")

    if result.rss_total is not None:
        rss_category = result.rss_category or _rss_category(result.rss_total)
        lines.append(f"RSS: {result.rss_total:g}/100 ({rss_category})")

    if result.top_drivers:
        lines.append(f"Top drivers: {'; '.join(result.top_drivers)}")

    if result.family_history_summary:
        lines.append(f"Family history: {result.family_history_summary}")

    if result.clarification and result.clarification.get("tier", 0) >= 2:
        lines.append(f"Clarification: {result.clarification.get('summary')}")

    if result.discordance_insight and result.discordance_insight.get("status") in {
        "discordant",
        "uncertain",
    }:
        lines.append(
            f"Discordance: {result.discordance_insight.get('headline')}"
        )

    return lines
