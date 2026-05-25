from renderers.continuum_bar import build_continuum_bar_html, render_continuum_bar


def build_risk_continuum_html(result):
    """Build the compact RCCKM risk-continuum HTML strip."""
    return build_continuum_bar_html(None, result)


def render_risk_continuum(result):
    """Render the RCCKM risk-continuum strip in Streamlit."""
    render_continuum_bar(None, result)
