from dash import Dash, html, dcc, Input, Output

import pages.dashboard as dashboard
import pages.mapa as mapa
import pages.stress as stress
import pages.financeira as financeira
import pages.medicamentos as medicamentos
import pages.contas as contas

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
)

# ---------------- SIDEBAR ----------------
sidebar = html.Div(
    className="sidebar",
    children=[
        html.H3(
            "SNS Dashboard",
            className="sidebar-title",
            style={
                "paddingLeft": "14px",
                "marginTop": "10px",
            },
        ),

        dcc.Link("Dashboard Geral", href="/dashboard", className="sidebar-link"),
        dcc.Link("Mapa Regional", href="/mapa", className="sidebar-link"),
        dcc.Link("Stress Hospitalar", href="/stress", className="sidebar-link"),
        dcc.Link("Evolução Financeira", href="/financeira", className="sidebar-link"),
        dcc.Link("Medicamentos", href="/medicamentos", className="sidebar-link"),
        dcc.Link("Contas SNS", href="/contas", className="sidebar-link"),
    ],
)

# ---------------- APP LAYOUT ----------------
app.layout = html.Div(
    className="app-wrapper",
    children=[
        dcc.Location(id="url"),
        sidebar,
        html.Div(id="page-content", className="page-content"),
    ],
)

# ---------------- ROUTER ----------------
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
)
def render_page(pathname):

    if pathname in (None, "/", "/dashboard"):
        return dashboard.layout
    elif pathname == "/mapa":
        return mapa.layout
    elif pathname == "/stress":
        return stress.layout
    elif pathname == "/financeira":
        return financeira.layout
    elif pathname == "/medicamentos":
        return medicamentos.layout
    elif pathname == "/contas":
        return contas.layout

    return html.H2("404 — Página não encontrada")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)