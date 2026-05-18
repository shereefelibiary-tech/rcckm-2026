from typing import Optional

from core.enums import PlaqueCategory


def classify_cac(cac: float | None) -> Optional[PlaqueCategory]:
    if cac is None:
        return None

    if cac == 0:
        return PlaqueCategory.NONE

    if 1 <= cac <= 99:
        return PlaqueCategory.MILD

    if 100 <= cac <= 299:
        return PlaqueCategory.HIGH

    if cac >= 300:
        return PlaqueCategory.EXTENSIVE

    return None
