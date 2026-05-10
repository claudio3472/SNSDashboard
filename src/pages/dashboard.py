import pandas as pd
import numpy as np
import os

from dash import html, dcc
import plotly.graph_objects as go
import plotly.express as px

# ============================================================
# LOAD DATA
# ============================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "processed", "master_dataset.csv")

df = pd.read_csv(DATA_PATH)

year = df["ano"].max()
df_year = df[df["ano"] == year].copy()

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
kpi_urgencias = int(df_year["total_urgencias"].sum())
kpi_consultas = int(df_year["no_de_consultas_medicas_total"].sum())
kpi_divida = df_year["divida_total_fornecedores_externos"].sum() / 1e6
kpi_instituicoes = df["instituicao"].nunique()

# ============================================================
# GASTOS vs RENDIMENTOS
# ============================================================
finance = (
    df_year
    .groupby("regiao")[["gastos_operacionais", "rendimentos_operacionais"]]
    .sum()
    .reindex(REGIOES)
    / 1e6
)

fig_gastos = go.Figure()
fig_gastos.add_bar(
    x=finance.index,
    y=finance["gastos_operacionais"],
    name="Gastos",
    marker_color="#ef4444",
)
fig_gastos.add_bar(
    x=finance.index,
    y=finance["rendimentos_operacionais"],
    name="Rendimentos",
    marker_color="#0f172a",
)

fig_gastos.update_layout(
    barmode="group",
    title="Gastos vs Rendimentos por Região (M€)",
    height=360,
)

# ============================================================
# ENCARGOS MEDICAMENTOS
# ============================================================
fig_medicamentos = px.pie(
    finance.reset_index(),
    names="regiao",
    values="gastos_operacionais",
    title="Encargos com Medicamentos / Custos Operacionais",
    hole=0.35,
)

# ============================================================
# PROFISSIONAIS
# ============================================================
prof = (
    df_year
    .groupby("regiao")[["medicos_internos", "enfermeiros"]]
    .sum()
    .reindex(REGIOES)
)

fig_prof = go.Figure()
fig_prof.add_bar(
    y=prof.index,
    x=prof["medicos_internos"],
    name="Médicos",
    orientation="h",
)
fig_prof.add_bar(
    y=prof.index,
    x=prof["enfermeiros"],
    name="Enfermeiros",
    orientation="h",
)

fig_prof.update_layout(
    barmode="stack",
    title="Profissionais por Região",
    height=360,
)

# ============================================================
# RADAR
# ============================================================
df_year["total_cirurgias"] = df_year[
    [
        "no_intervencoes_cirurgicas_programadas",
        "no_intervencoes_cirurgicas_convencionais",
        "no_intervencoes_cirurgicas_urgentes",
    ]
].sum(axis=1)

radar_df = (
    df_year
    .groupby("regiao")[[
        "total_urgencias",
        "total_cirurgias",
        "no_de_consultas_medicas_total",
    ]]
    .sum()
    .reindex(REGIOES)
)

fig_radar = go.Figure()
for col in radar_df.columns:
    fig_radar.add_trace(
        go.Scatterpolar(
            r=radar_df[col],
            theta=radar_df.index,
            fill="toself",
            name=col,
        )
    )

fig_radar.update_layout(
    title="Atividade Assistencial por Região",
    height=360,
)

# ============================================================
# KPI CARD
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
# ✅ LAYOUT (STATIC, STABLE)
# ============================================================
layout = html.Div(
    className="content",
    children=[
        html.H2("Dashboard Geral"),
        html.P(f"Dados referentes a {year}"),

        html.Div(
            className="kpi-row",
            children=[
                kpi_card("Urgências Totais", f"{kpi_urgencias:,}".replace(",", " ")),
                kpi_card("Consultas Médicas", f"{kpi_consultas:,}".replace(",", " ")),
                kpi_card("Dívida Total (M€)", f"{kpi_divida:,.1f}"),
                kpi_card("Instituições", kpi_instituicoes),
            ],
        ),

        html.Div(
            className="grid-2x2",
            children=[
                html.Div(className="card", children=dcc.Graph(figure=fig_gastos)),
                html.Div(className="card", children=dcc.Graph(figure=fig_medicamentos)),
                html.Div(className="card", children=dcc.Graph(figure=fig_prof)),
                html.Div(className="card", children=dcc.Graph(figure=fig_radar)),
            ],
        ),
    ],
)
