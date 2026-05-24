# RCCKM-2026 Concordance With 2026 ACC/AHA Multisociety Dyslipidemia Guideline

Source reviewed: `C:\Users\shere\Desktop\blumenthal-et-al-2026-2026-acc-aha-aacvpr-abc-acpm-ada-ags-apha-aspc-nla-pcna-guideline-on-the-management-of.pdf`

This document separates official guideline behavior from RCCKM interpretation-layer behavior. RCCKM should make guideline-aligned prevention easier to enter, explain, and act on, while clearly labeling any RCCKM-specific interpretation as such.

## High-Confidence Guideline Anchors

### PREVENT

- Adults age 30-79 without clinical ASCVD or subclinical atherosclerosis and LDL-C 70-189 mg/dL: use PREVENT-ASCVD for 10-year risk.
- PREVENT 10-year categories:
  - Low: `<3%`
  - Borderline: `3% to <5%`
  - Intermediate: `5% to <10%`
  - High: `>=10%`
- PREVENT 30-year risk is especially relevant for age 30-59.
- PREVENT is population risk. It does not diagnose plaque and should not imply Level 4 unless plaque is measured.

### Primary Prevention Lipid Treatment Posture

- Low 10-year PREVENT risk `<3%`, LDL-C `<160`, and 30-year ASCVD risk `<10%`: lifestyle-focused prevention.
- Low 10-year PREVENT risk `<3%` with LDL-C 160-189 or 30-year ASCVD risk `>=10%`: moderate-intensity statin is reasonable if chosen after shared decision-making.
- Borderline risk `3% to <5%`: risk enhancers and shared decision-making; moderate-intensity statin is reasonable when selected.
- Intermediate risk `5% to <10%`: at least moderate-intensity statin recommended.
- High risk `>=10%`: high-intensity statin recommended.

### Targets

- Borderline/intermediate primary prevention when statin chosen:
  - LDL-C `<100 mg/dL`
  - non-HDL-C `<130 mg/dL`
- High 10-year PREVENT risk:
  - LDL-C `<70 mg/dL`
  - non-HDL-C `<100 mg/dL`
- Secondary prevention / very high risk:
  - LDL-C `<55 mg/dL`
  - non-HDL-C `<85 mg/dL`

### CAC

- CAC 0: therapy may be deferred only when higher-risk conditions are absent.
  - Do not de-risk diabetes age >40, current smoking, strong premature family history, severe hypercholesterolemia/FH.
- CAC 1-99 and below 75th percentile: moderate-intensity statin reasonable; LDL-C `<100`, non-HDL-C `<130`.
- CAC 100-299 or >=75th percentile: lipid-lowering therapy recommended; LDL-C `<70`, non-HDL-C `<100`.
- CAC 300-999: lipid-lowering therapy recommended; >=50% LDL-C reduction; LDL-C `<70`, non-HDL-C `<100`; intensification toward LDL-C `<55`, non-HDL-C `<85` may be reasonable.
- CAC >=1000: LDL-C `<55`, non-HDL-C `<85`.

### Diabetes

- Diabetes age 40-75: moderate-intensity statin indicated; LDL-C `<100`, non-HDL-C `<130`.
- Diabetes age 40-75 with multiple risk factors: high-intensity statin reasonable; LDL-C `<70`, non-HDL-C `<100`.
- Diabetes-specific enhancers include duration, albuminuria `>=30 mg/g`, eGFR `<60`, retinopathy, neuropathy, ABI `<0.9`.

### CKD

- CKD stage 3 or higher, age 40-75, LDL-C 70-189: moderate-intensity statin or moderate-intensity statin plus ezetimibe recommended.

### Lp(a)

- Measure Lp(a) at least once in adults.
- Risk-enhancing threshold:
  - `>=125 nmol/L`
  - or `>=50 mg/dL`
- Higher tiers:
  - `>=250 nmol/L` / `>=100 mg/dL`: about 2-fold risk
  - `>=430 nmol/L` / `>=180 mg/dL`: about 4-fold risk
- Visible UI label should be `Lp(a)`, not `Genetics` or `inherited risk`.

### ApoB

- ApoB is especially useful on lipid-lowering therapy in ASCVD, CKM syndrome, T2DM, and/or triglyceride elevation.
- ApoB may be reasonable in untreated patients to refine risk assessment.
- Guideline risk-enhancing threshold: ApoB `>=120 mg/dL`.
- RCCKM may still describe ApoB 100-119 mg/dL as elevated particle burden, but that is RCCKM interpretation, not the guideline risk-enhancer threshold.

### Hypertriglyceridemia

- Persistent TG risk enhancer:
  - fasting `>=150 mg/dL`
  - nonfasting `>=175 mg/dL`
- TG `>=500 mg/dL`: severe hypertriglyceridemia / pancreatitis-risk pathway.
- TG `>=1000 mg/dL`: very severe pathway; pancreatitis risk reduction and nutrition/lipid specialist pathway become central.

### hsCRP

- hsCRP `>=2 mg/L` is a risk enhancer when present on more than one occasion and without an identifiable underlying cause.
- A single hsCRP value should not be overcalled as a major driver by itself.

### Reproductive Risk Markers

- In adults without clinical ASCVD, reproductive history can personalize ASCVD risk assessment during primary-prevention lipid discussions.
- Supported markers include early menopause `<45`, premature menopause `<40`, preeclampsia, gestational hypertension, gestational diabetes, preterm delivery `<37 weeks`, small-for-gestational-age infant, recurrent spontaneous pregnancy loss, PCOS / irregular menses, and early menarche `<10` when documented.
- These markers are not PREVENT inputs and do not independently mandate treatment in RCCKM.
- RCCKM treats documented markers as mild RSS contributors/context and uses them to support risk discussion when lipid-lowering therapy is being considered.

