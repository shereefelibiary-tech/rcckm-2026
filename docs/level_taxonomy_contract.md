# RCCKM Level Taxonomy Contract

RCCKM is not a PREVENT category display. PREVENT is a population risk estimate; RCCKM level is an interpretation of early cardiometabolic trajectory, measured plaque, organ-risk signals, and clinical ASCVD.

## Level 1 - minimal risk signal

Minimal risk signal.

Expected pattern:
- Low PREVENT 10-year risk.
- Low 30-year PREVENT risk if available.
- RSS near zero or no meaningful contributors.
- No CKM risk signals.
- No measured plaque.
- No clinical ASCVD.
- No major missing-data issue.

Treatment posture: lifestyle-based prevention.

## Level 2A - early isolated risk signal

One mild or early signal is present, but no clear convergence yet.

Examples:
- Isolated prediabetes.
- Mild triglyceride elevation.
- Mild ApoB/non-HDL elevation.
- Isolated obesity, MASLD, or OSA context.
- Single mild risk enhancer.
- Low 10-year and low 30-year PREVENT risk.
- No albuminuria.
- No measured plaque.
- No treatment-forward guideline pathway.

Treatment posture: lifestyle and periodic reassessment.

## Level 2B - converging early risk signals

Multiple early signals are present, but the case is not yet treatment-forward by 30-year risk, LDL threshold, albuminuria, CAC, diabetes, CKD, or high PREVENT.

Examples:
- Prediabetes plus triglyceride elevation plus obesity/MASLD/OSA.
- Mild ApoB/non-HDL burden plus reproductive risk marker.
- Lp(a) context plus mild atherogenic burden or risk-enhancer context with low 30-year risk and no plaque.
- Multiple small RSS contributors.
- No measured plaque.
- No UACR >=30.
- No 30-year PREVENT ASCVD >=10.
- No LDL-C >=160.
- No diabetes/CKD treatment pathway.

Treatment posture: lifestyle plus clinician-patient risk discussion.

## Level 3A - elevated long-term risk trajectory

Long-term or cumulative risk is treatment-relevant, even if short-term PREVENT risk is low or borderline.

Core triggers:
- Age 30-59 and PREVENT 30-year ASCVD risk >=10%.
- LDL-C 160-189 in primary prevention.
- Low 10-year risk but treatment-relevant cumulative atherogenic exposure.
- Borderline PREVENT plus major enhancer burden where treatment discussion is guideline-supported.
- No measured plaque requiring Level 4/5.
- No clinical ASCVD.
- No major kidney/albuminuria/diabetes organ-risk pattern requiring Level 3B or higher.

Treatment posture: prevention discussion; moderate-intensity lipid-lowering therapy may be reasonable depending pathway.

## Level 3B - actionable early CKM / atherogenic / kidney burden

Treatment-relevant long-term risk plus actionable biology or an early organ-risk signal. This is the central RCCKM "not an event yet, but no longer ignorable" zone.

Core triggers:
- PREVENT 30-year ASCVD risk >=10% plus biologic/CKM risk burden.
- UACR >=30, especially with BP, prediabetes/diabetes, metabolic risk, or elevated PREVENT.
- Diabetes without clinical ASCVD but with additional risk burden.
- CKD/eGFR <60 without clinical ASCVD.
- Borderline/intermediate PREVENT plus albuminuria or multiple CKM signals.
- ApoB/non-HDL/LDL burden plus metabolic/kidney/reproductive/enhancer burden.
- BP-treated/elevated BP plus albuminuria, prediabetes, or metabolic burden.
- Lp(a) elevation plus enough metabolic, kidney, atherogenic, or PREVENT trajectory burden to make the pattern treatment-relevant.
- Multiple RSS contributors when the combined pattern is clinically actionable rather than merely mild.

Level 3B does not mean plaque is present. If CAC is missing, plaque remains unmeasured and no subclinical atherosclerosis diagnosis is generated.

Treatment posture: domain action and/or treatment-forward clinician-patient discussion.

## Level 4 - subclinical atherosclerosis present

Measured plaque is present without clinical ASCVD and below the RCCKM Level 5 plaque pathway.

Examples:
- CAC >0 and <300.
- Other measured subclinical plaque evidence if supported.

Do not assign Level 4 from PREVENT alone.

## Level 5 - very high risk / ASCVD-intensity pathway

Clinical ASCVD or very high plaque burden.

Examples:
- Clinical ASCVD.
- CAC >=300 if RCCKM maps this to Level 5.
- CAC >=1000 extensive plaque / very-high target pathway.

Clinical ASCVD overrides PREVENT and CAC de-risking.

## Engine Contract

Primary classifier:
- `modules.levels.level_classifier.classify_rcckm_level(patient, result, rss_result=None, diagnosis_context=None)`

Compatibility helper:
- `modules.levels.definitions.classify_continuum_position(patient, result)`

Return fields:
- `level`
- `label`
- `short_reason`
- `drivers`
- `prevent_category`
- `plaque_status`
- `treatment_posture`

Invariants:
- PREVENT category must not overwrite RCCKM level.
- PREVENT category is displayed separately.
- Age 30-59 plus PREVENT 30-year ASCVD >=10 sets minimum Level 3A unless plaque/ASCVD is higher.
- UACR >=30 plus cardiometabolic burden sets Level 3B.
- CAC missing never creates a plaque diagnosis.
- CAC >0 creates measured plaque pathway.
- Clinical ASCVD overrides all.
- LDL-C >=190 should never be Level 1/LOW.
- CAC 0 does not de-risk LDL-C >=190/FH or clinical ASCVD.
- PREVENT is validated for primary-prevention adults age 30-79 and is not used to de-risk established ASCVD, LDL-C >=190, or suspected FH/HeFH.
- Secondary-prevention targets differ from primary-prevention targets: high-risk ASCVD uses LDL-C <70 / non-HDL-C <100, while very-high-risk ASCVD uses LDL-C <55 / non-HDL-C <85.
- Ancestry, reproductive, inflammatory, and HIV markers personalize risk and may contribute to RSS/context, but they are not diagnosis candidates by default.
