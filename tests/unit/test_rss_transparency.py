from html.parser import HTMLParser

from core.patient import Patient
from modules.rss.engine import (
    get_missing_clarifiers,
    get_risk_enhancers_context,
    get_rss_contributors,
)
from renderers.clarifier_renderer import build_clarifier_card_html
from renderers.rss_renderer import build_rss_panel_html
from renderers.rss_renderer import get_rss_display_items
from ui.report_layout import run_patient


def _labels(items):
    return [item.label for item in items]


def _details(items):
    return [item.detail for item in items]


def _tower_html(html):
    return html.split('<div class="rss-tower">', 1)[1].split('<div class="rss-list-zone rss-drivers">', 1)[0]


def _row_html(html):
    return html.split('<div class="rss-driver-list', 1)[1]


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._ignored_tags = []
        self.text_parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"style", "script"}:
            self._ignored_tags.append(tag)

    def handle_endtag(self, tag):
        if self._ignored_tags and self._ignored_tags[-1] == tag:
            self._ignored_tags.pop()

    def handle_data(self, data):
        if not self._ignored_tags:
            text = data.strip()
            if text:
                self.text_parts.append(text)


def _visible_text(html):
    parser = _VisibleTextParser()
    parser.feed(html)
    return " ".join(parser.text_parts)


def test_render_rss_html_no_raw_tags_or_escaped_fragments():
    patient = Patient(age=55, sex="male", apob=106, triglycerides=182, masld=True)
    result, rss_total, contributions = run_patient(patient)

    rendered = build_rss_panel_html(rss_total, contributions, result)
    text = _visible_text(rendered)

    assert "</div>" not in text
    assert "<div" not in text
    assert "&lt;div" not in text
    assert "&lt;/div&gt;" not in text


def test_render_rss_html_has_balanced_explicit_layout_zones():
    patient = Patient(age=55, sex="male", apob=106, triglycerides=182, masld=True)
    result, rss_total, contributions = run_patient(patient)

    rendered = build_rss_panel_html(rss_total, contributions, result)

    assert rendered.count('class="rss-card rss-module rc-panel"') == 1
    assert rendered.count('class="rss-body rss-module-body"') == 1
    assert rendered.count('class="rss-tower-zone"') == 1
    assert rendered.count('class="rss-list-zone rss-drivers"') == 1
    assert rendered.count("<div") == rendered.count("</div>")


def test_rss_layout_contains_tower_and_list_zones_without_clarifiers():
    patient = Patient(age=55, sex="male", prevent_10y_ascvd=6.0, cac=None, apob=106)
    result, rss_total, contributions = run_patient(patient)

    rendered = build_rss_panel_html(rss_total, contributions, result)

    assert 'class="rss-tower-zone"' in rendered
    assert 'class="rss-list-zone rss-drivers"' in rendered
    assert "Missing clarifiers" not in rendered
    assert "Plaque burden clarification" not in rendered
    assert "UACR missing" not in rendered


def test_rss_title_and_contributor_labels_are_concise():
    patient = Patient(
        age=55,
        sex="male",
        a1c=6.0,
        hscrp=2.2,
        triglycerides=186,
        apob=104,
        uacr=45,
        egfr=55,
        cac=350,
        family_history_relationship="father",
        family_history_event_type="MI",
        family_history_age_at_event=52,
    )
    result, rss_total, contributions = run_patient(patient)

    rendered = build_rss_panel_html(rss_total, contributions, result)
    rows = _row_html(rendered)

    assert "Where the Risk Is Coming From" in rendered
    assert "Why Risk Is Elevated" not in rendered
    assert '<strong class="rss-row-label">A1c</strong>' in rows
    assert '<strong class="rss-row-label">hsCRP</strong>' in rows
    assert '<strong class="rss-row-label">Triglycerides</strong>' in rows
    assert '<strong class="rss-row-label">ApoB / particle burden</strong>' in rows
    assert '<strong class="rss-row-label">Albuminuria</strong>' in rows
    assert '<strong class="rss-row-label">eGFR</strong>' in rows
    assert '<strong class="rss-row-label">Family history</strong>' in rows
    assert '<strong class="rss-row-label">Coronary calcium</strong>' in rows
    assert "Elevated inflammatory biomarker" not in rows
    assert "Elevated triglycerides" not in rows
    assert "Elevated particle burden" not in rows
    assert "Prediabetes-range A1c" not in rows
    assert "Diabetes-range A1c" not in rows


