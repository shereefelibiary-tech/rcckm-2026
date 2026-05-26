from ui.input_worksheet import build_patient_from_inputs, label_with_unit
from ui.report_state import hash_worksheet_state, worksheet_payload_from_source
from core.results import DiagnosisCandidate
from ui.diagnosis_confirm_panel import prioritize_linked_diagnoses
from ui.report_layout import (
    _build_targets_html,
    demo_patient,
    render_report,
    run_patient,
)
from ui.export_print import contains_html_tags, normalize_export_text
from renderers.clarifier_renderer import build_clarifier_card_html
from renderers.continuum_bar import build_continuum_bar_html
from renderers.prevent_card import render_prevent_card
from renderers.patient_roadmap import render_patient_roadmap
from renderers.rss_renderer import (
    build_rss_panel_html,
    format_tower_value,
    get_rss_display_contributions,
    get_rss_display_items,
)
from renderers.where_patient_falls import build_where_patient_falls_html


class _SessionState(dict):
    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


class _Column:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _Expander:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeComponentsV1:
    def __init__(self, owner):
        self.owner = owner

    def html(self, value, height=None, scrolling=False):
        self.owner.messages.append(("component_html", value, height, scrolling))


class _FakeComponents:
    def __init__(self, owner):
        self.v1 = _FakeComponentsV1(owner)


class _FakeStreamlit:
    def __init__(self, clicked_key=None):
        self.session_state = _SessionState()
        self.messages = []
        self.components = _FakeComponents(self)
        self.clicked_key = clicked_key
        self.rerun_requested = False

    def write(self, value):
        self.messages.append(("write", value))

    def caption(self, value):
        self.messages.append(("caption", value))

    def markdown(self, value, unsafe_allow_html=False):
        self.messages.append(("markdown", value, unsafe_allow_html))

    def code(self, value, language=None):
        self.messages.append(("code", value, language))

    def columns(self, count):
        if isinstance(count, int):
            return [_Column() for _ in range(count)]
        return [_Column() for _ in count]

    def button(self, label, key=None, **kwargs):
        self.messages.append(("button", label, key, kwargs))
        return key == self.clicked_key

    def download_button(self, label, data=None, file_name=None, mime=None, **kwargs):
        self.messages.append(("download_button", label, data, file_name, mime, kwargs))
        return False

    def checkbox(self, label, value=False, key=None):
        self.messages.append(("checkbox", label, value, key))
        return False

    def expander(self, label, expanded=False):
        self.messages.append(("expander", label, expanded))
        return _Expander()

    def rerun(self):
        self.rerun_requested = True


def test_render_report_fail_soft_without_streamlit_dependency():
    fake_st = _FakeStreamlit()

    result = render_report(fake_st, demo_patient())

    assert result.rss_total > 0
    assert any(message[0] == "markdown" for message in fake_st.messages)
    assert any("rss-module" in str(message) for message in fake_st.messages)

    html_messages = [
        message
        for message in fake_st.messages
        if message[0] == "component_html"
        and ("rc-shell" in str(message[1]) or "rss-module" in str(message[1]))
    ]
    assert html_messages
    inline_html = "\n".join(
        str(message[1])
        for message in fake_st.messages
        if message[0] == "markdown" and len(message) > 2 and message[2] is True
    )
    assert "WHERE THIS PATIENT FALLS" in inline_html


def test_risk_continuum_renders_as_unsafe_html():
    fake_st = _FakeStreamlit()

    render_report(fake_st, demo_patient())

    continuum_messages = [
        message
        for message in fake_st.messages
        if message[0] == "component_html" and "rc-shell" in str(message[1])
    ]

    assert continuum_messages
    assert not any("&lt;div" in str(message[1]) for message in continuum_messages)


def test_custom_html_renderers_return_html_strings():
    patient = demo_patient()
    result, rss_total, contributions = run_patient(patient)

    rendered = {
        "continuum": build_continuum_bar_html(patient, result),
        "prevent": render_prevent_card(result),
        "roadmap": render_patient_roadmap(patient, result),
        "rss": build_rss_panel_html(rss_total, contributions),
        "where": build_where_patient_falls_html(patient, result),
        "clarifiers": build_clarifier_card_html(result),
    }

    for html in rendered.values():
        assert isinstance(html, str)
        assert "<div" in html


