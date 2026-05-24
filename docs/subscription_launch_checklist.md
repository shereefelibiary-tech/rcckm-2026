# RCCKM Subscription Launch Checklist

Paid launch should wait until clinical, parser, legal, privacy, and operational gates are complete. This checklist is intentionally conservative.

## Clinical Safety Gates

Required before paid launch:

- [ ] Level taxonomy locked.
- [ ] Report section contract locked.
- [ ] Parser validation suite passing.
- [ ] Missing-vs-zero tests passing.
- [ ] Unknown/negation tests passing.
- [ ] Clinical ASCVD dominance tests passing.
- [ ] CAC missing versus CAC 0 tests passing.
- [ ] UACR missing versus UACR 0 tests passing.
- [ ] 50 golden clinical cases passing.
- [ ] 1,000+ fuzz/permutation cases passing in CI or release gate.
- [ ] 10,000 fuzz/permutation cases run locally before major release.
- [ ] No raw HTML visible in report outputs.
- [ ] No hidden RSS points.
- [ ] RSS total equals displayed contributor points.
- [ ] PREVENT category does not overwrite RCCKM level.

## Parser Gates

- [ ] EMR-style fixtures passing for Epic.
- [ ] EMR-style fixtures passing for Cerner.
- [ ] EMR-style fixtures passing for MEDITECH.
- [ ] EMR-style fixtures passing for Athena.
- [ ] EMR-style fixtures passing for eClinicalWorks.
- [ ] EMR-style fixtures passing for NextGen.
- [ ] EMR-style fixtures passing for Allscripts/Veradigm.
- [ ] EMR-style fixtures passing for VA CPRS.
- [ ] EMR-style fixtures passing for Labcorp.
- [ ] EMR-style fixtures passing for Quest.
- [ ] Generic portal copy/paste fixture passing.
- [ ] Messy mixed copy/paste fixture passing.
- [ ] Heavily incomplete unknown fixture passing.
- [ ] Stopped/allergy medication tests passing.
- [ ] Family history does not trigger clinical ASCVD.
- [ ] Unknown values do not generate RSS points, diagnoses, or recommendations.

## Product Gates

- [ ] Public website shell complete.
- [ ] Try demo page complete.
- [ ] SmartPhrase examples page complete.
- [ ] Validation / guideline alignment page complete.
- [ ] Pricing / early access page complete.
- [ ] Beta safety disclaimer visible on demo.
- [ ] Public demo does not auto-interpret before user action.
- [ ] Parser output clears stale report.
- [ ] Manual edits mark report stale or clear report.
- [ ] Copy EMR note works.
- [ ] Copy patient roadmap works.

## Legal and Policy Gates

- [ ] Privacy policy completed.
- [ ] Terms of use completed.
- [ ] Clinician-use disclaimer completed.
- [ ] Beta safety disclaimer completed.
- [ ] No-PHI public demo policy defined.
- [ ] HIPAA posture documented.
- [ ] Data retention decision documented.
- [ ] Data deletion process documented.
- [ ] Support contact and issue reporting defined.
- [ ] Medical disclaimer reviewed by counsel.

## Security and Compliance Gates

- [ ] Authentication implemented and tested.
- [ ] Authorization boundaries tested.
- [ ] Payment flow tested.
- [ ] Audit logs decision documented.
- [ ] Audit logs implemented if data is retained.
- [ ] Data encryption at rest and in transit documented.
- [ ] Error logging reviewed for PHI leakage.
- [ ] Analytics reviewed for PHI leakage.
- [ ] Demo environment separated from production clinical environment.
- [ ] Backups and retention policy documented.

## Billing and Subscription Gates

- [ ] Pricing model approved.
- [ ] Trial or early access policy defined.
- [ ] Stripe or payment provider tested.
- [ ] Subscription cancellation flow tested.
- [ ] Invoice and receipt flow tested.
- [ ] Account downgrade behavior defined.
- [ ] Team billing behavior defined if applicable.
- [ ] Enterprise/pilot contact path defined.

## Operational Gates

- [ ] Release checklist created.
- [ ] Rollback plan created.
- [ ] Incident response owner defined.
- [ ] Clinical safety issue escalation path defined.
- [ ] Parser misclassification reporting path defined.
- [ ] Support SLA expectations defined.
- [ ] Beta feedback intake defined.
- [ ] Changelog process defined.

## Launch Decision

Paid launch should not proceed until all P0 items above are complete or explicitly waived with documented rationale.

Recommended pre-launch signoff:

- Clinical owner.
- Engineering owner.
- Product owner.
- Privacy/legal owner.
- Security owner if PHI or accounts are involved.

