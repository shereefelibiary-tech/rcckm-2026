def test_streamlit_app_and_core_engine_import_for_deployment():
    """Smoke-test the Render entrypoint and core engine imports."""
    import app
    from core.engine import evaluate_patient
    from core.patient import Patient

    assert hasattr(app, "main")
    result = evaluate_patient(Patient(age=50, sex="female"))
    assert result is not None