def test_report_uses_component_html_for_custom_renderers():
    fake_st = _FakeStreamlit()

    render_report(fake_st, demo_patient())

    html_components = [
        message
        for message in fake_st.messages
        if message[0] == "component_html"
    ]
    combined = "\n".join(str(message[1]) for message in html_components)
    inline_html = "\n".join(
        str(message[1])
        for message in fake_st.messages
        if message[0] == "markdown" and len(message) > 2 and message[2] is True
    )

    assert "rc-shell" in combined
    assert "prevent-card" in inline_html
    assert "roadmap-card" in inline_html
    assert "rss-module" in inline_html
    assert "Where the Risk Is Coming From" in inline_html
    assert "grid-template-columns: 220px minmax(0, 1fr)" in inline_html
    assert "rss-tower-zone" in inline_html
    assert "rss-list-zone" in inline_html
    assert "rss-card" in inline_html
    assert "rss-contributor-heading" in inline_html
    assert "Largest contribution first" not in inline_html
    assert "ordered by contribution size" not in inline_html
    assert "Tower shows RSS burden" not in inline_html
    assert "Contributor explanations" not in inline_html
    assert "drivers-card" not in inline_html
    assert "rss-support-card" not in inline_html
    assert "wpf-card" in inline_html
    assert "clarifier-card" in inline_html
    assert "ckm-kdigo-strip" in inline_html
    ckm_html = inline_html.split('class="ckm-kdigo-strip"', 1)[1][:1000]
    assert "CKM Stage 3" in ckm_html
    assert "Subclinical cardiovascular disease or CKD is present." in ckm_html
    assert ckm_html.count("G3aA2") == 1
    assert "eGFR 55; UACR 45 mg/g" in ckm_html
    assert "CAC 350 indicates high plaque burden." in ckm_html
    assert "Cardiometabolic-kidney context" not in inline_html
    assert "Details" not in inline_html
    assert "&lt;div" not in combined
    assert not any(
        message[0] == "component_html" and "prevent-card" in str(message[1])
        for message in fake_st.messages
    )

    report_html = combined + "\n" + inline_html
    unwanted_wording = [
        "&lt;div",
        "phenotype",
        "inherited risk",
        "Genetics",
        "genetics",
        "Largest contribution first",
        "ordered by contribution size",
        "contributors largest first",
        "RSS support view",
        "confirmed by data",
        "data-derived",
        "YOU ARE HERE",
        "Cardiometabolic-kidney context",
        "Active signals:",
    ]
    for phrase in unwanted_wording:
        assert phrase not in report_html

    expander_labels = [
        message[1] for message in fake_st.messages if message[0] == "expander"
    ]
    assert "Where this patient falls - audit table" not in expander_labels
    assert "What would help clarify risk?" not in expander_labels
    assert "CKM / KDIGO details" not in expander_labels
    assert "Assessment candidates" not in expander_labels
    assert "EMR note" not in expander_labels
    assert "More candidates" not in expander_labels
    assert "Snapshot / synthesis" not in expander_labels


def test_report_hierarchy_is_clinician_first_and_patient_roadmap_last():
    fake_st = _FakeStreamlit()

    render_report(fake_st, demo_patient())

    messages = [str(message) for message in fake_st.messages]
    combined = "\n".join(messages)

    assert "prevent-card" in combined
    assert "10-Year Cardiovascular Risk" in combined
    assert "10.16%" in combined
    assert "prevent-matrix" in combined
    assert "30.65%" in combined
    assert "PREVENT population model" in combined
    assert "Your Prevention Roadmap" in combined
    assert "Copy patient roadmap" in combined
    assert "rss-module" in combined
    assert "Key Contributors" not in combined
    assert "Signal Burden" not in combined
    assert "Snapshot" not in combined

    continuum_index = next(i for i, message in enumerate(messages) if "rc-shell" in message)
    prevent_index = next(i for i, message in enumerate(messages) if "prevent-card" in message)
    drivers_index = next(i for i, message in enumerate(messages) if "rss-module" in message)
    ckm_index = next(i for i, message in enumerate(messages) if "ckm-kdigo-strip" in message)
    where_index = next(i for i, message in enumerate(messages) if "wpf-card" in message)
    clarifier_index = next(i for i, message in enumerate(messages) if "clarifier-card" in message)
    targets_index = next(i for i, message in enumerate(messages) if "targets-compact" in message)
    action_index = next(i for i, message in enumerate(messages) if "action-card" in message)
    assessment_index = next(i for i, message in enumerate(messages) if "Assessment candidates" in message)
    emr_index = next(i for i, message in enumerate(messages) if "Risk Continuum - EMR Note" in message)
    roadmap_index = next(i for i, message in enumerate(messages) if "roadmap-card" in message)
    copy_index = next(i for i, message in enumerate(messages) if "Copy patient roadmap" in message)
    export_index = next(i for i, message in enumerate(messages) if "Export / Print" in message)

    assert continuum_index < prevent_index < drivers_index < ckm_index
    assert ckm_index < where_index < clarifier_index < targets_index < action_index
    assert action_index < assessment_index < emr_index < roadmap_index < copy_index
    assert copy_index < export_index


