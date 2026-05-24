# 2026 ACC/AHA Dyslipidemia Guideline Coverage Matrix

Source of truth: `C:\Users\shere\Desktop\blumenthal-et-al-2026-2026-acc-aha-aacvpr-abc-acpm-ada-ags-apha-aspc-nla-pcna-guideline-on-the-management-of.pdf`

Status terms:

- `implemented`: RCCKM has explicit logic and tests or established coverage.
- `partially implemented`: core logic exists, but one or more inputs, edge cases, or display details are incomplete.
- `missing`: not represented yet.
- `RCCKM interpretation layer`: RCCKM-specific synthesis, not a direct guideline rule.
- `not planned for MVP`: intentionally deferred.

Priority:

- `P0`: must-have MVP / high-confidence implementation.
- `P1`: important next.
- `P2`: later or specialty workflow.

| # | Guideline domain | Guideline summary | RCCKM current status | Likely module/file | Priority | Notes / exact behavior needed |
|---:|---|---|---|---|---|---|
| 1 | PREVENT 10-year risk categories | Low `<3%`, borderline `3-<5%`, intermediate `5-<10%`, high `>=10%`. | implemented | `modules/prevent/engine.py`, `renderers/prevent_card.py` | P0 | Boundary tests cover 2.99/3/4.99/5/9.99/10. |
| 2 | PREVENT 30-year risk use | Use especially age 30-59 to inform longer-term trajectory. | implemented | `modules/prevent/*`, `modules/actions/engine.py` | P0 | 30-year output displays when eligible; low 10-year/high 30-year action path present. |
| 3 | CPR framework | Calculate risk, personalize with enhancers, reclassify with CAC, reassess response. | partially implemented | `core/engine.py`, `modules/actions/*`, `modules/clarification/*` | P1 | Calculate/personalize/reclassify are present; reassess/monitoring now has basic lipid follow-up but needs longitudinal workflow. |
| 4 | PREVENT eligibility guardrails | Use for adults without clinical ASCVD; age and required-input restrictions apply. | implemented | `modules/prevent/calculator.py`, `renderers/prevent_card.py`, `renderers/emr_renderer.py` | P0 | Clinical ASCVD dominance suppresses PREVENT as treatment driver. |
| 5 | Primary prevention LDL-C 70-189 pathway | PREVENT-guided LLT decisions in eligible primary-prevention adults. | partially implemented | `modules/targets/engine.py`, `modules/actions/engine.py` | P0 | LDL 70-189 is handled via PREVENT/CAC/diabetes/CKD, but no full shared-decision state machine. |
| 6 | Low 10-year + 30-year >=10 pathway | If 10-year `<3%` and 30-year `>=10%`, moderate-intensity statin reasonable. | implemented | `modules/actions/engine.py`, `modules/targets/engine.py` | P0 | Also supports LDL-C 160-189 at low 10-year risk. |
| 7 | Borderline risk pathway | Risk enhancers and shared decision-making; statin reasonable when selected. | partially implemented | `modules/actions/engine.py`, `modules/cac_recommendation/engine.py` | P0 | Reproductive markers now support risk discussion; broader risk-enhancer action phrasing remains incremental. |
| 8 | Intermediate risk pathway | At least moderate-intensity statin recommended; CAC can clarify uncertainty. | implemented | `modules/actions/engine.py`, `modules/targets/engine.py`, `modules/cac_recommendation/engine.py` | P0 | CAC recommended when treatment/intensity remains uncertain and age gate met. |
| 9 | High risk pathway | High-intensity statin recommended. | implemented | `modules/actions/engine.py`, `modules/targets/engine.py` | P0 | High PREVENT gets high-risk targets and indicated LLT wording. |
| 10 | LDL-C / non-HDL-C target tiers | `<100/<130`, `<70/<100`, `<55/<85` by pathway. | implemented | `modules/targets/engine.py`, `renderers/targets.py` | P0 | ApoB target is RCCKM support layer. |
| 11 | CAC 0 pathway | Measured CAC 0 may defer LLT only absent higher-risk conditions. | implemented | `modules/targets/engine.py`, `modules/actions/scaffold.py` | P0 | CAC 0 is distinct from missing/not performed. |
| 12 | CAC 1-99 pathway | Moderate-intensity statin reasonable; LDL `<100`, non-HDL `<130`. | implemented | `modules/targets/engine.py`, `modules/actions/scaffold.py` | P0 | Percentile modifier deferred. |
| 13 | CAC 100-299 or >=75th percentile | LLT recommended; LDL `<70`, non-HDL `<100`. | partially implemented | `modules/targets/engine.py` | P0/P1 | Numeric CAC tier implemented; CAC percentile missing. |
| 14 | CAC 300-999 pathway | LLT recommended; >=50% LDL reduction; LDL `<70`, non-HDL `<100`; intensify toward `<55/<85` reasonable. | partially implemented | `modules/targets/engine.py`, `modules/actions/scaffold.py` | P0 | Target and wording present; percent LDL reduction not computed. |
| 15 | CAC >=1000 pathway | LDL `<55`, non-HDL `<85`. | implemented | `modules/targets/engine.py` | P0 | Extensive plaque tier implemented. |
| 16 | CAC age gating | Men `>=40`, women `>=45` for routine selective CAC consideration. | implemented | `modules/cac_recommendation/engine.py` | P0 | Below gate shows soft note only with strong signals. |
| 17 | CAC percentile support | CAC `>=75th percentile` modifies pathway. | missing | new percentile input/calculator | P1 | Need CAC percentile input or calculator before guideline logic can be exact. |
| 18 | ApoB measurement logic | Useful in CKM/T2DM/TG elevation/on LLT/residual risk. | partially implemented | `modules/actions/engine.py`, `modules/clarification/engine.py` | P0/P1 | ApoB clarifier exists; on-treatment/residual-risk workflow needs more context. |
| 19 | ApoB risk-enhancer threshold | ApoB `>=120 mg/dL` is guideline risk enhancer. | implemented | `modules/risk_enhancers/engine.py` | P0 | ApoB 100-119 remains RCCKM particle-burden interpretation only. |
| 20 | Lp(a) once-in-lifetime testing | Measure at least once in adults. | implemented | `modules/actions/engine.py`, `modules/rss/engine.py` | P0 | Missing clarifier uses `Lp(a)` only. |
| 21 | Lp(a) risk tiers | `<75`, `75-124`, `>=125/50`, `>=250/100`, `>=430/180`. | implemented | `modules/rss/engine.py`, `renderers/where_patient_falls.py` | P0 | Lp(a) 80 is not major. |
| 22 | hsCRP repeated >=2 logic | Risk enhancer if persistent/repeated `>=2 mg/L`. | partially implemented | `modules/risk_enhancers/engine.py`, `renderers/where_patient_falls.py` | P0 | Single value is mild/verify with persistence language; repeated-value field not implemented. |
| 23 | Risk enhancers table | Guideline risk enhancers inform shared decision-making. | partially implemented | `modules/risk_enhancers/engine.py`, `modules/actions/engine.py` | P1 | Major enhancers present; full table and persistence qualifiers incomplete. |
| 24 | Reproductive risk markers | Pregnancy/menopause/PCOS markers personalize primary-prevention risk. | implemented | `modules/risk_enhancers/reproductive.py`, `smartphrase_ingest/parser.py`, `ui/input_worksheet.py` | P0 | Mild RSS contributors/context; not PREVENT inputs. |
| 25 | Severe hypercholesterolemia / LDL-C >=190 | Treatment-forward pathway; do not de-risk with CAC. | partially implemented | `modules/targets/engine.py`, `modules/actions/engine.py`, `modules/cac_recommendation/engine.py` | P0/P1 | CAC de-risk guard present; dedicated targets/referral pathway needs expansion. |
| 26 | FH suspicion / genetic testing / referral | Identify likely FH and refer/test when appropriate. | missing | new FH module | P1 | Needs family history + LDL severity + physical findings/known mutation fields. |
| 27 | Diabetes pathway | Diabetes age 40-75: statin indicated; targets depend on risk factors. | implemented | `modules/targets/engine.py`, `modules/actions/engine.py` | P0 | Multiple-risk-factor pathway represented. |
| 28 | Diabetes-specific risk enhancers | Duration, albuminuria, eGFR, retinopathy, neuropathy, ABI `<0.9`. | implemented | `core/patient.py`, `modules/targets/engine.py`, `modules/risk_enhancers/engine.py`, `smartphrase_ingest/parser.py` | P0 | Duration/retinopathy/neuropathy/ABI fields added. |
| 29 | CKD stage 3+ pathway | Age 40-75 CKD stage 3+: moderate statin or statin+ezetimibe recommended. | implemented | `modules/targets/engine.py`, `modules/actions/engine.py` | P0 | Chronicity still clinician-reviewed. |
| 30 | HIV pathway | HIV is a risk enhancer. | implemented | `smartphrase_ingest/parser.py`, `modules/rss/engine.py`, `modules/risk_enhancers/engine.py` | P0 | Explicit no/yes parsing is covered. |
| 31 | Chronic inflammatory disease pathway | RA/SLE/psoriasis/IBD/inflammatory context are risk enhancers. | implemented | `smartphrase_ingest/parser.py`, `modules/rss/engine.py`, `modules/risk_enhancers/engine.py` | P0 | Single generic inflammatory disease remains contextual. |
| 32 | Hypertriglyceridemia 150-499 | Lifestyle + ASCVD/PREVENT-guided statin discussion; non-HDL/ApoB helpful. | partially implemented | `modules/actions/engine.py`, `modules/rss/engine.py`, `modules/diagnoses/engine.py` | P0 | Diagnosis/RSS present; dietary counseling text is not full guideline depth. |
| 33 | Hypertriglyceridemia 500-999 | Pancreatitis-risk pathway; TG-lowering therapy reasonable. | implemented | `modules/actions/engine.py` | P0 | Wording includes repeat fasting lipids, secondary causes, TG-lowering therapy. |
| 34 | Hypertriglyceridemia >=1000 | Pancreatitis priority, RDN referral, very-low-fat/no alcohol, TG-lowering therapy. | implemented | `modules/actions/engine.py` | P0 | Specialty workflow details remain concise. |
| 35 | Non-HDL-C calculation/display | Calculate TC-HDL when available and use target tiers. | implemented | `core/engine.py`, `ui/input_worksheet.py`, `modules/targets/engine.py` | P0 | Engine now fills missing non-HDL from TC/HDL. |
| 36 | Dietary supplements warning | Supplements should not replace evidence-based LLT. | implemented | `smartphrase_ingest/parser.py`, `modules/actions/engine.py` | P0 | Supplement mentions for lipid lowering produce warning/action line. |
| 37 | RDN referral triggers | RDN useful for severe TG and nutrition-intensive pathways. | partially implemented | `modules/actions/engine.py` | P1 | TG >=1000 line includes RDN referral; broader dietitian triggers not modeled. |
| 38 | Lipid specialist referral triggers | FH, refractory severe dyslipidemia, complex therapy. | missing | new referral module | P1 | Needs robust FH/severe TG/medication-intolerance workflow. |
| 39 | Monitoring after LLT initiation/intensification | Lipid profile 4-12 weeks, then every 6-12 months. | implemented | `modules/actions/scaffold.py` | P0 | Added to visible recommendation scaffold when LLT is indicated/considered. |
| 40 | Pregnancy/lactation medication safety | Statin/nonstatin safety and contraception/pregnancy planning. | missing | new reproductive medication safety module | P1 | Do not implement casually; needs medication-specific safety logic. |
| 41 | Heart failure nuance | PREVENT total CVD includes HF; lipid recommendations vary by HF context. | partially implemented | `modules/prevent/*`, `renderers/prevent_card.py` | P2 | HF risk displays from PREVENT where available; HF clinical state not modeled. |
| 42 | Cancer survivor / active cancer considerations | Cancer therapy/survivorship may affect ASCVD risk and treatment choices. | missing | new history/risk-enhancer fields | P2 | Not planned for MVP unless oncology workflow added. |

