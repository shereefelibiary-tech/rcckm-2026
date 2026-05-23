from renderers.continuum_bar import build_continuum_bar_html, render_continuum_bar


def build_risk_continuum_html(result):
    return build_continuum_bar_html(None, result)


def render_risk_continuum(result):
    render_continuum_bar(None, result)
