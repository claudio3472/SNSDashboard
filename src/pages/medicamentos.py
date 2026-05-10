from dash import html, dcc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# DATA LOAD
# ============================================================
df = pd.read_csv("data/processed/medicamento_hospitalar.csv")

df["tempo"] = pd.to_datetime(df["tempo"])
df["ano"] = df["ano"].astype(int)

REGIOES = [
    "Norte",
    "Centro",
    "Lisboa e Vale do Tejo",
    "Alentejo",
    "Algarve",
]

# ============================================================
# KPIs
# ============================================================
total_encargos = df["encargos_sns_hospitalar"].sum() / 1e6
num_periodos = df["tempo"].nunique()
media_mensal = df["encargos_sns_hospitalar"].mean() / 1e6

# ============================================================
# EVOLUÇÃO MENSAL
# ============================================================
ts_mensal = (
    df.groupby("tempo")["encargos_sns_hospitalar"]
    .sum()
    .reset_index()
)

ts_mensal["encargos_sns_hospitalar"] /= 1e6
ts_mensal["rolling_3m"] = ts_mensal["encargos_sns_hospitalar"].rolling(3).mean()

fig_ts = go.Figure()
fig_ts.add_trace(go.Scatter(
    x=ts_mensal["tempo"],
    y=ts_mensal["encargos_sns_hospitalar"],
    mode="lines",
    name="Encargos"
))
fig_ts.add_trace(go.Scatter(
    x=ts_mensal["tempo"],
    y=ts_mensal["rolling_3m"],
    mode="lines",
    name="Média Móvel (3m)",
    line=dict(width=3, dash="dot")
))

fig_ts.update_layout(
    title="Evolução Temporal dos Encargos (M€)",
    height=360,
)

# ============================================================
# SUPPORTING CHARTS
# ============================================================
gastos_regiao = (
    df.groupby("regiao")["encargos_sns_hospitalar"]
    .sum()
    .reindex(REGIOES)
    .reset_index()
)
gastos_regiao["encargos_sns_hospitalar"] /= 1e6

fig_regiao = px.pie(
    gastos_regiao,
    names="regiao",
    values="encargos_sns_hospitalar",
    hole=0.4,
    title="Distribuição por Região",
)

ts_anual = (
    df.groupby("ano")["encargos_sns_hospitalar"]
    .sum()
    .reset_index()
)
ts_anual["encargos_sns_hospitalar"] /= 1e6

fig_anual = px.bar(
    ts_anual,
    x="ano",
    y="encargos_sns_hospitalar",
    title="Evolução Anual (M€)",
)

comp_regiao = (
    df.groupby(["ano", "regiao"])["encargos_sns_hospitalar"]
    .sum()
    .reset_index()
)
comp_regiao["encargos_sns_hospitalar"] /= 1e6

fig_comp = px.line(
    comp_regiao,
    x="ano",
    y="encargos_sns_hospitalar",
    color="regiao",
    title="Comparação por Região (M€/ano)",
)

# ============================================================
# LAYOUT
# ============================================================
def kpi_card(title, value):
    return html.Div(
        className="kpi-card",
        children=[
            html.Div(title, className="kpi-title"),
            html.Div(value, className="kpi-value"),
        ],
    )

layout = html.Div(
    className="content",
    children=[
        html.H2("Medicamentos Hospitalares"),
        html.P("Encargos SNS com medicamentos"),

        html.Div(
            className="kpi-row",
            children=[
                kpi_card("Total Encargos", f"{total_encargos:,.1f} M €"),
                kpi_card("Períodos", f"{num_periodos}"),
                kpi_card("Média Mensal", f"{media_mensal:,.1f} M €"),
            ],
        ),

        html.Div(
            className="grid-2x2",
            children=[
                dcc.Graph(figure=fig_ts),
                dcc.Graph(figure=fig_regiao),
                dcc.Graph(figure=fig_anual),
                dcc.Graph(figure=fig_comp),
            ],
        ),
    ],
)