from modules.plaque.classifier import classify_cac
from core.results import RCCKMResult


def build_plaque_result(patient):
    plaque_category = classify_cac(patient.cac)
    return RCCKMResult(plaque_category=plaque_category)
