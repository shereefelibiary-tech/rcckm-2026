from __future__ import annotations

from collections import Counter

from rcckm.governance import audit_result
from tests.helpers import render_all_outputs
from tools.demo_audit import audit_demo_cases
from ui.demo_case_gallery import DEMO_CASES, build_demo_patient
from ui.report_layout import run_patient


def build_report() -> str:
    """Build a concise CLI governance report across demo cases."""
    demo_report = audit_demo_cases()
    governance_findings = []
    missing_evidence = []
    trace_count = 0
    for label, case_name in DEMO_CASES:
        patient = build_demo_patient(case_name)
        result, _rss_total, _rss_contributions = run_patient(patient)
        outputs = render_all_outputs(patient, result)
        audit = audit_result(patient, result, outputs["visible"])
        trace_count += len(audit.traces)
        governance_findings.extend((label, finding) for finding in audit.findings)
        missing_evidence.extend(
            (label, trace.recommendation_id)
            for trace in audit.traces
            if not trace.evidence_basis
        )

    category_counts = Counter(finding.category for _label, finding in governance_findings)
    error_count = sum(1 for _label, finding in governance_findings if finding.severity == "error")
    warning_count = sum(1 for _label, finding in governance_findings if finding.severity == "warning")

    lines = [
        "RCCKM Clinical Governance Report",
        f"Demo cases audited: {len(DEMO_CASES)}",
        f"Passing demo audits: {len([case for case in demo_report.cases if not case.errors])}",
        f"Demo audit failures: {len(demo_report.errors)}",
        f"Governance findings: {len(governance_findings)}",
        f"Governance errors: {error_count}",
        f"Governance warnings: {warning_count}",
        f"Rule traces generated: {trace_count}",
        f"Missing evidence mappings: {len(missing_evidence)}",
        "",
        "Failures by category:",
    ]
    if category_counts:
        lines.extend(f"- {category}: {count}" for category, count in sorted(category_counts.items()))
    else:
        lines.append("- none")
    lines.extend(["", "Top clinical contradictions:"])
    contradictions = [
        f"{label}: {finding.message}"
        for label, finding in governance_findings
        if finding.category == "contradiction"
    ]
    lines.extend(f"- {item}" for item in contradictions[:10]) if contradictions else lines.append("- none")
    lines.extend(["", "Terminology violations:"])
    terminology = [
        f"{label}: {finding.message}"
        for label, finding in governance_findings
        if finding.category in {"terminology", "prevent"}
    ]
    lines.extend(f"- {item}" for item in terminology[:10]) if terminology else lines.append("- none")
    lines.extend(["", "Demos needing revision:"])
    lines.extend(f"- {item}" for item in demo_report.errors[:10]) if demo_report.errors else lines.append("- none")
    return "\n".join(lines)


def main() -> int:
    print(build_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
