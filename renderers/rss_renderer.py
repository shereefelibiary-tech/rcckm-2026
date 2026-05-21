from html import escape

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


def render_domain_bar(rss_total, domain_rows):
    if rss_total <= 0 or not domain_rows:
        return

    colors = [
        "#2563eb",
        "#059669",
        "#d97706",
        "#7c3aed",
        "#dc2626",
        "#0891b2",
        "#4b5563",
    ]
    segments = []
    for index, row in enumerate(domain_rows):
        percentage = (row["Points"] / rss_total) * 100
        label = ""
        if percentage >= 12:
            label = (
                f'<span class="rss-domain-label">'
                f'{escape(row["Domain"])} {row["Points"]:g}'
                f"</span>"
            )
        segments.append(
            f'<div class="rss-domain-segment" '
            f'style="width: {percentage:.2f}%; '
            f'background: {colors[index % len(colors)]};">'
            f"{label}</div>"
        )

    st.markdown(
        """
        <style>
            .rss-domain-bar {
                display: flex;
                width: 100%;
                height: 34px;
                overflow: hidden;
                border-radius: 6px;
                background: #e5e7eb;
                margin: 0.25rem 0 1rem;
            }
            .rss-domain-segment {
                display: flex;
                align-items: center;
                justify-content: center;
                min-width: 2px;
                color: white;
                font-size: 0.8rem;
                font-weight: 600;
                white-space: nowrap;
            }
            .rss-domain-label {
                padding: 0 0.35rem;
                overflow: hidden;
                text-overflow: ellipsis;
            }
        </style>
        <div class="rss-domain-bar">
            """ + "".join(segments) + """
        </div>
        """,
        unsafe_allow_html=True,
    )


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

    domain_points = {}
    for contribution in rss_contributions:
        domain_points[contribution.domain] = (
            domain_points.get(contribution.domain, 0) + contribution.points
        )
    domain_rows = sorted(
        [
            {"Domain": domain, "Points": points}
            for domain, points in domain_points.items()
        ],
        key=lambda row: row["Points"],
        reverse=True,
    )

    render_domain_bar(rss_total, domain_rows)

    st.write("### Domain Subtotals")
    st.dataframe(
        domain_rows,
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
