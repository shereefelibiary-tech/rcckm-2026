from ui.input_worksheet import WORKSHEET_KEY_BY_FIELD
from ui.worksheet_field_registry import (
    WORKSHEET_FIELD_REGISTRY,
    audit_worksheet_fields,
    should_show_field_in_default_worksheet,
)


def test_every_worksheet_field_has_registry_metadata():
    assert set(WORKSHEET_KEY_BY_FIELD).issubset(WORKSHEET_FIELD_REGISTRY)


def test_worksheet_audit_passes_default_inclusion_rules():
    audit = audit_worksheet_fields()

    assert audit["default_low_impact"] == []
    assert audit["hidden_high_impact"] == []
    assert audit["missing_metadata"] == []
    assert audit["manual_only_no_output"] == []
    assert audit["parseable_not_shown"] == []
    assert audit["visibility_mismatches"] == []


def test_default_fields_are_not_low_parseability_low_impact():
    default_fields = [
        metadata
        for metadata in WORKSHEET_FIELD_REGISTRY.values()
        if metadata.default_visible
    ]

    assert default_fields
    assert all(
        not (
            metadata.parseable_from_smartphrase == "low"
            and metadata.clinical_impact == "low"
        )
        for metadata in default_fields
    )


def test_high_impact_manual_fields_remain_visible_or_documented_advanced():
    high_impact_fields = [
        metadata
        for metadata in WORKSHEET_FIELD_REGISTRY.values()
        if metadata.clinical_impact == "high"
    ]

    assert high_impact_fields
    assert all(
        metadata.default_visible
        or (metadata.advanced_only and metadata.remove_from_default_reason)
        for metadata in high_impact_fields
    )


def test_material_default_risk_fields_are_visible():
    expected_default = {
        "age",
        "sex",
        "sbp",
        "dbp",
        "bmi",
        "tc",
        "ldl_c",
        "hdl_c",
        "triglycerides",
        "a1c",
        "egfr",
        "uacr",
        "smoker",
        "medications_raw",
        "clinical_ascvd",
        "cac",
        "incidental_cac",
        "incidental_cac_severity",
        "apob",
        "lp_a_value",
        "lp_a_unit",
        "statin_intensity",
        "statin_intolerance",
        "lipid_lowering",
        "ace_arb",
        "sglt2",
        "glp1",
        "dm_meds_raw",
        "family_history_premature_ascvd",
        "south_asian_ancestry",
        "filipino_ancestry",
    }

    assert expected_default <= {
        field_id
        for field_id, metadata in WORKSHEET_FIELD_REGISTRY.items()
        if metadata.default_visible
    }


def test_low_value_manual_context_is_advanced_only():
    for field_id in [
        "inflammatory_disease",
        "active_cancer",
        "cancer_survivor",
        "cancer_life_expectancy_gt_2y",
        "zip_code",
        "neighborhood_sdoh_context",
        "higher_risk_ancestry_context",
    ]:
        metadata = WORKSHEET_FIELD_REGISTRY[field_id]
        assert metadata.advanced_only
        assert not metadata.default_visible
        assert metadata.remove_from_default_reason


def test_low_value_manual_context_is_not_session_mapped():
    for field_id in [
        "zip_code",
        "neighborhood_sdoh_context",
        "higher_risk_ancestry_context",
    ]:
        assert field_id not in WORKSHEET_KEY_BY_FIELD


def test_lipid_supplements_are_not_structured_worksheet_field():
    assert "lipid_supplements" not in WORKSHEET_FIELD_REGISTRY
    assert "lipid_supplements" not in WORKSHEET_KEY_BY_FIELD


def test_default_visibility_helper_matches_registry_flags():
    assert all(
        metadata.default_visible == should_show_field_in_default_worksheet(metadata)
        for metadata in WORKSHEET_FIELD_REGISTRY.values()
    )