def test_export_print_section_uses_plain_text_outputs_and_downloads():
    fake_st = _FakeStreamlit()

    render_report(fake_st, demo_patient())

    combined = "\n".join(str(message) for message in fake_st.messages)
    assert "Export / Print" in combined
    assert "Copy the EMR note for clinical documentation" in combined
    assert "Copy EMR note" in combined
    assert "Copy patient roadmap" in combined
    assert "Print patient roadmap" in combined
    assert "Review all copied or printed output before use." in combined

    downloads = [message for message in fake_st.messages if message[0] == "download_button"]
    labels = [message[1] for message in downloads]
    assert "Download EMR note (.txt)" in labels
    assert "Download patient roadmap (.txt)" in labels
    for _kind, _label, data, _file_name, mime, _kwargs in downloads:
        assert mime == "text/plain"
        assert data == normalize_export_text(data)
        assert not contains_html_tags(data)


def test_default_demo_patient_populates_major_outputs_and_renderers():
    patient = demo_patient()
    fake_st = _FakeStreamlit()

    result = render_report(fake_st, patient)

    assert patient.age == 55
    assert patient.sbp == 132
    assert patient.dbp == 82
    assert patient.bp_treated is True
    assert patient.tc == 205
    assert patient.ldl_c == 132
    assert patient.hdl_c == 48
    assert patient.triglycerides == 180
    assert patient.apob == 110
    assert patient.lp_a_value == 80
    assert patient.lp_a_unit == "nmol/L"
    assert patient.a1c == 7.1
    assert patient.diabetes is True
    assert patient.bmi == 31
    assert patient.egfr == 55
    assert patient.uacr == 45
    assert patient.cac == 350
    assert patient.clinical_ascvd is False
    assert patient.smoker is False
    assert patient.family_history_premature_ascvd is True
    assert patient.hscrp == 2.4
    assert patient.inflammatory_disease is False
    assert patient.osa is True
    assert patient.masld is True
    assert patient.lipid_lowering is False
    assert patient.sglt2 is False
    assert patient.glp1 is False
    assert patient.ace_arb is True

    assert result.prevent_10y_ascvd is not None
    assert result.prevent_10y_total_cvd is not None
    assert result.prevent_30y_ascvd is not None
    assert result.prevent_30y_total_cvd is not None
    assert result.rss_total > 0
    assert result.kdigo_stage == "G3aA2"
    assert result.targets
    assert result.dominant_action
    assert result.diagnosis_candidates

    combined = "\n".join(str(message) for message in fake_st.messages)
    assert "prevent-card" in combined
    assert "roadmap-card" in combined
    assert "rss-module" in combined
    assert "targets-compact" in combined


def test_unified_rss_module_returns_unescaped_contributor_rows():
    patient = demo_patient()
    _result, rss_total, contributions = run_patient(patient)

    html = build_rss_panel_html(rss_total, contributions)

    assert "rss-module" in html
    assert "Where the Risk Is Coming From" in html
    assert "rss-driver-row" in html
    assert "grid-template-columns: 220px minmax(0, 1fr)" in html
    assert "rss-tower-zone" in html
    assert "rss-list-zone" in html
    assert "rss-card" in html
    assert "rss-contributor-heading" in html
    assert "Largest contribution first" not in html
    assert "ordered by contribution size" not in html
    assert "Tower shows RSS burden" not in html
    assert html.count("rss-driver-row") >= 5
    assert "Contributor explanations" not in html
    assert "Key Contributors" not in html
    assert "RSS tower and contributor explanations" not in html
    assert "&lt;div" not in html


