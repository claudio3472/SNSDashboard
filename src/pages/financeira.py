from dash import html, dcc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# DATA LOAD
# ============================================================
df = pd.read_csv("data/processed/master_dataset.csv")

# Ensure year is sorted
df["ano"] = df["ano"].astype(int)

REGIOES = [
    "Norte",
    "Centro",
    "Lisboa e Vale do Tejo",
    "Alentejo",
    "Algarve",
]

# ============================================================
# KPI CALCULATIONS
# ============================================================
total_gastos = df["gastos_operacionais"].sum() / 1e6
total_rendimentos = df["rendimentos_operacionais"].sum() / 1e6
balanco = total_rendimentos - total_gastos
regioes_analisadas = df["regiao"].nunique()

# ============================================================
# 1️⃣ EVOLUÇÃO GASTOS vs RENDIMENTOS (TEMPORAL)
# ============================================================
ts = (
    df.groupby("ano")[["gastos_operacionais", "rendimentos_operacionais"]]
    .sum()
    / 1e6
).reset_index()

fig_evolucao = go.Figure()

fig_evolucao.add_trace(go.Scatter(
    x=ts["ano"],
    y=ts["rendimentos_operacionais"],
    mode="lines",
    name="Rendimentos",
    line=dict(color="#16a34a"),
))

fig_evolucao.add_trace(go.Scatter(
    x=ts["ano"],
    y=ts["gastos_operacionais"],
    mode="lines",
    name="Gastos",
    line=dict(color="#dc2626"),
    fill="tonexty",
))

fig_evolucao.update_layout(
    title="Evolução Gastos vs Rendimentos (M€)",
    height=360,
    legend=dict(orientation="h", y=-0.2),
)

# ============================================================
# 2️⃣ GASTOS POR REGIÃO (PIE)
# ============================================================
gastos_regiao = (
    df.groupby("regiao")["gastos_operacionais"]
    .sum()
    .reindex(REGIOES)
    / 1e6
).reset_index()

fig_gastos_regiao = px.pie(
    gastos_regiao,
    names="regiao",
    values="gastos_operacionais",
    title="Gastos por Região (Fatia)",
    hole=0.4,
)

# ============================================================
# 3️⃣ ORÇAMENTO vs EXECUÇÃO (APROXIMAÇÃO)
# ============================================================
# Nota: como não existe orçamento separado no master_dataset,
# usamos rendimentos = orçamento proxy e gastos = execução proxy

orc_exec = (
    df.groupby("ano")[["rendimentos_operacionais", "gastos_operacionais"]]
    .sum()
    / 1e6
).reset_index()

fig_orc_exec = go.Figure()

fig_orc_exec.add_trace(go.Bar(
    x=orc_exec["ano"],
    y=orc_exec["rendimentos_operacionais"],
    name="Orçamento (proxy)",
    marker_color="#2563eb",
))

fig_orc_exec.add_trace(go.Bar(
    x=orc_exec["ano"],
    y=orc_exec["gastos_operacionais"],
    name="Execução (proxy)",
    marker_color="#22c55e",
))

fig_orc_exec.update_layout(
    title="Orçamento vs Execução SNS (M€)",
    barmode="group",
    height=360,
)

# ============================================================
# 4️⃣ DÍVIDA POR REGIÃO (DONUT)
# ============================================================
divida_regiao = (
    df.groupby("regiao")["divida_total_fornecedores_externos"]
    .sum()
    .reindex(REGIOES)
    / 1e6
).reset_index()

fig_divida = px.pie(
    divida_regiao,
    names="regiao",
    values="divida_total_fornecedores_externos",
    title="Dívida por Região (Fatia)",
    hole=0.45,
)

# ============================================================
# KPI CARD COMPONENT
# ============================================================
def kpi_card(title, value):
    return html.Div(
        className="kpi-card",
        children=[
            html.Div(title, className="kpi-title"),
            html.Div(value, className="kpi-value"),
        ],
    )

# ============================================================
# LAYOUT
# ============================================================
layout = html.Div(
    className="content",
    children=[
        html.H2("Evolução Financeira"),
        html.P("Análise de gastos, rendimentos e dívida"),

        html.Div(
            className="kpi-row",
            children=[
                kpi_card("Total Gastos", f"{total_gastos:,.0f} M €"),
                kpi_card("Total Rendimentos", f"{total_rendimentos:,.0f} M €"),
                kpi_card("Balanço", f"{balanco:,.0f} M €"),
                kpi_card("Regiões Analisadas", f"{regioes_analisadas}"),
            ],
        ),

        html.Div(
            className="grid-2x2",
            children=[
                dcc.Graph(figure=fig_evolucao),
                dcc.Graph(figure=fig_gastos_regiao),
                dcc.Graph(figure=fig_orc_exec),
                dcc.Graph(figure=fig_divida),
            ],
        ),
    ],
)