## P0 Implementation Notes From This Pass

- Added diabetes-specific risk enhancer fields and parser support.
- Added lipid supplement warning/action support.
- Added non-HDL calculation at engine entry when TC and HDL-C are available.
- Added lipid monitoring language to the action scaffold for started/intensified/considered LLT.
- Preserved PREVENT coefficients and existing RSS scoring philosophy.

## Taxonomy Discipline Update

RCCKM now separates PREVENT category from RCCKM level through `modules/levels/level_classifier.py`.

- PREVENT remains a population risk estimate and is displayed in the PREVENT card.
- RCCKM Level 2A/2B captures early isolated or converging risk signals that are not yet treatment-forward.
- RCCKM Level 3A captures elevated long-term/cumulative risk trajectory, including age 30-59 with PREVENT 30-year ASCVD risk >=10% or LDL-C 160-189 when no higher plaque/ASCVD pathway applies.
- RCCKM Level 3B captures actionable early CKM, kidney, or atherogenic burden.
- CAC missing remains plaque unmeasured and does not create subclinical atherosclerosis.
- Clinical ASCVD and high CAC pathways override PREVENT category.

Protected by:
- `tests/golden_cases/test_level_taxonomy.py`
- `tests/unit/test_levels_definitions.py`
- `tests/test_invariants.py`