def test_rss_module_uses_shared_visual_order_for_tower_and_list():
    patient = demo_patient()
    _result, rss_total, contributions = run_patient(patient)

    html = build_rss_panel_html(rss_total, contributions)

    expected = [
        "A1c 7.1%",
        "Albuminuria, UACR 45 mg/g",
        "Kidney filtration, eGFR 55",
        "ApoB 110 mg/dL",
        "Coronary calcium 350",
    ]
    tower_expected = [
        "A1c 7.1%",
        "UACR 45 mg/g",
        "eGFR 55",
        "ApoB 110 mg/dL",
        "CAC 350",
    ]
    tower = html.split('<div class="rss-tower">', 1)[1].split('<div class="rss-drivers">', 1)[0]
    driver_list = html.split('<div class="rss-driver-list">', 1)[1]
    row_indexes = [driver_list.index(label) for label in expected]
    tower_indexes = [tower.index(label) for label in tower_expected]

    assert row_indexes == sorted(row_indexes)
    assert tower_indexes == sorted(tower_indexes)
    display_contributions = get_rss_display_contributions(contributions)
    assert {item.label for item in display_contributions} == {
        item.label for item in contributions if item.points > 0
    }
    for item in display_contributions:
        tower_value = format_tower_value(item)
        assert tower_value in tower
    for item in get_rss_display_items(None, contributions, rss_total)["contributors"]:
        assert item["label"] in driver_list
    assert "CAC 350" in html
    assert "ApoB 110 mg/dL" in html
    assert "eGFR 55" in html
    assert "UACR 45 mg/g" in html
    assert "A1c 7.1%" in html
    assert "rss-tower-empty" in tower
    assert tower.index("rss-tower-empty") < tower.index("A1c 7.1%")
    assert tower.rindex("CAC 350") > tower.index("ApoB 110 mg/dL")
    assert "CAC 350: Coronary calcium" not in html
    assert "ApoB 110 mg/dL: ApoB / particle burden" not in html
    assert "Albuminuria signal" not in driver_list
    assert "Diabetes-range glycemia" not in driver_list
    assert " signal" not in driver_list.lower()


def test_rss_tower_and_rows_match_exact_visual_order_without_sorting_copy():
    patient = demo_patient()
    _result, rss_total, contributions = run_patient(patient)

    html = build_rss_panel_html(rss_total, contributions)
    rows = html.split('<div class="rss-driver-list">', 1)[1]

    row_expected = [
        "A1c 7.1%",
        "Albuminuria, UACR 45 mg/g",
        "Kidney filtration, eGFR 55",
        "ApoB 110 mg/dL",
        "Coronary calcium 350",
    ]

    assert "Tower shows RSS burden" not in html
    assert "ordered by contribution size" not in html
    assert "Largest contribution first" not in html
    assert [rows.index(label) for label in row_expected] == sorted(
        rows.index(label) for label in row_expected
    )


def test_targets_card_uses_compact_horizontal_target_line():
    patient = demo_patient()
    result, _rss_total, _contributions = run_patient(patient)

    html = _build_targets_html(result, patient)

    assert "targets-compact" in html
    assert "target-line" in html
    assert "target-item" in html
    assert "target-name" in html
    assert "target-goal" in html
    assert "target-strip" not in html
    assert "target-cell" not in html
    assert "LDL-C" in html
    assert "&lt;70 mg/dL" in html
    assert "ApoB" in html
    assert "&lt;80 mg/dL" in html
    assert "TG" in html
    assert "Current 180" in html
    assert "non-HDL-C" in html
    assert "&lt;100 mg/dL" in html
    assert "Current 157" in html
    assert "Calculated from total cholesterol minus HDL-C." in html
    assert "target-secondary" in html
    assert html.count("mg/dL") >= 4
    assert "High plaque burden (CAC 350)." in html
    assert "rcckm-metric-grid" not in html
    assert "target-separator" not in html
    assert "rcckm-metric" not in html


def test_assessment_candidates_are_compact_and_deduped():
    fake_st = _FakeStreamlit()

    render_report(fake_st, demo_patient())

    combined = "\n".join(str(message) for message in fake_st.messages)
    assert "detail-section-title" in combined
    assert "Assessment candidates" in combined
    assert "Clinical diagnoses and coding support" in combined
    assert "dx-panel" in combined
    assert "dx-column-panel" in combined
    assert "Accepted" in combined
    assert "Confirmed / accepted" not in combined
    assert "Confirmed by data" not in combined
    assert "Needs review" in combined
    assert "Review suggested" not in combined
    assert "ICD:" in combined
    assert "dx-code-chip" in combined
    assert "Evidence:" in combined
    assert "confirm_dx" not in combined
    button_labels = [message[1] for message in fake_st.messages if message[0] == "button"]
    assert "Review" not in button_labels
    assert "Suppress" not in button_labels