## Module Concordance

| Module | Status | Notes |
| --- | --- | --- |
| `modules/prevent/engine.py` | Guideline aligned | PREVENT 10-year risk categories match `<3`, `3-<5`, `5-<10`, `>=10`. |
| `modules/prevent/official.py` / `modules/prevent/calculator.py` | Guideline aligned with gaps | Official coefficient path supports 10-year and 30-year outputs. PREVENT-age and percentile fields exist but remain `None` unless official source support is added. |
| `modules/targets/engine.py` | Updated / mostly aligned | CAC tiers, PREVENT categories, low-risk 30-year/LDL exceptions, diabetes age 40-75, and CKD stage 3+ pathways are represented. CAC percentile is not implemented. |
| `modules/risk_enhancers/engine.py` | Updated / mostly aligned | Lp(a) threshold aligned. ApoB `>=120` added as guideline enhancer. hsCRP wording now asks to confirm persistence. TG `>=150` is represented, but fasting vs nonfasting persistence is not fully modeled. |
| `modules/actions/engine.py` | Updated / partially aligned | TG `>=500` and `>=1000` now use pancreatitis-risk wording. Other action wording remains RCCKM clinical synthesis. |
| `modules/rss/engine.py` | RCCKM interpretation layer | RSS point values are RCCKM-specific and were not changed. ApoB 100-119 and single hsCRP may contribute to RSS as biologic burden, not as official guideline risk-enhancer thresholds. |
| `modules/risk_enhancers/reproductive.py` | Guideline-supporting context / RCCKM interpretation layer | Reproductive markers are captured as primary-prevention risk enhancers, shown in RSS/roadmap/context when present, and not used as PREVENT inputs. |
| `modules/drivers/engine.py` | RCCKM interpretation layer | Top drivers are display synthesis. Lp(a) is suppressed unless above threshold; hsCRP requires supportive context. |
| `modules/cac_recommendation/engine.py` | Partially aligned | CAC clarification logic is consistent with guideline concept, but percentile-based CAC is not implemented. |
| `modules/ckm/engine.py` | RCCKM interpretation layer | CKM staging supports context but is not itself a dyslipidemia guideline target algorithm. |
| `modules/kdigo/engine.py` | Guideline-supporting context | KDIGO staging supports CKD target/action paths. Chronicity/persistence is still a clinical review requirement. |
| `modules/diagnoses/engine.py` | RCCKM documentation layer | Diagnosis synthesis is for clinical documentation and should not be interpreted as guideline scoring. |
| `renderers/*` and `ui/*` | Presentation layer | Should display guideline-aligned wording without raw HTML or engine leakage. |

## Mismatches Found

1. Targets were being selected before calculated PREVENT values were copied into the patient object.
   - Impact: PREVENT-driven targets could be missed unless PREVENT values were manually supplied.
   - Status: fixed.

2. Diabetes and CKD stage 3+ target pathways were not represented in `modules/targets/engine.py`.
   - Impact: guideline-indicated target ranges could be absent when CAC was missing.
   - Status: fixed for diabetes age 40-75 and CKD stage 3+ age 40-75.

3. CAC 0 previously behaved like a broad de-risking path.
   - Impact: diabetes age >40, current smoking, premature family history, and severe LDL could be under-targeted.
   - Status: fixed for available fields.

4. ApoB risk-enhancer threshold was not separated from RCCKM ApoB interpretation.
   - Impact: ApoB 100-119 could be confused with the guideline enhancer threshold.
   - Status: ApoB `>=120 mg/dL` added to risk enhancers; RCCKM particle-burden interpretation remains separate.

5. hsCRP could read as a simple single-value risk enhancer.
   - Impact: guideline persistence requirement was not visible.
   - Status: wording changed to `hsCRP >=2 mg/L (confirm persistence)`.

6. Severe hypertriglyceridemia action was too narrow.
   - Impact: TG `>=500` emphasized repeat testing without enough pancreatitis-risk context; TG `>=1000` was not distinct.
   - Status: fixed in action plan wording.

## High-Confidence Changes Implemented

- Moved target selection in `core/engine.py` after PREVENT calculation and copied calculated PREVENT values into the in-flight patient object.
- Added diabetes age 40-75 target pathways.
- Added CKD stage 3+ age 40-75 target pathway.
- Added low 10-year PREVENT plus LDL-C 160-189 or 30-year risk `>=10%` moderate-target pathway.
- Guarded CAC 0 de-risking against higher-risk conditions.
- Added ApoB `>=120 mg/dL` as a guideline risk enhancer.
- Reworded hsCRP enhancer to require persistence confirmation.
- Added TG `>=500` and `>=1000` pancreatitis-risk action wording.

## Remaining Gaps / Do Not Blindly Change

- CAC percentile (`>=75th percentile`) is not implemented because the app currently lacks percentile calculation/input.
- LDL-C `>=190` / familial hypercholesterolemia pathway is only partly represented; a dedicated severe hypercholesterolemia target/action pathway should be added deliberately.
- PREVENT-age and percentile are not populated by the current adapter.
- ApoB on-treatment guidance is not fully modeled because treatment state and follow-up context remain limited.
- hsCRP persistence cannot be confirmed from a single value; UI should continue to treat this as review-needed context.
- TG fasting vs nonfasting and persistence are not fully modeled.
- Diabetes duration, retinopathy, neuropathy, and ABI are not currently worksheet fields.