def test_rss_markers_and_points_use_consistent_visual_system():
    patient = Patient(age=55, sex="male", apob=106, triglycerides=182, masld=True)
    result, rss_total, contributions = run_patient(patient)

    rendered = build_rss_panel_html(rss_total, contributions, result)

    assert ".rss-marker," in rendered
    assert ".rss-driver-color {" in rendered
    assert "height: 9px;" in rendered
    assert "width: 9px;" in rendered
    assert "border-radius: 3px;" in rendered
    assert ".rss-driver-row--tiny .rss-driver-color" not in rendered
    assert ".rss-driver-row--mild .rss-driver-color" not in rendered
    assert ".rss-row-points," in rendered
    assert ".rss-driver-points {" in rendered
    assert "color: var(--rc-black);" in rendered
    assert 'class="rss-row-points rss-driver-points" style=' not in rendered


def test_prediabetes_range_a1c_appears_as_rss_contributor_when_scored():
    patient = Patient(age=50, sex="male", a1c=5.7)
    result, rss_total, contributions = run_patient(patient)

    html = build_rss_panel_html(rss_total, contributions, result)
    display = get_rss_display_items(result, contributions, rss_total)
    tower = _tower_html(html)
    rows = _row_html(html)

    assert any(item.label == "A1c elevation" for item in get_rss_contributors(result))
    assert rss_total == 2
    assert sum(item["points"] for item in display["contributors"] if item["stack_in_tower"]) == rss_total
    assert "A1c" in html
    assert "A1c 5.7%" in tower
    assert "A1c 5.7%" in rows
    assert '<span class="rss-tower-label">A1c 5.7%</span>' not in tower


def test_diabetes_range_a1c_appears_as_rss_contributor_when_scored():
    patient = Patient(age=55, sex="male", diabetes=True, a1c=7.1)
    result, rss_total, contributions = run_patient(patient)

    assert any(item.label == "Diabetes" for item in get_rss_contributors(result))
    html = build_rss_panel_html(rss_total, contributions, result)

    assert "A1c" in html
    assert "A1c 7.1%" in html


def test_diabetes_range_a1c_appears_as_rss_contributor_when_diabetes_flag_absent():
    patient = Patient(age=55, sex="male", diabetes=False, a1c=7.1)
    result, rss_total, contributions = run_patient(patient)

    html = build_rss_panel_html(rss_total, contributions, result)

    assert any(item.label == "A1c elevation" for item in get_rss_contributors(result))
    assert rss_total == 8
    assert "A1c" in html
    assert "A1c 7.1%" in html


def test_lpa_80_is_tiny_not_major_and_stacks_when_scored():
    patient = Patient(age=55, sex="male", lp_a_value=80, lp_a_unit="nmol/L")
    result, rss_total, contributions = run_patient(patient)
    html = build_rss_panel_html(rss_total, contributions, result)
    tower = _tower_html(html)
    rows = _row_html(html)

    assert any(item.label == "Elevated Lp(a)" and item.points == 2 for item in get_rss_contributors(result))
    assert "major driver" not in html.lower()
    assert rss_total == 2
    assert "Lp(a) 80 nmol/L" in tower
    assert "Lp(a) 80 nmol/L" in rows
    assert '<span class="rss-tower-label">Lp(a) 80 nmol/L</span>' not in tower