def test_assessment_candidate_rows_use_chips_and_clean_evidence():
    from core.engine import evaluate_patient
    from core.patient import Patient
    from core.diagnosis_workflow import prepare_diagnosis_display_entries
    from ui.diagnosis_confirm_panel import _candidate_html

    result = evaluate_patient(
        Patient(
            age=60,
            sex="male",
            cac=350,
            diabetes=True,
            egfr=55,
            uacr=45,
            triglycerides=180,
        )
    )
    rows = prepare_diagnosis_display_entries(result)
    html = "\n".join(_candidate_html(row, confirmed=True) for row in rows)

    assert "dx-code-chip" in html
    assert "ICD: I25.10" in html
    assert "ICD: E11.22" in html
    assert "ICD: N18.31" in html
    assert html.count("ICD: E11.22") == 1
    assert "HCC-supported" in html
    assert "Evidence: CAC ≥300" in html
    assert "Evidence: Diabetes documented; eGFR &lt;60; albuminuria present" in html
    assert "Evidence: eGFR 45-59" in html
    assert "Evidence: triglycerides ≥150 mg/dL" in html
    assert "diabetes flag" not in html
    assert "dominant_action" not in html
    assert "action_domains" not in html


def test_assessment_candidates_do_not_show_family_history_context_as_review_item():
    from core.results import DiagnosisCandidate, RCCKMResult
    from ui.diagnosis_confirm_panel import render_diagnosis_confirm_panel

    fake_st = _FakeStreamlit()
    result = RCCKMResult(
        diagnosis_candidates=[
            DiagnosisCandidate(
                "Premature family history of ASCVD",
                "Z82.49",
                "data-derived",
                "family history",
                False,
            )
        ]
    )

    render_diagnosis_confirm_panel(fake_st, result)

    combined = "\n".join(str(message) for message in fake_st.messages)
    assert "Premature family history of ASCVD" not in combined
    assert "Review suggested" not in combined
    assert "Suggested ICD: Z82.49" not in combined
    assert "confirm_dx" not in combined
    assert "Accept" not in combined
    assert "Suppress" not in combined
    assert not any(message[1] == "Confirm" for message in fake_st.messages if message[0] == "button")


def test_assessment_candidate_accept_does_not_apply_to_family_history_context():
    from core.results import DiagnosisCandidate, RCCKMResult
    from ui.diagnosis_confirm_panel import render_diagnosis_confirm_panel

    result = RCCKMResult(
        diagnosis_candidates=[
            DiagnosisCandidate(
                "Premature family history of ASCVD",
                "Z82.49",
                "data-derived",
                "family history",
                False,
            )
        ]
    )
    first = _FakeStreamlit(clicked_key="dx_accept__Premature family history of ASCVD")
    render_diagnosis_confirm_panel(first, result)

    assert "dx_review_accepted_ids" not in first.session_state
    assert first.rerun_requested is False

    second = _FakeStreamlit()
    second.session_state.update(first.session_state)
    render_diagnosis_confirm_panel(second, result)
    combined = "\n".join(str(message) for message in second.messages)

    assert "Premature family history of ASCVD" not in combined
    assert "ICD: Z82.49" not in combined
    assert "dx-status'>Review suggested" not in combined


def test_assessment_confirmed_rows_do_not_render_review_or_suppress_controls():
    from core.results import DiagnosisCandidate, RCCKMResult
    from ui.diagnosis_confirm_panel import render_diagnosis_confirm_panel

    result = RCCKMResult(
        diagnosis_candidates=[
            DiagnosisCandidate(
                "Severe subclinical coronary atherosclerosis",
                "I25.10",
                "data-derived",
            ),
            DiagnosisCandidate(
                "Type 2 diabetes mellitus",
                "E11.9",
                "data-derived",
            ),
        ]
    )

    fake_st = _FakeStreamlit()
    render_diagnosis_confirm_panel(fake_st, result)

    button_labels = [message[1] for message in fake_st.messages if message[0] == "button"]
    assert "Review" not in button_labels
    assert "Suppress" not in button_labels
    assert "Confirm" not in button_labels


def test_prioritize_linked_diagnoses_suppresses_fragment_duplicates():
    candidates = [
        DiagnosisCandidate("Type 2 diabetes mellitus", "E11.9", "data-derived"),
        DiagnosisCandidate(
            "Type 2 diabetes mellitus with diabetic chronic kidney disease",
            "E11.22",
            "data-derived",
        ),
        DiagnosisCandidate("Type 2 diabetes mellitus with albuminuria", "E11.29", "data-derived"),
        DiagnosisCandidate("Chronic kidney disease", "N18.9", "data-derived"),
        DiagnosisCandidate("Chronic kidney disease, stage 3a", "N18.31", "data-derived"),
        DiagnosisCandidate("Albuminuria", "R80.9", "data-derived"),
    ]

    visible = prioritize_linked_diagnoses(candidates)
    names = [candidate.name for candidate in visible]

    assert "Type 2 diabetes mellitus with diabetic chronic kidney disease" in names
    assert "Chronic kidney disease, stage 3a" in names
    assert "Type 2 diabetes mellitus" not in names
    assert "Type 2 diabetes mellitus with albuminuria" not in names
    assert "Chronic kidney disease" not in names
    assert "Albuminuria" not in names


