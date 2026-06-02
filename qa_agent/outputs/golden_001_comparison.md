# RCCKM QA Comparison: golden_001

Status: **PASS**

| Status | Category | Severity | Key | Expected | Actual | Explanation |
|---|---|---|---|---|---|---|
| pass | parser | low | `age` | 55 | 55 | Parsed `age` matched expected value. |
| pass | parser | low | `sex` | "male" | "male" | Parsed `sex` matched expected value. |
| pass | parser | low | `ldl_c` | 142 | 142.0 | Parsed `ldl_c` matched expected value. |
| pass | parser | low | `apob` | 116 | 116.0 | Parsed `apob` matched expected value. |
| pass | parser | low | `a1c` | 6.3 | 6.3 | Parsed `a1c` matched expected value. |
| pass | parser | low | `egfr` | 72 | 72.0 | Parsed `egfr` matched expected value. |
| pass | parser | low | `uacr_mg_g` | 84 | 84.0 | Parsed `uacr` matched expected value. |
| pass | parser | low | `cac_score` | 0 | 0.0 | Parsed `cac` matched expected value. |
| pass | parser | low | `family_history_premature_ascvd` | true | true | Parsed `family_history_premature_ascvd` matched expected value. |
| pass | parser | low | `known_ascvd` | false | false | Parsed `clinical_ascvd` matched expected value. |
| pass | derived_logic | low | `albuminuria_category` | "A2" | "A2" | Derived `albuminuria_category` matched expected value. |
| pass | derived_logic | low | `diabetes_range` | false | false | Derived `diabetes_range` matched expected value. |
| pass | derived_logic | low | `prediabetes_range` | true | true | Derived `prediabetes_range` matched expected value. |
| pass | derived_logic | low | `aspirin_primary_prevention_indicated` | false | false | Derived `aspirin_primary_prevention_indicated` matched expected value. |
| pass | derived_logic | low | `lipid_therapy_reasonable` | true | true | Derived `lipid_therapy_reasonable` matched expected value. |
| pass | report | low | `final_report_text` | "available when interpretation has run" | true | Final report text is available. |
| pass | report | low | `engine_output_json` | "available when interpretation has run" | true | Engine output is available. |
| pass | report | low | `ckm_stage` | 3 | 3 | CKM stage matched expected interpretation. |
| pass | report | low | `risk_level` | "3B" | "3B" | Risk level matched expected interpretation. |
| pass | report | low | `kdigo_stage` | "G2A2" | "RISK CONTINUUM CKM\n\nLevel: 3B - CKM stage 3 with albuminuria-mediated kidney and ASCVD risk.\nPREVENT: unavailable.\nCKM/Kidney/Plaque: CKM stage 3; kidney G2A2; CAC 0.\nContext: father MI age 49.\n\nAssessment:\n- Moderately increased albuminuria (ICD: R80.9)\n- Essential hypertension (ICD: I10)\n- Obesity (ICD: E66.9)\n- Prediabetes (ICD: R73.03)\n- Adult BMI 31.0-31.9 (ICD: Z68.31)\n\nRecommendations:\n1. Lipids: Discuss moderate-intensity statin.\n2. Plaque: CAC 0.\n3. Kidney: UACR 84; ACEi/ARB active.\n4. BP: Treat toward <130/80.\n5. Glycemia: Prediabetes prevention; A1c 6.3%.\n6. Aspirin: Not indicated.\n7. Additional information: Lp(a).\nDiscuss moderate-intensity statin therapy.\nConfirm persistent albuminuria with repeat UACR if not already confirmed; optimize kidney-protective therapy.\nContinue or optimize ACEi/ARB therapy if hypertension and persistent albuminuria are present.\nTreat BP toward goal <130/80.\nCheck Lp(a) once." | Report text includes expected KDIGO stage. |
| pass | report | low | `aspirin_recommendation` | "Not indicated" | "RISK CONTINUUM CKM\n\nLevel: 3B - CKM stage 3 with albuminuria-mediated kidney and ASCVD risk.\nPREVENT: unavailable.\nCKM/Kidney/Plaque: CKM stage 3; kidney G2A2; CAC 0.\nContext: father MI age 49.\n\nAssessment:\n- Moderately increased albuminuria (ICD: R80.9)\n- Essential hypertension (ICD: I10)\n- Obesity (ICD: E66.9)\n- Prediabetes (ICD: R73.03)\n- Adult BMI 31.0-31.9 (ICD: Z68.31)\n\nRecommendations:\n1. Lipids: Discuss moderate-intensity statin.\n2. Plaque: CAC 0.\n3. Kidney: UACR 84; ACEi/ARB active.\n4. BP: Treat toward <130/80.\n5. Glycemia: Prediabetes prevention; A1c 6.3%.\n6. Aspirin: Not indicated.\n7. Additional information: Lp(a).\nDiscuss moderate-intensity statin therapy.\nConfirm persistent albuminuria with repeat UACR if not already confirmed; optimize kidney-protective therapy.\nContinue or optimize ACEi/ARB therapy if hypertension and persistent albuminuria are present.\nTreat BP toward goal <130/80.\nCheck Lp(a) once." | Aspirin recommendation matched expected wording signal. |
| pass | report | low | `lipid_recommendation_contains` | "Discuss moderate-intensity statin" | "RISK CONTINUUM CKM\n\nLevel: 3B - CKM stage 3 with albuminuria-mediated kidney and ASCVD risk.\nPREVENT: unavailable.\nCKM/Kidney/Plaque: CKM stage 3; kidney G2A2; CAC 0.\nContext: father MI age 49.\n\nAssessment:\n- Moderately increased albuminuria (ICD: R80.9)\n- Essential hypertension (ICD: I10)\n- Obesity (ICD: E66.9)\n- Prediabetes (ICD: R73.03)\n- Adult BMI 31.0-31.9 (ICD: Z68.31)\n\nRecommendations:\n1. Lipids: Discuss moderate-intensity statin.\n2. Plaque: CAC 0.\n3. Kidney: UACR 84; ACEi/ARB active.\n4. BP: Treat toward <130/80.\n5. Glycemia: Prediabetes prevention; A1c 6.3%.\n6. Aspirin: Not indicated.\n7. Additional information: Lp(a).\nDiscuss moderate-intensity statin therapy.\nConfirm persistent albuminuria with repeat UACR if not already confirmed; optimize kidney-protective therapy.\nContinue or optimize ACEi/ARB therapy if hypertension and persistent albuminuria are present.\nTreat BP toward goal <130/80.\nCheck Lp(a) once." | Lipid recommendation matched expected wording signal. |
| pass | report | low | `diagnoses` | "diagnosis candidates available" | true | Diagnosis candidates are available in QA export. |
| pass | ui | low | `visible_ui_text` | "visible UI summary text available" | true | Visible UI summary text is available. |
