import streamlit as st

from core.patient import Patient
from core.engine import evaluate_patient
from modules.rss.engine import build_rss_contributions, calculate_rss_total


def format_signal(contribution):
    value = contribution.actual_value
    if value is None or isinstance(value, bool):
        return contribution.label

    value_labels = {
        "CAC plaque burden": f"CAC {value}",
        "ApoB elevation": f"ApoB {value} mg/dL",
        "Elevated Lp(a)": f"Lp(a) {value}",
        "Inflammatory risk": f"hsCRP {value} mg/L",
        "Reduced eGFR": f"eGFR {value}",
        "Albuminuria": f"UACR {value} mg/g",
        "Hypertriglyceridemia": f"Triglycerides {value} mg/dL",
    }
    value_label = value_labels.get(contribution.label, str(value))
    return f"{contribution.label} ({value_label})"


def main():
    st.title("RCCKM 2026")

    if st.button("Run Demo Patient"):
        patient = Patient(
            age=60,
            sex="male",
            cac=350,
            apob=110,
            lp_a_value=80,
            uacr=45,
            egfr=55,
            diabetes=True,
        )

        result = evaluate_patient(patient)
        rss_contributions = build_rss_contributions(patient, result)
        rss_total = calculate_rss_total(rss_contributions)

        st.write("### Results")
        st.write(f"Risk level: {result.risk_level}")
        st.write(f"Plaque category: {result.plaque_category}")
        st.write(f"Decision stability: {result.decision_stability}")

        if result.targets:
            target = result.targets[0]
            st.write("### Targets")
            st.write(f"LDL target: {target.ldl_c_target}")
            st.write(f"non-HDL target: {target.non_hdl_c_target}")
            st.write(f"ApoB target: {target.apob_target}")

        if result.diagnosis_candidates:
            st.write("### Diagnosis candidates")
            for candidate in result.diagnosis_candidates:
                st.write(f"- {candidate.name}")

        if result.dominant_action:
            st.write("### Dominant Action")
            st.write(result.dominant_action)

        if result.snapshot_lines:
            st.write("### Snapshot")
            for line in result.snapshot_lines:
                st.write(line)

        st.write("### RSS")
        st.write(f"Total RSS: {rss_total}")

        st.write("### Top Drivers")
        top_drivers = sorted(
            rss_contributions,
            key=lambda contribution: contribution.points,
            reverse=True,
        )[:3]
        for contribution in top_drivers:
            st.write(
                f"+{contribution.points} "
                f"{format_signal(contribution)}: "
                f"{contribution.rationale}"
            )

        st.write("### Domain Subtotals")
        domain_points = {}
        for contribution in rss_contributions:
            domain_points[contribution.domain] = (
                domain_points.get(contribution.domain, 0) + contribution.points
            )
        st.table(
            sorted(
                [
                    {"Domain": domain, "Points": points}
                    for domain, points in domain_points.items()
                ],
                key=lambda row: row["Points"],
                reverse=True,
            )
        )

        st.table(
            [
                {
                    "Points": contribution.points,
                    "Domain": contribution.domain,
                    "Signal": format_signal(contribution),
                    "Severity": contribution.severity or "",
                    "Rationale": contribution.rationale,
                }
                for contribution in rss_contributions
            ]
        )


if __name__ == "__main__":
    main()
