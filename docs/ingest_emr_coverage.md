# RCCKM Ingest EMR Coverage

All examples are synthetic and de-identified. The parser is source-aware but source-agnostic at the output boundary: Epic, Cerner, Meditech, athenahealth, eClinicalWorks, NextGen, Allscripts/Veradigm, VA CPRS, Labcorp, Quest, portal copies, and messy mixed paste all normalize into RCCKM worksheet fields.

## Normalized Output Fields

Supported normalized fields include:

- Demographics: `age`, `sex`
- Vitals: `sbp`, `dbp`, `bpTreated`
- Lipids: `tc`, `ldl`, `hdl`, `tg`, `apob`, `lpa`, `lpa_unit`, `fasting_lipids`
- Glycemia/metabolic: `a1c`, `diabetes`, `bmi`
- Kidney: `egfr`, `creatinine`, `uacr`
- Plaque/ASCVD: `cac`, `ascvd_clinical`
- Enhancers: `smoker`, `fhx`, `fhx_text`, `hscrp`, inflammatory disease context, OSA, MASLD
- Medications/context: `medications_raw`, `dm_meds_raw`, `lipidLowering`, `sglt2`, `glp1`, `ace_arb`

## Source Styles Covered

| Source style | Fixture | Fields covered | Supported labels/examples | Known weak spots |
| --- | --- | --- | --- | --- |
| Epic SmartPhrase | `epic_smartphrase_standard.txt` | Complete demo case | `55M`, `BP 132/82`, `LDL-C`, `ApoB`, `Lp(a)`, `Father MI age 49` | SmartPhrase macros with custom abbreviations may need additional labels. |
| Epic lab table | `epic_lab_results_table.txt` | Complete demo case | `Component | Value | Units`, `LDL Cholesterol Calc`, `Albumin/Creatinine Ratio` | Table units are not retained except where clinically needed, such as Lp(a). |
| Cerner PowerChart summary | `cerner_powerchart_summary.txt` | Complete demo case | `Age/Sex: 55/M`, `PowerChart`, prose labs | Complex medication status histories may need clinician review. |
| Cerner lab flowsheet | `cerner_lab_flowsheet.txt` | Complete demo case | uppercase lab names, `Stopped atorvastatin` | Prior medication history is parsed conservatively as inactive. |
| Meditech Expanse | `meditech_expanse_summary.txt` | Complete demo case | `55-year-old male`, `E-GFR`, `Agatston score` | The parser does not infer source from local hospital headers unless Meditech/Expanse appears. |
| athenahealth | `athenahealth_visit_summary.txt` | Complete demo case | visit-summary prose, medication names | Diabetes medications are captured as raw context, not full medication reconciliation. |
| eClinicalWorks | `eclinicalworks_progress_note.txt` | Complete demo case | nonfasting lipid language, diabetes prose | Nonfasting status is preserved; fasting repeat recommendations are handled downstream. |
| NextGen | `nextgen_clinical_summary.txt` | Complete demo case | `Gender M`, `Alb/Cr Ratio` | Abbreviated smoking histories beyond never/current/former may need review. |
| Allscripts/Veradigm | `allscripts_veradigm_summary.txt` | Complete demo case | line-separated lab labels | Custom medication sections may need more active/inactive patterns. |
| VA CPRS | `va_cprs_note.txt` | Complete demo case | `CPRS`, slash-delimited lab block | Family-history stroke/MI is separated from patient ASCVD, but ambiguous phrasing still needs review. |
| Labcorp | `labcorp_results_text.txt` | Complete demo case | `Cholesterol, Total`, `Apolipoprotein B`, `Lipoprotein (a)` | Accession/date/provider content is intentionally ignored. |
| Quest | `quest_results_text.txt` | Complete demo case | `LDL-CHOLESTEROL`, `CARDIO IQ hsCRP` | Some Quest panels use long proprietary names that may need incremental aliases. |
| Generic portal copy | `generic_portal_lab_copy.txt` | Complete demo case | compact copy/paste lines | Source style may be `generic` or `unknown` depending on surrounding text. |
| Messy mixed paste | `messy_mixed_copy_paste.txt` | Complete demo case | mixed PowerChart + portal text, old CAC not-done plus current CAC | Conflicts are surfaced when text contains both unavailable and measured values. |

## Edge Cases Covered

- A1c reference ranges do not falsely trigger diabetes.
- Lp(a) `mg/dL` and `nmol/L` units are preserved.
- eGFR unavailable reasons are preserved.
- UACR unavailable reasons are preserved.
- CAC `not done` does not become CAC 0.
- Family history does not become clinical ASCVD.
- Clinical ASCVD does not trigger from family-history lines.
- Nonfasting TG `>=400` can drive repeat fasting lipid clarification downstream.
- `No diabetes` plus A1c `>=6.5` creates a conflict.
- Stopped statin does not count as active lipid-lowering therapy.

## Unsupported / Review-Needed Items

- The parser does not attempt full medication reconciliation or dose parsing.
- It does not infer diabetes duration, retinopathy, neuropathy, or ABI.
- It does not convert Lp(a) between `mg/dL` and `nmol/L`; it preserves the reported unit.
- It does not treat missing CAC as CAC 0.
- It does not use real patient identifiers and should continue rejecting pasted PHI through the ingest UI guardrail.
- Source detection is advisory. Generic parsing always runs as fallback, and the worksheet remains the final source of truth after clinician review.