def test_lpa_168_appears_as_elevated_rss_contributor():
    patient = Patient(age=55, sex="male", lp_a_value=168, lp_a_unit="nmol/L")
    result, rss_total, contributions = run_patient(patient)
    html = build_rss_panel_html(rss_total, contributions, result)

    assert any(item.label == "Elevated Lp(a)" for item in get_rss_contributors(result))
    assert "Lp(a)" in html
    assert "Lp(a) 168 nmol/L" in html


def test_apob_and_lpa_scored_items_both_stack_in_tower_and_list():
    patient = Patient(age=55, sex="male", apob=106, lp_a_value=168, lp_a_unit="nmol/L")
    result, rss_total, contributions = run_patient(patient)
    html = build_rss_panel_html(rss_total, contributions, result)
    display = get_rss_display_items(result, contributions, rss_total)
    tower = _tower_html(html)
    rows = _row_html(html)

    assert rss_total == 16
    assert [item["id"] for item in display["contributors"]] == ["lpa", "apob"]
    assert sum(item["points"] for item in display["contributors"] if item["stack_in_tower"]) == rss_total
    assert 'data-rss-id="lpa"' in tower
    assert 'data-rss-id="apob"' in tower
    assert "Lp(a) 168 nmol/L" in rows
    assert "ApoB 106 mg/dL" in rows


def test_family_history_context_distinguishes_premature_and_nonpremature():
    premature = Patient(
        age=50,
        sex="male",
        family_history_relationship="father",
        family_history_event_type="MI",
        family_history_age_at_event=52,
    )
    nonpremature = Patient(
        age=50,
        sex="male",
        family_history_relationship="father",
        family_history_event_type="MI",
        family_history_age_at_event=61,
    )

    premature_result, _, _ = run_patient(premature)
    nonpremature_result, _, _ = run_patient(nonpremature)

    assert any(item.label == "Premature family history" for item in get_rss_contributors(premature_result))
    assert "Family history" not in _labels(get_risk_enhancers_context(premature_result))
    assert "Family history" in _labels(get_risk_enhancers_context(nonpremature_result))
    assert "Premature family history" not in _labels(get_risk_enhancers_context(nonpremature_result))
    assert "Father MI age 61" in _details(get_risk_enhancers_context(nonpremature_result))


def test_premature_family_history_stacks_when_scored():
    patient = Patient(
        age=50,
        sex="male",
        family_history_relationship="father",
        family_history_event_type="MI",
        family_history_age_at_event=52,
    )
    result, rss_total, contributions = run_patient(patient)
    html = build_rss_panel_html(rss_total, contributions, result)
    tower = _tower_html(html)
    rows = _row_html(html)

    assert rss_total == 3
    assert "Father MI age 52" in tower
    assert "Father MI age 52" in rows
    assert '<span class="rss-tower-label">Father MI age 52</span>' not in tower


def test_small_condition_contributors_stack_individually():
    patient = Patient(age=55, sex="female", osa=True, psoriasis=True, masld=True)
    result, rss_total, contributions = run_patient(patient)
    html = build_rss_panel_html(rss_total, contributions, result)
    tower = _tower_html(html)
    rows = _row_html(html)

    assert rss_total == 6
    assert "OSA" in tower
    assert "Psoriasis" in tower
    assert "MASLD" in tower
    assert "OSA" in rows
    assert "Psoriasis" in rows
    assert "MASLD" in rows
    assert '<span class="rss-tower-label">OSA</span>' not in tower
    assert '<span class="rss-tower-label">Psoriasis</span>' not in tower
    assert '<span class="rss-tower-label">MASLD</span>' not in tower


def test_missing_lpa_appears_as_missing_clarifier_when_relevant():
    patient = Patient(age=55, sex="male", ldl_c=130, lp_a_value=None)
    result, rss_total, contributions = run_patient(patient)
    html = build_rss_panel_html(rss_total, contributions, result)
    clarifier_html = build_clarifier_card_html(result)

    assert "Lp(a)" in _labels(get_missing_clarifiers(result))
    assert "Missing clarifiers" not in html
    assert "One-time risk assessment" not in html
    assert "Lp(a)" in clarifier_html
    assert "Lp(a) measurement" in clarifier_html