def _value_by_label(widgets, label):
    for widget in widgets:
        if widget.label == label or str(widget.label).startswith(f"{label} "):
            return widget.value
    raise AssertionError(f"Missing widget {label}")


def _label_matches(widget, label):
    return widget.label == label or str(widget.label).startswith(f"{label} ")


def _click_button_by_label(app_test, label):
    for button in app_test.button:
        if button.label == label:
            return button.click().run(timeout=10)
    raise AssertionError(f"Missing button {label}")


def _assert_sidebar_navigation(app_test):
    assert len(app_test.radio) == 1
    assert app_test.radio[0].label == "Section"
    assert list(app_test.radio[0].options) == ["Worksheet", "Validation & Safety"]


def test_ingest_populates_editable_worksheet_fields():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py")
    at.run(timeout=10)
    _assert_sidebar_navigation(at)
    at.text_area[0].set_value(
        "60M BP 132/78 TC 210 LDL 142 HDL 42 TG 180 ApoB 118 "
        "Lp(a) 180 nmol/L A1c 7.1 eGFR 55 UACR 45 CAC 350 "
        "BMI 31 Father MI age 49 Current smoker on atorvastatin"
    )
    _click_button_by_label(at, "Parse")

    assert len(at.exception) == 0
    assert _value_by_label(at.text_input, "LDL-C") == "142"
    assert _value_by_label(at.text_input, "ApoB") == "118"
    assert _value_by_label(at.text_input, "A1c") == "7.1"
    assert _value_by_label(at.checkbox, "Smoking") is True
    assert _value_by_label(at.checkbox, "Lipid lowering") is True
    assert _value_by_label(at.selectbox, "Event type") == "MI"

    for widget in at.text_input:
        if _label_matches(widget, "LDL-C"):
            widget.set_value("130").run(timeout=10)
            break

    assert _value_by_label(at.text_input, "LDL-C") == "130"


def test_ingest_clear_button_clears_paste_and_parse_state_without_erasing_worksheet():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py")
    at.run(timeout=10)
    at.text_area[0].set_value(
        "60M BP 132/78 TC 210 LDL 142 HDL 42 TG 180 ApoB 118 "
        "A1c 7.1 eGFR 55 UACR 45 CAC 350"
    )
    _click_button_by_label(at, "Parse")

    assert len(at.exception) == 0
    assert _value_by_label(at.text_input, "LDL-C") == "142"
    assert at.session_state["parsed_ingest"]

    _click_button_by_label(at, "Clear")

    assert len(at.exception) == 0
    assert at.text_area[0].value == ""
    assert at.session_state["parsed_ingest"] == {}
    assert at.session_state["parse_report"]["parsed"] == {}
    assert _value_by_label(at.text_input, "LDL-C") == "142"


def test_app_loads_with_demo_patient_and_unified_input_flow():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py")
    at.run(timeout=10)

    assert len(at.exception) == 0
    _assert_sidebar_navigation(at)
    assert _value_by_label(at.text_input, "Age") == "55"
    assert _value_by_label(at.text_input, "SBP") == "132"
    assert _value_by_label(at.text_input, "DBP") == "82"
    assert _value_by_label(at.text_input, "CAC score") == "350"
    assert _value_by_label(at.text_input, "ApoB") == "110"
    assert _value_by_label(at.text_input, "A1c") == "7.1"
    assert _value_by_label(at.text_input, "eGFR") == "55"
    assert _value_by_label(at.text_input, "UACR") == "45"
    assert at.session_state["report_generated"] is False
    assert at.session_state["current_result"] is None
    assert at.session_state["active_patient"] is None
    assert any(button.label == "Parse" for button in at.button)
    assert any(button.label == "Clear" for button in at.button)
    assert any(button.label == "Interpret reviewed worksheet" for button in at.button)
    markdown_text = "\n".join(str(message.value) for message in at.markdown)
    assert "Review the worksheet, then click Interpret reviewed worksheet." in markdown_text
    assert "10-Year Cardiovascular Risk" not in markdown_text


