# 2026 Risk-Enhancer Coverage Matrix

This matrix tracks RCCKM support for guideline risk enhancers and adjacent personalization inputs. Status reflects the current beta implementation, not a claim that all guideline nuance is complete.

| Domain | Guideline concept | Status | Worksheet field | Parser support | RSS support | EMR output support | Roadmap support | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Higher-risk ancestry: South Asian | South Asian ancestry can personalize primary-prevention risk discussion. | partial | `south_asian_ancestry` | explicit yes/no/unknown | tiny contextual contributor | risk-context sentence | context item | P1 |
| Higher-risk ancestry: Filipino | Filipino ancestry can personalize primary-prevention risk discussion. | partial | `filipino_ancestry` | explicit yes/no/unknown | tiny contextual contributor | risk-context sentence | context item | P1 |
| Other ancestry/context | Other higher-risk ancestry or social context may affect interpretation. | partial | `higher_risk_ancestry_context` | missing | context only | risk-context sentence | not surfaced unless entered | P2 |
| Chronic inflammatory disease: RA | RA is a risk-enhancing inflammatory condition. | present | `rheumatoid_arthritis` | yes/no/unknown, negation-safe | tiny contributor | via RSS/audit/context | context item | P0 |
| Chronic inflammatory disease: SLE | SLE is a risk-enhancing inflammatory condition. | present | `sle` | yes/no/unknown, negation-safe | tiny contributor | via RSS/audit/context | context item | P0 |
| Chronic inflammatory disease: psoriasis | Psoriasis is a risk-enhancing inflammatory condition. | present | `psoriasis` | yes/no/unknown, negation-safe | tiny contributor | via RSS/audit/context | context item | P0 |
| Chronic inflammatory disease: inflammatory arthritis | Inflammatory arthritis is a risk-enhancing inflammatory condition. | partial | `inflammatory_arthritis` | explicit yes/no/unknown | tiny contributor | via RSS/audit/context | context item | P1 |
| Chronic inflammatory disease: IBD | IBD is a risk-enhancing inflammatory condition. | present | `ibd` | yes/no/unknown, negation-safe | tiny contributor | via RSS/audit/context | context item | P0 |
| Reproductive risk markers | Early/premature menopause, hypertensive pregnancy disorders, gestational diabetes, preterm delivery, SGA infant, recurrent pregnancy loss, PCOS/irregular menses, and early menarche personalize risk. | present | reproductive history fields | yes/no/unknown, negation-safe | tiny contributors | concise context | context item | P0 |
| HIV on stable ART | Adults age 40-75 with HIV on stable ART have a specific statin pathway and interaction review need. | partial | `hiv`, `stable_art` | explicit yes/no/unknown | HIV contributor, separate from inflammation | HIV/stable ART context and action | context item | P0 |
| CKM syndrome | CKM context informs Level 2/3 interpretation. | present | CKM inputs including BP, glycemia, BMI, TG, kidney markers | generic fallback | multiple contributors | CKM/kidney sentence | priority/context | P0 |
| eGFR / UACR / CKD | Kidney function and albuminuria refine risk; missing UACR is not A1. | present | `egfr`, `uacr`, `ckd` | numeric parsing | kidney contributors when measured | kidney summary and UACR completion line | kidney context | P0 |
| ApoB thresholds | ApoB `>=120 mg/dL` is guideline risk-enhancing; `>=140` supports severe particle/FH concern. | present | `apob` | numeric parsing | tiered particle contributor | atherogenic burden summary | context item | P0 |
| Lp(a) thresholds | Lp(a) tiers: reference, mild/context, elevated, high, very high. | present | `lp_a_value`, `lp_a_unit` | numeric parsing + unit | tiered contributor | atherogenic burden summary | context item | P0 |
| Persistent TG elevation | TG `>=150` is a risk enhancer; `>=500` and `>=1000` trigger severe TG pathways. | present | `triglycerides` | numeric parsing | TG contributor | TG and action pathways | context item | P0 |
| Family history | Premature first-degree family history is a risk enhancer; non-premature FH remains context. | present | family-history fields | structured extraction | tiny contributor if premature | context, not diagnosis candidate | context item | P0 |
| hsCRP persistent `>=2` | Guideline enhancer requires persistence; single value should prompt verification. | partial | `hscrp` | numeric parsing | tiny/mild contributor | verify-persistence wording | context item | P1 |
| Cancer survivor / active cancer | Cancer survivors who otherwise qualify for LLT should generally be treated similarly when life expectancy is >2 years. | partial | `active_cancer`, `cancer_survivor`, `cancer_life_expectancy_gt_2y` | explicit yes/no/unknown | context only | context only | context item | P1 |
| Suspected FH / HeFH pathway | FH/severe hypercholesterolemia should not be de-risked by PREVENT or CAC 0. | partial | `suspected_fh_hefh`, LDL-C, ApoB, family history | explicit yes/no/unknown + lipid signals | moderate contributor/context | FH pathway line when present | context item | P0 |
| Incidental CAC on noncardiac CT | Incidental CAC is qualitative plaque evidence; do not overquantify without Agatston score. | partial | `incidental_cac`, `incidental_cac_severity` | explicit yes/no/unknown + severity | qualitative plaque contributor | plaque context | context item | P1 |
| Neighborhood-level SDOH / ZIP PREVENT support | PREVENT has neighborhood/zip-code support; RCCKM keeps this optional/off by default. | missing | `zip_code`, `neighborhood_sdoh_context` | missing | none | none by default | none by default | P2 |
| LDL-C equation preference note | If LDL-C is calculated upstream, Martin/Hopkins or Sampson/NIH methods are preferred when applicable. | documented | entered LDL-C | not applicable | none | not surfaced in routine note | none | P2 |

## CPR Framework

- **Calculate:** PREVENT 10-year and 30-year risk.
- **Personalize:** CKM context, risk enhancers, ApoB, Lp(a), eGFR/UACR, reproductive history, ancestry/context, HIV, and special populations.
- **Reclassify:** CAC/plaque, including qualitative incidental CAC when available.
- **Reassess:** targets, actions, monitoring, EMR note, and patient roadmap.

## LDL-C Equation Note

RCCKM uses entered LDL-C values. If LDL-C is calculated upstream, Martin/Hopkins or Sampson/NIH methods are preferred when applicable, especially when triglycerides are elevated or LDL-C is low.

## Safety Guardrails

- PREVENT is a primary-prevention estimator validated for adults age 30-79.
- PREVENT is not used to de-risk established clinical ASCVD.
- PREVENT is not used to de-risk LDL-C `>=190 mg/dL`, suspected FH/HeFH, or severe hypercholesterolemia pathways.
- CAC 0 must not defer lipid-lowering therapy in established ASCVD or LDL-C `>=190` / possible FH pathways.
- Ancestry, reproductive history, inflammatory disease, and HIV are personalization enhancers/context unless a separate treatment pathway is explicitly triggered.
