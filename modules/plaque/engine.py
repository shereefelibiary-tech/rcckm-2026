from core.enums import PlaqueCategory
from core.results import RCCKMResult


def normalize_cac_percentile(cac_percentile):
    """Return a CAC percentile as a bounded float, or None when invalid."""
    if cac_percentile is None:
        return None
    try:
        value = float(cac_percentile)
    except (TypeError, ValueError):
        return None
    if 0 <= value <= 100:
        return value
    return None


def _percentile_label(percentile):
    if percentile is None:
        return ""
    if float(percentile).is_integer():
        return f"{int(percentile)}th percentile"
    return f"{percentile:.1f}th percentile"


def format_cac_percentile_context(cac_score, cac_percentile, *, include_clinician_detail=False):
    """Format CAC percentile as contextual wording without changing CAC classification."""
    if cac_score is None:
        return None
    try:
        cac_value = float(cac_score)
    except (TypeError, ValueError):
        return None
    percentile = normalize_cac_percentile(cac_percentile)
    if percentile is None or cac_value == 0 or cac_value >= 300:
        return None

    detail = f" Clinician detail: {_percentile_label(percentile)}." if include_clinician_detail else ""
    if percentile >= 75:
        return f"Higher than expected for age and sex.{detail}"
    if cac_value < 100:
        return f"Within the expected range for age and sex.{detail}"
    return f"Clinician detail: {_percentile_label(percentile)}." if include_clinician_detail else None


def build_plaque_result(patient):
    cac = getattr(patient, "cac", None)

    if cac is None:
        plaque_category = PlaqueCategory.UNKNOWN
    elif cac == 0:
        plaque_category = PlaqueCategory.NONE
    elif 1 <= cac <= 99:
        plaque_category = PlaqueCategory.MILD
    elif 100 <= cac <= 299:
        plaque_category = PlaqueCategory.MODERATE
    elif 300 <= cac <= 999:
        plaque_category = PlaqueCategory.SEVERE
    elif cac >= 1000:
        plaque_category = PlaqueCategory.EXTENSIVE
    else:
        plaque_category = PlaqueCategory.UNKNOWN

    return RCCKMResult(plaque_category=plaque_category)