def test_demo_case_gallery_loads_case_and_clears_report_state():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py")
    at.run(timeout=10)

    demo_select = next(widget for widget in at.selectbox if widget.label == "Demo case")
    demo_select.set_value("On-treatment above-target lipids")
    at.run(timeout=10)
    _click_button_by_label(at, "Load demo case")

    assert len(at.exception) == 0
    assert "Loaded demo case: On-treatment above-target lipids." in "\n".join(
        str(message.value) for message in at.success
    )
    assert _value_by_label(at.text_input, "LDL-C") == "124"
    assert _value_by_label(at.text_input, "ApoB") == "112"
    assert _value_by_label(at.text_input, "Height") == "65"
    assert _value_by_label(at.text_input, "Weight") == "173"
    assert at.session_state["parsed_ingest"] == {}
    assert at.session_state["report_generated"] is False
    assert at.session_state["current_result"] is None


def test_worksheet_numeric_labels_include_compact_units():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py")
    at.run(timeout=10)

    labels = {widget.label for widget in at.text_input}
    expected_labels = {
        label_with_unit("SBP", "mmHg"),
        label_with_unit("DBP", "mmHg"),
        label_with_unit("TC", "mg/dL"),
        label_with_unit("LDL-C", "mg/dL"),
        label_with_unit("HDL-C", "mg/dL"),
        label_with_unit("TG", "mg/dL"),
        label_with_unit("ApoB", "mg/dL"),
        label_with_unit("Lp(a)", "value"),
        label_with_unit("A1c", "%"),
        label_with_unit("Height", "in"),
        label_with_unit("Weight", "lb"),
        label_with_unit("BMI", "kg/m²"),
        label_with_unit("eGFR", "mL/min/1.73m²"),
        label_with_unit("Creatinine", "mg/dL"),
        label_with_unit("UACR", "mg/g"),
        label_with_unit("CAC score", "Agatston"),
        label_with_unit("hsCRP", "mg/L"),
    }

    assert expected_labels.issubset(labels)
    assert any(widget.label == "Lp(a) unit" for widget in at.selectbox)
    assert "US lipid units shown; convert mmol/L before entry." in "\n".join(
        caption.value for caption in at.caption
    )
    assert not any("<span" in label or "</span>" in label for label in labels)


def test_hash_worksheet_state_uses_canonical_fields_only():
    first = {
        "input_age": "55",
        "input_ldl_c": "132",
        "input_uacr": "",
        "unrelated_debug_toggle": True,
    }
    second = {
        "age": "55",
        "ldl_c": "132",
        "uacr": "",
        "unrelated_debug_toggle": False,
    }

    assert worksheet_payload_from_source(first)["uacr"] == ""
    assert hash_worksheet_state(first) == hash_worksheet_state(second)


def test_pasting_new_text_after_interpret_clears_existing_report():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py")
    at.run(timeout=10)
    _click_button_by_label(at, "Interpret reviewed worksheet")

    assert at.session_state["report_generated"] is True
    assert at.session_state["current_result"] is not None

    at.text_area[0].set_value("60M BP 132/78 TC 210 LDL 142 HDL 42 TG 180").run(timeout=10)

    assert len(at.exception) == 0
    assert at.session_state["report_generated"] is False
    assert at.session_state["current_result"] is None
    assert at.session_state["worksheet_dirty"] is True
    markdown_text = "\n".join(str(message.value) for message in at.markdown)
    assert "Worksheet changed. Click Interpret reviewed worksheet to update the report." in markdown_text


def test_parse_new_text_updates_worksheet_but_keeps_report_cleared_until_interpret():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py")
    at.run(timeout=10)
    _click_button_by_label(at, "Interpret reviewed worksheet")
    assert at.session_state["report_generated"] is True

    at.text_area[0].set_value("60M BP 132/78 TC 210 LDL 142 HDL 42 TG 180")
    _click_button_by_label(at, "Parse")

    assert len(at.exception) == 0
    assert _value_by_label(at.text_input, "LDL-C") == "142"
    assert at.session_state["report_generated"] is False
    assert at.session_state["current_result"] is None
    assert at.session_state["worksheet_dirty"] is True


