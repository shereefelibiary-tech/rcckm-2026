from core.enums import PlaqueCategory
from core.results import RCCKMResult


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
