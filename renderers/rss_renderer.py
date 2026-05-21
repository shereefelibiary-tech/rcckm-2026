import streamlit as st


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


def render_rss_panel(rss_total, rss_contributions):
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
    st.dataframe(
        sorted(
            [
                {"Domain": domain, "Points": points}
                for domain, points in domain_points.items()
            ],
            key=lambda row: row["Points"],
            reverse=True,
        ),
        hide_index=True,
    )

    st.dataframe(
        [
            {
                "Points": contribution.points,
                "Domain": contribution.domain,
                "Signal": format_signal(contribution),
                "Severity": contribution.severity or "",
                "Rationale": contribution.rationale,
            }
            for contribution in rss_contributions
        ],
        hide_index=True,
    )