def test_manual_edit_after_interpret_hides_stale_report_until_reinterpreted():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py")
    at.run(timeout=10)
    _click_button_by_label(at, "Interpret reviewed worksheet")
    assert at.session_state["report_generated"] is True

    for widget in at.text_input:
        if _label_matches(widget, "LDL-C"):
            widget.set_value("120").run(timeout=10)
            break

    assert len(at.exception) == 0
    assert at.session_state["report_generated"] is False
    assert at.session_state["current_result"] is None
    assert at.session_state["worksheet_dirty"] is True
    markdown_text = "\n".join(str(message.value) for message in at.markdown)
    assert "Worksheet changed. Click Interpret reviewed worksheet to update the report." in markdown_text

    _click_button_by_label(at, "Interpret reviewed worksheet")
    assert at.session_state["report_generated"] is True
    assert at.session_state["worksheet_dirty"] is False


def test_no_cac_button_sets_no_cac_state_and_numeric_entry_clears_it():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py")
    at.run(timeout=10)
    _click_button_by_label(at, "No CAC performed")

    assert _value_by_label(at.checkbox, "Show raw renderer HTML") is False
    assert _value_by_label(at.text_input, "CAC score") == ""
    assert at.session_state["input_cac_not_done"] is True
    assert "Plaque burden unmeasured." in "\n".join(caption.value for caption in at.caption)

    for widget in at.text_input:
        if _label_matches(widget, "CAC score"):
            widget.set_value("0").run(timeout=10)
            break

    assert _value_by_label(at.text_input, "CAC score") == "0"
    assert at.session_state["input_cac_not_done"] is False
    assert "CAC 0 entered." in "\n".join(caption.value for caption in at.caption)


def test_manual_patient_flow_produces_nonzero_rss_and_domain_rows():
    patient = build_patient_from_inputs(
        {
            "age": 60,
            "sex": "male",
            "cac": 350,
            "apob": 110,
            "a1c": 7.1,
            "diabetes": True,
            "egfr": 55,
            "uacr": 45,
            "tc": 190,
            "ldl_c": 115,
            "hdl_c": 50,
            "triglycerides": 150,
            "sbp": 128,
            "dbp": 78,
            "bmi": 28,
        }
    )

    result, rss_total, contributions = run_patient(patient)
    domain_subtotals = {}
    for contribution in contributions:
        domain_subtotals[contribution.domain] = (
            domain_subtotals.get(contribution.domain, 0) + contribution.points
        )

    assert rss_total > 0
    assert result.top_drivers
    assert domain_subtotals
    assert domain_subtotals["CAC"] == 30
    assert any(contribution.label == "ApoB elevation" for contribution in contributions)


def test_manual_app_run_shows_debug_payload_and_nonzero_rss():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py")
    at.run(timeout=10)

    values = {
        "Age": 60,
        "CAC score": 350,
        "ApoB": 110,
        "A1c": 7.1,
        "eGFR": 55,
        "UACR": 45,
        "TC": 190,
        "LDL-C": 115,
        "HDL-C": 50,
        "TG": 150,
        "SBP": 128,
        "DBP": 78,
        "BMI": 28,
    }
    for widget in at.text_input:
        if widget.label in values:
            widget.set_value(str(values[widget.label]))
    for checkbox in at.checkbox:
        if checkbox.label == "Diabetes":
            checkbox.set_value(True)

    _click_button_by_label(at, "Interpret reviewed worksheet")

    assert len(at.exception) == 0
    assert any("Debug: patient payload" in str(expander.label) for expander in at.expander)
    assert any('"cac": 350' in str(payload.value) for payload in at.json)
    markdown_text = "\n".join(str(message.value) for message in at.markdown)
    assert "10-Year Cardiovascular Risk" in markdown_text
    assert "padding: 16px 18px 18px" in markdown_text
    assert "Atherosclerotic event risk" in markdown_text
    assert '<div class="prevent-body">' in markdown_text
    assert '&lt;div class="prevent-body"&gt;' not in markdown_text
    assert '<div class="drivers-row">' not in markdown_text


def test_primary_report_copy_limits_repeated_ascvd_jargon():
    patient = demo_patient()
    result, rss_total, contributions = run_patient(patient)
    combined_html = "\n".join(
        [
            build_continuum_bar_html(patient, result),
            render_prevent_card(result),
            render_patient_roadmap(patient, result),
            build_rss_panel_html(rss_total, contributions),
            _build_targets_html(result, patient),
            build_clarifier_card_html(result),
            build_where_patient_falls_html(patient, result),
        ]
    )

    assert combined_html.count("ASCVD") <= 6
    assert "ASCVD-intensity phenotype" not in combined_html
    assert combined_html.count("Atherosclerotic events include heart attack") == 1
    assert "10-year ASCVD risk" in combined_html
    assert "30-year ASCVD risk" in combined_html

