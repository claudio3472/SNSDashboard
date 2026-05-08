from dash import Dash, html, dcc, Input, Output

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
)

# ---------------- SIDEBAR ----------------
sidebar = html.Div(
    className="sidebar",
    children=[
        html.H3("SNS Dashboard", className="sidebar-title"),

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

    # ✅ default page on load
    if pathname in (None, "/", "/dashboard"):
        from pages.dashboard import layout
        return layout

    elif pathname == "/mapa":
        from pages.mapa import layout
        return layout

    elif pathname == "/stress":
        from pages.stress import layout
        return layout

    elif pathname == "/financeira":
        from pages.financeira import layout
        return layout

    elif pathname == "/medicamentos":
        from pages.medicamentos import layout
        return layout

    elif pathname == "/contas":
        from pages.contas import layout
        return layout

    return html.H2("404 — Página não encontrada")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)