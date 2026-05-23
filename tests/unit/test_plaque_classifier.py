from core.enums import PlaqueCategory
from modules.plaque.classifier import classify_cac


def test_classify_cac_returns_expected_category():
    cases = [
        (None, None),
        (0, PlaqueCategory.NONE),
        (1, PlaqueCategory.MILD),
        (99, PlaqueCategory.MILD),
        (100, PlaqueCategory.HIGH),
        (299, PlaqueCategory.HIGH),
        (300, PlaqueCategory.EXTENSIVE),
        (1000, PlaqueCategory.EXTENSIVE),
    ]
    for cac, expected in cases:
        assert classify_cac(cac) == expected
