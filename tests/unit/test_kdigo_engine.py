from core.patient import Patient
from modules.kdigo.engine import (
    build_kdigo_stage,
    classify_albuminuria_stage,
    classify_egfr_stage,
)


def test_classify_egfr_stage_boundaries():
    assert classify_egfr_stage(90) == "G1"
    assert classify_egfr_stage(60) == "G2"
    assert classify_egfr_stage(45) == "G3a"
    assert classify_egfr_stage(30) == "G3b"
    assert classify_egfr_stage(15) == "G4"
    assert classify_egfr_stage(14) == "G5"


def test_classify_albuminuria_stage_boundaries():
    assert classify_albuminuria_stage(29) == "A1"
    assert classify_albuminuria_stage(30) == "A2"
    assert classify_albuminuria_stage(300) == "A3"


def test_build_kdigo_stage_returns_combined_stage():
    patient = Patient(age=60, sex="male", egfr=55, uacr=45)

    assert build_kdigo_stage(patient) == "G3aA2"


def test_build_kdigo_stage_returns_partial_stage_when_one_axis_missing():
    egfr_only = Patient(age=60, sex="male", egfr=55, uacr=None)
    albuminuria_only = Patient(age=60, sex="male", egfr=None, uacr=420)
    neither = Patient(age=60, sex="male", egfr=None, uacr=None)

    assert build_kdigo_stage(egfr_only) == "G3a"
    assert build_kdigo_stage(albuminuria_only) == "A3"
    assert build_kdigo_stage(neither) is None
