from ui.html import render_html


def component_theme_css() -> str:
    """Shared CSS tokens/classes for app-owned HTML renderers.

    Component iframes do not inherit the Streamlit page CSS, so renderers can
    prepend this small system layer and then keep only local layout details.
    """
    return """
:root {
    --rc-garnet: #73000A;
    --rc-garnet-deep: #4B0007;
    --rc-black: #111111;
    --rc-charcoal: #222222;
    --rc-ivory: #F7F2E8;
    --rc-panel: #FFFDF8;
    --rc-line: rgba(17, 17, 17, 0.12);
    --rc-garnet-tint: rgba(115, 0, 10, 0.08);
    --rc-bg: var(--rc-ivory);
    --rc-surface: var(--rc-panel);
    --rc-surface-2: #FBF7EF;
    --rc-text: var(--rc-black);
    --rc-muted: #5D6B7A;
    --rc-primary: var(--rc-charcoal);
    --rc-primary-2: var(--rc-garnet);
    --rc-accent: #2F5F8F;
    --rc-border: var(--rc-line);
    --rc-border-soft: rgba(17, 17, 17, 0.09);
    --rc-shadow: 0 16px 38px rgba(11, 31, 58, 0.07);
    --rc-shadow-soft: 0 10px 24px rgba(11, 31, 58, 0.055);
    --rc-radius: 16px;
    --rc-radius-sm: 10px;
    --rc-xs: 4px;
    --rc-sm: 8px;
    --rc-md: 14px;
    --rc-lg: 20px;
    --rc-font-body: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    --rc-font-title: Georgia, "Times New Roman", serif;
    --rc-plaque: var(--rc-garnet);
    --rc-apob: #D97706;
    --rc-kidney: #0F8B8D;
    --rc-metabolic: #7C3AED;
    --rc-inflammatory: #EA580C;
    --rc-lpa: #4F46E5;
}
.rc-panel {
    border: 1px solid var(--rc-border);
    border-radius: var(--rc-radius);
    background: linear-gradient(180deg, var(--rc-surface) 0%, var(--rc-surface-2) 100%);
    box-shadow: var(--rc-shadow);
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    margin: 10px 0 14px;
    padding: 15px 17px;
}
.rc-report {
    color: var(--rc-text);
    font-family: var(--rc-font-body);
}
.rc-panel-compact {
    border: 1px solid var(--rc-border);
    border-radius: 12px;
    background: rgba(255, 253, 248, 0.78);
    box-shadow: none;
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    margin: 6px 0 8px;
    padding: 10px 12px;
}
.rc-section-title {
    color: var(--rc-primary);
    font-family: var(--rc-font-title);
    font-size: 1.13rem;
    font-weight: 700;
    letter-spacing: -0.012em;
    line-height: 1.1;
}
.rc-eyebrow {
    color: var(--rc-garnet);
    font-family: var(--rc-font-body);
    font-size: 0.68rem;
    font-weight: 850;
    letter-spacing: 0.08em;
    line-height: 1.1;
}
.rc-row {
    border-bottom: 1px solid var(--rc-border-soft);
    display: grid;
    gap: 2px;
    padding: 6px 0;
}
.rc-row:last-child {
    border-bottom: 0;
}
.rc-row-title {
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    font-size: 0.86rem;
    font-weight: 850;
    line-height: 1.18;
}
.rc-row-detail {
    color: rgba(7, 26, 47, 0.58);
    font-family: var(--rc-font-body);
    font-size: 0.76rem;
    font-weight: 650;
    line-height: 1.24;
}
.rc-section-title,
.rc-card-title {
    line-height: 1.15;
}
.rc-section-title { font-size: 1.14rem; }
.rc-card-title {
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    font-size: 1.04rem;
    font-weight: 750;
    letter-spacing: 0;
    margin-bottom: 8px;
}
.rc-subsection-title {
    color: var(--rc-primary-2);
    font-family: var(--rc-font-body);
    font-size: 0.78rem;
    font-weight: 850;
    letter-spacing: 0;
    line-height: 1.2;
}
.rc-body {
    color: rgba(7, 26, 47, 0.78);
    font-family: var(--rc-font-body);
    font-size: 0.86rem;
    font-weight: 650;
    line-height: 1.32;
}
.rc-muted {
    color: rgba(7, 26, 47, 0.58);
    font-family: var(--rc-font-body);
    font-size: 0.76rem;
    font-weight: 650;
    line-height: 1.28;
}
.rc-metric {
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    font-size: 1.8rem;
    font-weight: 900;
    letter-spacing: -0.035em;
    line-height: 0.98;
}
.rc-meta {
    color: rgba(47, 95, 143, 0.88);
    font-family: var(--rc-font-body);
    font-size: 0.68rem;
    font-weight: 850;
    letter-spacing: 0.08em;
}
.rc-metric-number {
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    font-size: 2rem;
    font-weight: 900;
    letter-spacing: -0.04em;
    line-height: 0.98;
}
.rc-chip,
.rc-chip-subtle,
.rc-chip-warning,
.rc-chip-major {
    border-radius: 999px;
    display: inline-flex;
    font-family: var(--rc-font-body);
    font-size: 0.72rem;
    font-weight: 850;
    line-height: 1;
    padding: 0.28rem 0.56rem;
    white-space: nowrap;
}
.rc-chip {
    border: 1px solid rgba(47, 95, 143, 0.26);
    background: rgba(47, 95, 143, 0.08);
    color: var(--rc-primary-2);
}
.rc-chip-subtle {
    border: 1px solid rgba(11, 31, 58, 0.12);
    background: rgba(255, 253, 248, 0.72);
    color: var(--rc-muted);
}
.rc-chip-warning {
    border: 1px solid rgba(217, 119, 6, 0.28);
    background: rgba(217, 119, 6, 0.14);
    color: #7c3f00;
}
.rc-chip-major {
    border: 1px solid rgba(115, 0, 10, 0.24);
    background: var(--rc-garnet);
    color: #fffdf8;
}
.rc-table {
    border-collapse: collapse;
    border: 1px solid rgba(11, 31, 58, 0.12);
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    width: 100%;
}
.rc-table th,
.rc-table td {
    border-bottom: 1px solid rgba(11, 31, 58, 0.10);
    padding: 8px 10px;
    text-align: left;
    vertical-align: middle;
}
.rc-divider {
    border-top: 1px solid rgba(11, 31, 58, 0.10);
    margin: 9px 0;
}
.rc-app-title {
    color: var(--rc-primary);
    font-family: var(--rc-font-title);
    font-size: clamp(1.85rem, 3vw, 3rem);
    font-weight: 700;
    letter-spacing: -0.035em;
    line-height: 0.98;
}
.rc-app-subtitle {
    color: rgba(7, 26, 47, 0.66);
    font-family: var(--rc-font-body);
    font-size: 0.94rem;
    font-weight: 600;
    line-height: 1.28;
}
.rc-field-label {
    color: rgba(7, 26, 47, 0.66);
    font-family: var(--rc-font-body);
    font-size: 0.74rem;
    font-weight: 720;
    line-height: 1.1;
}
.rc-input {
    border: 1px solid rgba(11, 31, 58, 0.18);
    border-radius: 9px;
    background: #fffefa;
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    font-size: 0.86rem;
    font-weight: 720;
}
.rc-button-primary,
.rc-button-secondary {
    border-radius: 999px;
    display: inline-flex;
    font-family: var(--rc-font-body);
    font-weight: 850;
    line-height: 1;
    white-space: nowrap;
}
.rc-button-primary {
    border: 1px solid var(--rc-primary);
    background: var(--rc-primary);
    color: var(--rc-surface);
}
.rc-button-secondary {
    border: 1px solid rgba(11, 31, 58, 0.18);
    background: rgba(255, 253, 248, 0.82);
    color: var(--rc-primary);
}
.rc-grid {
    display: grid;
    gap: var(--rc-sm);
}
"""