def test_missing_a1c_and_family_history_do_not_render_as_normal():
    patient = Patient(age=55, sex="male")
    result, rss_total, contributions = run_patient(patient)
    html = build_rss_panel_html(rss_total, contributions, result)

    assert "normal A1c" not in html.lower()
    assert "no family history" not in html.lower()


def test_tower_list_consistency_for_all_positive_contributors():
    patient = Patient(
        age=60,
        sex="male",
        apob=106,
        lp_a_value=168,
        lp_a_unit="nmol/L",
        hscrp=5.2,
        triglycerides=520,
        smoker=True,
    )
    result, rss_total, contributions = run_patient(patient)
    html = build_rss_panel_html(rss_total, contributions, result)
    display = get_rss_display_items(result, contributions, rss_total)
    tower = _tower_html(html)
    rows = _row_html(html)

    for item in display["contributors"]:
        assert item["points"] > 0
        assert f'data-rss-id="{item["id"]}"' in tower
        assert item["value_label"] in rows
    assert sum(item["points"] for item in display["contributors"] if item["stack_in_tower"]) == rss_total


def test_many_small_contributors_remain_complete_and_transparent():
    patient = Patient(
        age=55,
        sex="female",
        apob=80,
        a1c=5.7,
        uacr=31,
        hscrp=2.1,
        osa=True,
        psoriasis=True,
        masld=True,
    )
    result, rss_total, contributions = run_patient(patient)
    html = build_rss_panel_html(rss_total, contributions, result)
    display = get_rss_display_items(result, contributions, rss_total)
    tower = _tower_html(html)
    rows = _row_html(html)

    expected_labels = {
        "A1c elevation",
        "Inflammatory risk",
        "OSA",
        "MASLD",
        "Psoriasis",
        "Albuminuria",
        "ApoB elevation",
    }
    assert {item.label for item in get_rss_contributors(result)} == expected_labels
    assert rss_total == 22
    assert sum(item["points"] for item in display["contributors"] if item["stack_in_tower"]) == rss_total
    for item in display["contributors"]:
        assert f'data-rss-id="{item["id"]}"' in tower
        assert item["value_label"] in rows


def test_many_contributors_case_stays_complete_without_forcing_tiny_tower_labels():
    patient = Patient(
        age=55,
        sex="male",
        cac=350,
        apob=110,
        egfr=55,
        uacr=45,
        triglycerides=180,
        lp_a_value=80,
        lp_a_unit="nmol/L",
        family_history_relationship="father",
        family_history_event_type="MI",
        family_history_age_at_event=52,
        osa=True,
        masld=True,
        hscrp=2.4,
        diabetes=True,
        a1c=7.1,
    )
    result, rss_total, contributions = run_patient(patient)
    html = build_rss_panel_html(rss_total, contributions, result)
    display = get_rss_display_items(result, contributions, rss_total)
    tower = _tower_html(html)
    rows = _row_html(html)

    expected_ids = {
        "cac",
        "apob",
        "egfr",
        "uacr",
        "triglycerides",
        "lpa",
        "family_history",
        "osa",
        "masld",
        "hscrp",
        "diabetes",
    }
    assert {item["id"] for item in display["contributors"]} == expected_ids
    assert sum(item["points"] for item in display["contributors"] if item["stack_in_tower"]) == rss_total
    assert 'class="rss-driver-list rss-driver-list--scroll"' not in html
    assert "height: 440px;" in html
    assert "rss-card" in html
    assert "rss-title" in html
    assert "rss-score-chip" in html
    assert "rss-contributor-heading" in html
    assert "rss-row-label" in html
    assert "rss-row-value" in html
    assert "rss-row-points" in html
    assert "rss-marker" in html
    assert "rss-tower-callout" not in html
    assert "Missing clarifiers" not in html
    assert '<span class="rss-tower-label">CAC 350</span>' in tower
    assert '<span class="rss-tower-label">ApoB 110 mg/dL</span>' in tower
    assert '<span class="rss-tower-label">A1c 7.1%</span>' in tower
    assert '<span class="rss-tower-label">UACR 45 mg/g</span>' in tower
    assert '<span class="rss-tower-label">eGFR 55</span>' not in tower
    assert '<span class="rss-tower-label">Lp(a) 80 nmol/L</span>' not in tower
    assert 'data-rss-id="lpa"' in tower
    assert 'title="Lp(a) - Lp(a) 80 nmol/L - +2 RSS points"' in tower
    for item in display["contributors"]:
        assert f'data-rss-id="{item["id"]}"' in tower
        assert f'data-rss-id="{item["id"]}"' in rows
        assert item["value_label"] in rows


