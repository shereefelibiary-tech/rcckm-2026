# RCCKM Report Section Contract

This contract protects report hierarchy before parser validation. Clinician-facing interpretation appears first; patient-facing output appears last.

## 1. Risk Continuum

Purpose: show RCCKM level only.

May show:
- Level position.
- Short level meaning.
- Compact CAC/ASCVD context when relevant.

Must not show:
- Full PREVENT table.
- RSS contributor narrative.
- "YOU ARE HERE."
- Microscopic rationale text.

Source:
- `renderers/continuum_bar.py`
- `modules/levels/level_classifier.py`

Tests:
- `tests/unit/test_risk_continuum_renderer.py`
- `tests/golden_cases/test_level_taxonomy.py`

## 2. PREVENT card

Purpose: population risk estimate.

May show:
- 10-year and 30-year atherosclerotic event risk.
- Total cardiovascular event risk.
- PREVENT category.
- Model notes and missing PREVENT inputs.
- Clinical ASCVD note that PREVENT is not used for decisions.

Must not show:
- RSS drivers.
- RCCKM diagnosis/coding workflow.

Source:
- `renderers/prevent_card.py`

## 3. Why Risk Is Elevated

Purpose: RSS burden accumulator.

May show:
- RSS total.
- Tower segments.
- Contributor list.
- Additional context that does not score.

Must not show:
- Hidden RSS points.
- PREVENT category as RCCKM level.
- Different tower/list contributor sources.

Source:
- `modules/rss/engine.py`
- `renderers/rss_renderer.py`

## 4. CKM / KDIGO

Purpose: disease-stage context.

May show:
- CKM stage.
- eGFR stage.
- UACR/albuminuria stage when measured.
- Incomplete KDIGO state when UACR is missing.

Must not show:
- KDIGO A1 from missing UACR.
- Plaque diagnosis from PREVENT.

Source:
- `modules/ckm/engine.py`
- `modules/kdigo/engine.py`
- `ui/report_layout.py`

## 5. Where This Patient Falls

Purpose: clinician audit table.

May show:
- Inputs.
- Thresholds.
- Missingness.
- Level effect.
- Attention badge for clinically relevant missing UACR.

Must not show:
- Narrative duplicated from PREVENT or Action.
- Hidden missing-as-normal values.

Source:
- `renderers/where_patient_falls.py`

## 6. Clarifiers

Purpose: missing data that would clarify risk.

May show:
- UACR for kidney-risk completion.
- CAC when age eligible and treatment decision/intensity remains uncertain.
- Lp(a) once-in-lifetime measurement when relevant.
- ApoB/hsCRP/repeat fasting lipids when useful.

Must not show:
- Bulky completed-clarifier cards.
- CAC as a default recommendation for low-risk below-threshold patients.

Source:
- `modules/clarification/engine.py`
- `renderers/clarifier_renderer.py`

## 7. Targets + Action

Purpose: clinician plan.

May show:
- Target strip.
- Ordered natural-language plan.
- Internal scaffold order.

Must not show:
- "Supporting actions:"
- Duplicated labels such as "Aspirin: Aspirin..."
- CAC status as dominant action when therapy is already clearly indicated.

Source:
- `modules/targets/engine.py`
- `modules/actions/engine.py`
- `modules/actions/scaffold.py`
- `renderers/action_renderer.py`
- `renderers/targets_renderer.py`

## 8. Assessment Candidates

Purpose: diagnosis/coding support.

May show:
- Compact diagnosis candidates.
- ICD/HCC where available.
- Small review/accept controls.

Must not show:
- Premature family history as a default diagnosis candidate.
- Generic duplicate diagnoses when linked diagnoses are rendered.

Source:
- `modules/diagnoses/engine.py`
- `diagnosis_workflow.py`
- `ui/diagnosis_confirm_panel.py`

## 9. EMR Note

Purpose: copy/paste clinical documentation.

May show:
- Plain text risk summary.
- Assessment.
- Recommendations from the same action scaffold.

Must not show:
- Patient handout prose.
- Raw HTML.
- Repeated "data-derived" labels.

Source:
- `renderers/emr_renderer.py`
- `ui/emr_copy_box.py`

## 10. Patient Roadmap

Purpose: patient-facing handout.

May show:
- Patient-friendly risk explanation.
- Plain-language drivers.
- Goals and next steps.
- Copy patient roadmap plain-text renderer.

Must not show:
- Clinician audit density.
- Raw JSON or raw HTML.

Source:
- `renderers/patient_roadmap.py`
- `render_patient_roadmap_text(patient, result)`

Tests:
- `tests/unit/test_patient_roadmap_renderer.py`
- `tests/unit/test_ui_report_layout.py`
