# RCCKM Discrepancy Review: synthetic_001_low_risk

Status: **FAIL**

## 1. risk level (FAIL)

- Expected: `"3A"`
- Actual: `"2A"`
- Rationale: Oracle assigns level from clinical ASCVD, CAC, CKM, and actionable risk burden.
- Clinical significance: Risk level mismatch can alter clinical posture and documentation.
- Suspected source: Risk continuum classification/export

## 2. lipid recommendation (WARN)

- Expected: `"discuss moderate-intensity statin"`
- Actual: `"RISK CONTINUUM CKM\n\nLevel: 2A - early isolated risk signal.\nPREVENT: unavailable.\nCKM/Kidney/Plaque: CKM stage 0; kidney G2A1; CAC 0.\nContext: Filipino ancestry.\n\nAssessment:\n- No diagnosis candidates generated.\n\nRecommendations:\n1. Lipids: No lipid-lowering medication indicated.\n2. Plaque: CAC 0.\n3. Kidney: Stable.\n4. BP: At goal.\n5. Glycemia: No glycemic action; A1c 5.3.\n6. Aspirin: Not indicated.\nNo active domain changes from current risk profile."`
- Rationale: Oracle applies ApoB-first lipid logic with LDL-C, ApoB, CAC, ASCVD, and kidney/risk-enhancer context.
- Clinical significance: Lipid mismatch may change whether therapy is started, continued, or intensified.
- Suspected source: Lipid action wording or treatment-posture selection