def test_rss_contributor_typography_is_consistent_sans_serif():
    patient = Patient(
        age=55,
        sex="male",
        cac=350,
        apob=110,
        egfr=55,
        uacr=45,
        triglycerides=180,
        a1c=7.1,
        diabetes=True,
    )
    result, rss_total, contributions = run_patient(patient)
    html = build_rss_panel_html(rss_total, contributions, result)

    assert ".rss-card *" in html
    assert "font-family: var(--rc-font-body)" in html
    heading_block = html.split(".rss-contributor-heading", 1)[1].split("}", 1)[0]
    title_block = html.split(".rss-title", 1)[1].split("}", 1)[0]
    label_block = html.split(".rss-row-label", 1)[1].split("}", 1)[0]
    value_block = html.split(".rss-row-value", 1)[1].split("}", 1)[0]
    points_block = html.split(".rss-row-points", 1)[1].split("}", 1)[0]

    assert "font-family: var(--rc-font-body)" in heading_block
    assert "font-weight: 800" in heading_block
    assert "font-size: 1.0rem" in heading_block
    assert "font-family: var(--rc-font-title)" not in heading_block
    assert "font-weight: 800" in title_block
    assert "font-weight: 750" in label_block
    assert "font-size: 0.86rem" in label_block
    assert "font-weight: 500" in value_block
    assert "font-size: 0.76rem" in value_block
    assert "font-weight: 800" in points_block
    assert "font-size: 0.82rem" in points_block
    assert "font-variant-numeric: tabular-nums" in points_block


def test_long_contributor_list_uses_clean_scroll_area_without_hiding_rows():
    patient = Patient(
        age=55,
        sex="female",
        cac=350,
        apob=110,
        egfr=55,
        uacr=45,
        triglycerides=180,
        lp_a_value=168,
        lp_a_unit="nmol/L",
        family_history_relationship="father",
        family_history_event_type="MI",
        family_history_age_at_event=52,
        osa=True,
        masld=True,
        hscrp=2.4,
        diabetes=True,
        a1c=7.1,
        psoriasis=True,
        sle=True,
        preeclampsia=True,
    )
    result, rss_total, contributions = run_patient(patient)
    html = build_rss_panel_html(rss_total, contributions, result)
    display = get_rss_display_items(result, contributions, rss_total)
    tower = _tower_html(html)
    rows = _row_html(html)

    assert len(display["contributors"]) > 12
    assert "rss-driver-list--scroll" in html
    assert sum(item["points"] for item in display["contributors"] if item["stack_in_tower"]) == rss_total
    assert '<span class="rss-tower-label">Lp(a) 168 nmol/L</span>' in tower
    assert 'title="Lp(a) - Lp(a) 168 nmol/L - +8 RSS points"' in tower
    assert "rss-tower-callout" not in html
    for item in display["contributors"]:
        assert f'data-rss-id="{item["id"]}"' in tower
        assert f'data-rss-id="{item["id"]}"' in rows