def apply_global_theme(st):
    render_html(
        st,
        """
<style>
/*COMPONENT_THEME*/
:root {
    --rc-garnet: #73000A;
    --rc-garnet-deep: #4B0007;
    --rc-black: #111111;
    --rc-charcoal: #222222;
    --rc-ivory: #F7F2E8;
    --rc-panel: #FFFDF8;
    --rc-line: rgba(17, 17, 17, 0.12);
    --rc-garnet-tint: rgba(115, 0, 10, 0.08);
    --rc-bg: var(--rc-ivory);
    --rc-surface: var(--rc-panel);
    --rc-text: var(--rc-black);
    --rc-muted: #5D6B7A;
    --rc-primary: var(--rc-charcoal);
    --rc-primary-2: var(--rc-garnet);
    --rc-accent: #2F5F8F;
    --rc-border: var(--rc-line);
    --rc-plaque: var(--rc-garnet);
    --rc-apob: #D97706;
    --rc-kidney: #0F8B8D;
    --rc-metabolic: #7C3AED;
    --rc-inflammatory: #EA580C;
    --rc-lpa: #4F46E5;

    --rcckm-ivory: var(--rc-bg);
    --rcckm-ivory-2: #fbf7ef;
    --rcckm-card: var(--rc-surface);
    --rcckm-green: var(--rc-primary);
    --rcckm-green-2: var(--rc-primary-2);
    --rcckm-ink: var(--rc-text);
    --rcckm-muted: var(--rc-muted);
    --rcckm-line: var(--rc-border);
    --rcckm-line-strong: rgba(17, 17, 17, 0.20);
    --rcckm-gold: var(--rc-accent);
}

.stApp {
    background:
        radial-gradient(circle at 10% 0%, var(--rc-garnet-tint), transparent 30rem),
        linear-gradient(180deg, var(--rcckm-ivory) 0%, #f3eadc 100%);
    color: var(--rcckm-ink);
    font-family: var(--rc-font-body);
}

html,
body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stSidebar"],
div[data-testid="stMarkdownContainer"],
div[data-testid="stWidgetLabel"],
input,
textarea,
button {
    font-family: var(--rc-font-body) !important;
}

header[data-testid="stHeader"] {
    background: transparent !important;
    height: 0 !important;
}

div[data-testid="stToolbar"],
#MainMenu,
footer {
    display: none !important;
    visibility: hidden !important;
}

.block-container {
    padding-top: 0.55rem;
    max-width: 1180px;
}

h1, h2, h3, h4,
div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3,
div[data-testid="stMarkdownContainer"] h4 {
    color: var(--rcckm-green);
    font-family: Georgia, "Times New Roman", serif;
    letter-spacing: -0.015em;
}

.rc-report {
    color: var(--rc-text);
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.rc-panel,
.rc-panel-compact {
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.rc-section-title {
    color: var(--rc-primary);
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1.13rem;
    font-weight: 700;
    letter-spacing: -0.012em;
    line-height: 1.1;
}

.rc-card-title {
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    font-size: 1.04rem;
    font-weight: 750;
    letter-spacing: 0;
    line-height: 1.15;
    margin-bottom: 8px;
}

.rc-eyebrow {
    color: rgba(47, 95, 143, 0.88);
    font-size: 0.68rem;
    font-weight: 850;
    letter-spacing: 0.08em;
    line-height: 1.1;
}

.rc-row {
    border-bottom: 1px solid var(--rc-border-soft);
    display: grid;
    gap: 2px;
    padding: 6px 0;
}

.rc-row:last-child {
    border-bottom: 0;
}

.rc-row-title {
    color: var(--rc-text);
    font-size: 0.86rem;
    font-weight: 850;
    line-height: 1.18;
}

.rc-row-detail,
.rc-muted {
    color: rgba(7, 26, 47, 0.58);
    font-size: 0.76rem;
    font-weight: 650;
    line-height: 1.24;
}

.rc-divider {
    border-top: 1px solid var(--rc-border-soft);
    margin: 8px 0;
}

.rc-metric {
    color: var(--rc-text);
    font-size: 1.8rem;
    font-weight: 900;
    letter-spacing: -0.035em;
    line-height: 0.98;
}

div[data-testid="stMarkdownContainer"] p,
label,
.stCaptionContainer {
    color: var(--rcckm-muted);
}

.rcckm-hero {
    border: 1px solid var(--rcckm-line);
    border-radius: 12px;
    background: linear-gradient(180deg, rgba(255,253,248,0.88), rgba(255,253,248,0.70));
    padding: 0.56rem 0.78rem 0.52rem;
    margin-bottom: 0.46rem;
    box-shadow: none;
}

.rcckm-kicker {
    color: var(--rc-garnet);
    font-size: 0.58rem;
    font-weight: 850;
    letter-spacing: 0.105em;
    text-transform: uppercase;
    margin-bottom: 0.16rem;
}

.rcckm-title {
    color: var(--rc-black);
    font-family: Georgia, "Times New Roman", serif;
    font-size: clamp(1.34rem, 2vw, 1.86rem);
    font-weight: 700;
    letter-spacing: -0.024em;
    line-height: 1.0;
}

.rcckm-subtitle {
    color: rgba(7, 26, 47, 0.66);
    font-size: 0.78rem;
    font-weight: 600;
    line-height: 1.15;
    margin-top: 0.14rem;
}

.rcckm-panel-title {
    color: var(--rc-text);
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1.10rem;
    font-weight: 700;
    letter-spacing: -0.008em;
    line-height: 1.15;
    margin: 0 0 0.10rem;
}

.rcckm-panel-title {
    font-family: var(--rc-font-title);
}

.rcckm-card-title,
.detail-section-title {
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    font-size: 1.04rem;
    font-weight: 750;
    letter-spacing: 0;
    line-height: 1.15;
    margin-bottom: 8px;
}

.rcckm-panel-caption,
.rcckm-list-row,
.rcckm-chip,
.rcckm-card-kicker {
    font-family: var(--rc-font-body);
}

.rcckm-panel-caption {
    font-size: 0.84rem;
    line-height: 1.22;
    margin-bottom: 0.18rem;
}

.rcckm-card {
    border: 1px solid var(--rcckm-line);
    border-radius: 18px;
    background: linear-gradient(180deg, #fffdf8 0%, #fbf7ef 100%);
    box-shadow: 0 16px 38px rgba(11, 31, 58, 0.07);
    padding: 16px 18px;
    margin: 12px 0 14px;
}

.rcckm-card-title {
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    font-size: 1.04rem;
    font-weight: 750;
    letter-spacing: 0;
    margin-bottom: 8px;
}

.rcckm-card-kicker {
    color: var(--rc-garnet);
    font-size: 0.72rem;
    font-weight: 850;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

.rcckm-metric-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
}

.rcckm-metric {
    border: 1px solid rgba(11, 31, 58, 0.12);
    border-radius: 14px;
    background: rgba(255, 253, 248, 0.78);
    padding: 10px 12px;
    min-height: 76px;
}

.rcckm-metric-label {
    color: rgba(7, 26, 47, 0.56);
    font-size: 0.72rem;
    font-weight: 850;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.rcckm-metric-value {
    color: var(--rc-black);
    font-size: 1.55rem;
    font-weight: 850;
    line-height: 1.05;
    margin-top: 0.32rem;
}

.rcckm-metric-note {
    color: rgba(7, 26, 47, 0.62);
    font-size: 0.75rem;
    font-weight: 650;
    margin-top: 0.2rem;
}

.rcckm-compact-list {
    display: flex;
    flex-direction: column;
    gap: 7px;
}

.rcckm-list-row {
    border: 1px solid rgba(11, 31, 58, 0.11);
    border-radius: 11px;
    background: rgba(255, 253, 248, 0.72);
    color: rgba(7, 26, 47, 0.82);
    font-size: 0.88rem;
    font-weight: 650;
    line-height: 1.3;
    padding: 8px 10px;
}

.rcckm-list-row strong {
    color: var(--rcckm-green);
    font-weight: 850;
}

@media (max-width: 850px) {
    .rcckm-metric-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

.rcckm-panel-caption {
    color: var(--rcckm-muted);
    font-size: 0.84rem;
    font-weight: 620;
    line-height: 1.25;
    margin-bottom: 0.24rem;
}

.rcckm-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin: 0.7rem 0 0.65rem;
}

.rcckm-chip {
    border: 1px solid var(--rcckm-line-strong);
    border-radius: 999px;
    background: rgba(255, 253, 248, 0.88);
    color: var(--rcckm-green);
    display: inline-flex;
    font-size: 0.78rem;
    font-weight: 800;
    padding: 0.26rem 0.68rem;
}

.rcckm-chip-muted {
    color: var(--rcckm-muted);
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: var(--rcckm-line) !important;
    border-radius: 12px !important;
    background: rgba(255, 253, 248, 0.72) !important;
    box-shadow: none;
    padding: 0.42rem 0.58rem !important;
    margin-bottom: 0.38rem !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlock"] {
    gap: 0.16rem !important;
}

div[data-testid="stNumberInput"],
div[data-testid="stSelectbox"],
div[data-testid="stCheckbox"],
div[data-testid="stTextInput"],
div[data-testid="stTextArea"] {
    margin-bottom: 0 !important;
}

div[data-testid="stWidgetLabel"] label,
div[data-testid="stWidgetLabel"] p {
    color: rgba(7, 26, 47, 0.66) !important;
    font-size: 0.84rem !important;
    font-weight: 700 !important;
    line-height: 1.14 !important;
    margin-bottom: 0.14rem !important;
}

div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    border-color: rgba(11, 31, 58, 0.18) !important;
    border-radius: 9px !important;
    background: #fffefa !important;
    color: var(--rcckm-ink) !important;
    box-shadow: none !important;
}

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {
    font-size: 0.94rem !important;
    font-weight: 720 !important;
    min-height: 1.86rem !important;
    padding-bottom: 0.10rem !important;
    padding-top: 0.10rem !important;
}

div[data-testid="stNumberInput"] button {
    min-height: 2rem !important;
    width: 2rem !important;
}

div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    font-size: 0.94rem !important;
    min-height: 1.86rem !important;
}

div[data-testid="stCheckbox"] label {
    min-height: 1.16rem !important;
    padding-bottom: 0 !important;
    padding-top: 0 !important;
}

div[data-testid="stCheckbox"] p {
    font-size: 0.86rem !important;
    font-weight: 650 !important;
    line-height: 1.18 !important;
}

div[data-testid="stExpander"] {
    border: 1px solid rgba(11, 31, 58, 0.10) !important;
    border-radius: 10px !important;
    background: rgba(255, 253, 248, 0.54) !important;
    box-shadow: none !important;
    margin-top: 0.22rem !important;
}

div[data-testid="stExpander"] details summary {
    border: 0 !important;
    box-shadow: none !important;
    min-height: 1.75rem !important;
    padding: 0.22rem 0.55rem !important;
}

div[data-testid="stExpander"] details summary p {
    color: rgba(7, 26, 47, 0.62) !important;
    font-size: 0.84rem !important;
    font-weight: 720 !important;
}

div[data-testid="stTextArea"] textarea {
    font-size: 0.92rem !important;
    line-height: 1.22 !important;
    min-height: 90px !important;
    padding: 0.40rem 0.52rem !important;
}

.stCaptionContainer,
div[data-testid="stCaptionContainer"],
div[data-testid="stCaptionContainer"] p {
    color: rgba(7, 26, 47, 0.55) !important;
    font-size: 0.80rem !important;
    font-weight: 620 !important;
    line-height: 1.22 !important;
}

.stButton > button[kind="secondary"],
div[data-testid="stButton"] button[kind="secondary"],
div[data-testid="stButton"] button {
    border: 1px solid rgba(11, 31, 58, 0.18) !important;
    border-radius: 999px !important;
    background: rgba(255, 253, 248, 0.82) !important;
    color: var(--rcckm-green) !important;
    font-size: 0.78rem !important;
    font-weight: 800 !important;
    line-height: 1 !important;
    min-height: 1.62rem !important;
    padding: 0.10rem 0.44rem !important;
    white-space: nowrap !important;
}

div[data-testid="stButton"] button p,
.stButton > button p {
    color: inherit !important;
}

.stButton > button[kind="primary"],
div[data-testid="stButton"] button[kind="primary"] {
    border: 1px solid var(--rcckm-green) !important;
    border-radius: 999px !important;
    background: var(--rcckm-green) !important;
    color: #fffdf8 !important;
    font-size: 0.80rem !important;
    font-weight: 850 !important;
    line-height: 1 !important;
    min-height: 1.78rem !important;
    padding: 0.20rem 0.72rem !important;
    white-space: nowrap !important;
}

.stButton > button[kind="primary"]:hover,
div[data-testid="stButton"] button[kind="primary"]:hover {
    border-color: var(--rc-garnet) !important;
    background: var(--rc-garnet) !important;
    color: #fffdf8 !important;
}

.stButton > button[kind="secondary"]:hover,
div[data-testid="stButton"] button[kind="secondary"]:hover,
div[data-testid="stButton"] button:not([kind="primary"]):hover {
    border-color: rgba(11, 31, 58, 0.26) !important;
    background: rgba(11, 31, 58, 0.06) !important;
    color: var(--rcckm-green) !important;
}

.stButton > button:disabled,
.stButton > button[disabled],
div[data-testid="stButton"] button:disabled,
div[data-testid="stButton"] button[disabled] {
    border: 1px solid rgba(11, 31, 58, 0.12) !important;
    background: rgba(11, 31, 58, 0.10) !important;
    color: rgba(11, 31, 58, 0.45) !important;
    cursor: not-allowed !important;
    opacity: 1 !important;
}

div[data-testid="stDataFrame"] {
    border: 1px solid var(--rcckm-line);
    border-radius: 14px;
    overflow: hidden;
}

div[data-testid="stRadio"] {
    background: rgba(255, 253, 248, 0.55);
    border: 1px solid var(--rcckm-line);
    border-radius: 999px;
    padding: 0.2rem 0.6rem;
    width: fit-content;
}

hr {
    border-color: var(--rcckm-line);
}
</style>
        """.replace("/*COMPONENT_THEME*/", component_theme_css()),
    )


def render_brand_header(st):
    render_html(
        st,
        """
<section class="rcckm-hero">
    <div class="rcckm-kicker">Cardiovascular &middot; Kidney &middot; Metabolic</div>
    <div class="rcckm-title">Risk Continuum CKM</div>
    <div class="rcckm-subtitle">Structured clinical interpretation layer</div>
</section>
        """,
    )


def section_heading(st, title, caption=None):
    caption_html = f'<div class="rcckm-panel-caption">{caption}</div>' if caption else ""
    render_html(
        st,
        f"""
<div>
    <div class="rcckm-panel-title">{title}</div>
    {caption_html}
</div>
        """,
    )


def status_chips_html(items):
    chips = []
    for label, count in items:
        chips.append(f'<span class="rcckm-chip">{label}: {count}</span>')
    return '<div class="rcckm-chip-row">' + "".join(chips) + "</div>"