def test_low_rss_18_case_has_callout_and_keeps_exact_tower_scale():
    patient = Patient(
        age=55,
        sex="male",
        a1c=5.7,
        apob=106,
        triglycerides=182,
        osa=True,
        masld=True,
    )
    result, rss_total, contributions = run_patient(patient)
    html = build_rss_panel_html(rss_total, contributions, result)
    display = get_rss_display_items(result, contributions, rss_total)
    tower = _tower_html(html)
    rows = _row_html(html)

    assert rss_total == 18
    assert {item["id"] for item in display["contributors"]} == {
        "a1c",
        "apob",
        "triglycerides",
        "osa",
        "masld",
    }
    assert sum(item["points"] for item in display["contributors"] if item["stack_in_tower"]) == rss_total
    assert tower.count('class="rss-tower-segment"') == 5
    assert 'style="height: 82.00%;"' in tower
    assert 'data-rss-id="a1c"' in tower
    assert 'data-rss-id="apob"' in tower
    assert 'data-rss-id="triglycerides"' in tower
    assert 'data-rss-id="osa"' in tower
    assert 'data-rss-id="masld"' in tower
    assert "A1c" in rows
    assert "A1c 5.7%" in rows
    assert "ApoB 106 mg/dL" in rows
    assert "TG 182 mg/dL" in rows
    assert "OSA" in rows
    assert "MASLD" in rows
    assert 'data-rss-low-callout="true"' in html
    assert "Top:" in html
    assert "ApoB 106 mg/dL" in html
    assert "5 contributors total" in html
    assert "rss-tower-callout" not in html
    assert "Missing clarifiers" not in html


def test_moderate_rss_43_case_uses_readable_labels_only_without_callout():
    patient = Patient(
        age=55,
        sex="male",
        cac=38,
        apob=106,
        egfr=55,
        uacr=45,
        triglycerides=182,
        lp_a_value=168,
        lp_a_unit="nmol/L",
        a1c=5.7,
    )
    result, rss_total, contributions = run_patient(patient)
    html = build_rss_panel_html(rss_total, contributions, result)
    display = get_rss_display_items(result, contributions, rss_total)
    tower = _tower_html(html)
    rows = _row_html(html)

    assert rss_total == 43
    assert {item["id"] for item in display["contributors"]} == {
        "a1c",
        "cac",
        "apob",
        "egfr",
        "uacr",
        "triglycerides",
        "lpa",
    }
    assert sum(item["points"] for item in display["contributors"] if item["stack_in_tower"]) == rss_total
    assert tower.count('class="rss-tower-segment"') == len(display["contributors"])
    assert 'data-rss-low-callout="true"' not in html
    assert '<span class="rss-tower-label">CAC 38</span>' in tower
    assert '<span class="rss-tower-label">Lp(a) 168 nmol/L</span>' in tower
    assert '<span class="rss-tower-label">ApoB 106 mg/dL</span>' in tower
    assert '<span class="rss-tower-label">eGFR 55</span>' not in tower
    assert '<span class="rss-tower-label">TG 182 mg/dL</span>' not in tower
    for item in display["contributors"]:
        assert f'data-rss-id="{item["id"]}"' in tower
        assert f'data-rss-id="{item["id"]}"' in rows
        assert item["value_label"] in rows
    assert "Missing clarifiers" not in html


def test_cac_missing_clarifier_is_separate_from_rss_card():
    patient = Patient(age=55, sex="male", prevent_10y_ascvd=6.0, cac=None)
    result, rss_total, contributions = run_patient(patient)
    rss_html = build_rss_panel_html(rss_total, contributions, result)
    clarifier_html = build_clarifier_card_html(result)

    assert "Missing clarifiers" not in rss_html
    assert "plaque burden clarification" not in rss_html.lower()
    assert "CAC" in clarifier_html
    assert "plaque burden clarification" in clarifier_html


def test_hiv_rss_label_is_not_generic_inflammatory_disease():
    patient = Patient(age=55, sex="male", hiv=True, inflammatory_disease=False)
    result, rss_total, contributions = run_patient(patient)
    html = build_rss_panel_html(rss_total, contributions, result)

    assert any(item.label == "HIV" for item in get_rss_contributors(result))
    assert "HIV-related risk enhancer" in html
    assert "HIV is shown as its own guideline risk-enhancing pathway." in html
    assert "Inflammatory disease" not in html

