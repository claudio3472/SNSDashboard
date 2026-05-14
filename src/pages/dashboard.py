# ============================================================
# dashboard.py
# ============================================================

import os
import pandas as pd

from dash import (
    html,
    dcc,
    Input,
    Output,
    callback,
)

import plotly.graph_objects as go
import plotly.express as px

# ============================================================
# LOAD DATA
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

DATA_PATH = os.path.join(
    BASE_DIR,
    "..",
    "data",
    "processed",
    "master_dataset.csv"
)

df = pd.read_csv(DATA_PATH)

df["ano"] = df["ano"].astype(int)
df["regiao"] = df["regiao"].astype(str).str.strip()
df["instituicao"] = df["instituicao"].astype(str).str.strip()

REGIOES = [
    "Norte",
    "Centro",
    "Lisboa e Vale do Tejo",
    "Alentejo",
    "Algarve",
]

ANOS = sorted(
    df["ano"]
    .astype(int)
    .unique()
    .tolist()
)

REGION_OPTIONS = [
    {"label": "Todas as regiões", "value": "all"}
] + [
    {"label": r, "value": r}
    for r in REGIOES
]

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
# LAYOUT
# ============================================================

layout = html.Div(
    className="content",
    children=[

        html.H2("Dashboard Geral"),

        html.P("Visão global do SNS"),

        html.Div(
            className="filter-row",
            children=[
                dcc.Dropdown(
                    id="dashboard-region-filter",
                    options=REGION_OPTIONS,
                    value="all",
                    clearable=False,
                    placeholder="Selecionar região",
                ),

                dcc.Dropdown(
                    id="dashboard-institution-filter",
                    value="all",
                    clearable=False,
                    placeholder="Selecionar instituição",
                ),
            ],
        ),

        html.Div(
            className="slider-container",
            children=[
                html.Label("Filtrar por Ano"),

                dcc.RangeSlider(
                    id="dashboard-slider",
                    min=int(min(ANOS)),
                    max=int(max(ANOS)),
                    step=1,
                    value=[
                        int(min(ANOS)),
                        int(max(ANOS)),
                    ],
                    marks={
                        int(ano): str(ano)
                        for ano in ANOS
                    },
                    tooltip={
                        "placement": "bottom"
                    },
                ),
            ],
        ),

        html.Div(
            id="dashboard-kpis"
        ),

        html.Div(
            className="grid-2x2",
            children=[
                dcc.Graph(id="dashboard-finance"),
                dcc.Graph(id="dashboard-pie"),
                dcc.Graph(id="dashboard-prof"),
                dcc.Graph(id="dashboard-radar"),
            ],
        ),
    ],
)

# ============================================================
# INSTITUTION FILTER CALLBACK
# ============================================================

@callback(
    Output("dashboard-institution-filter", "options"),
    Output("dashboard-institution-filter", "value"),
    Input("dashboard-region-filter", "value"),
)
def update_dashboard_institution_filter(region):

    dff = df.copy()

    if region != "all":
        dff = dff[dff["regiao"] == region]

    options = [
        {"label": "Todas as instituições", "value": "all"}
    ] + [
        {
            "label": inst,
            "value": inst,
        }
        for inst in sorted(
            dff["instituicao"]
            .dropna()
            .unique()
        )
    ]

    return options, "all"

# ============================================================
# CALLBACK
# ============================================================

@callback(
    [
        Output("dashboard-kpis", "children"),
        Output("dashboard-finance", "figure"),
        Output("dashboard-pie", "figure"),
        Output("dashboard-prof", "figure"),
        Output("dashboard-radar", "figure"),
    ],
    [
        Input("dashboard-slider", "value"),
        Input("dashboard-region-filter", "value"),
        Input("dashboard-institution-filter", "value"),
    ],
)
def update_dashboard(
    year_range,
    selected_region,
    selected_institution,
):

    ano_inicio, ano_fim = year_range

    df_filtered = df[
        (df["ano"] >= ano_inicio)
        & (df["ano"] <= ano_fim)
    ].copy()

    if selected_region != "all":
        df_filtered = df_filtered[
            df_filtered["regiao"] == selected_region
        ]

    if selected_institution != "all":
        df_filtered = df_filtered[
            df_filtered["instituicao"] == selected_institution
        ]

    # ========================================================
    # KPI VALUES
    # ========================================================

    kpi_urgencias = int(
        df_filtered["total_urgencias"].sum()
    )

    kpi_consultas = int(
        df_filtered["no_de_consultas_medicas_total"].sum()
    )

    kpi_divida = (
        df_filtered["divida_total_fornecedores_externos"].sum()
        / 1e6
    )

    kpi_instituicoes = (
        df_filtered["instituicao"].nunique()
    )

    kpis = html.Div(
        className="kpi-row",
        children=[
            kpi_card(
                "Urgências Totais",
                f"{kpi_urgencias:,}".replace(",", " ")
            ),

            kpi_card(
                "Consultas Médicas",
                f"{kpi_consultas:,}".replace(",", " ")
            ),

            kpi_card(
                "Dívida Total (M€)",
                f"{kpi_divida:,.1f}"
            ),

            kpi_card(
                "Instituições",
                f"{kpi_instituicoes}"
            ),
        ],
    )

    # ========================================================
    # GASTOS vs RENDIMENTOS
    # ========================================================

    finance = (
        df_filtered
        .groupby("regiao")[
            [
                "gastos_operacionais",
                "rendimentos_operacionais",
            ]
        ]
        .sum()
        .reindex(REGIOES)
        .fillna(0)
        / 1e6
    )

    fig_gastos = go.Figure()

    fig_gastos.add_bar(
        x=finance.index,
        y=finance["gastos_operacionais"],
        name="Gastos",
    )

    fig_gastos.add_bar(
        x=finance.index,
        y=finance["rendimentos_operacionais"],
        name="Rendimentos",
    )

    fig_gastos.update_layout(
        barmode="group",
        title="Gastos vs Rendimentos por Região (M€)",
        height=360,
    )

    # ========================================================
    # PIE
    # ========================================================

    fig_pie = px.pie(
        finance.reset_index(),
        names="regiao",
        values="gastos_operacionais",
        title="Distribuição de Custos Operacionais",
        hole=0.35,
    )

    # ========================================================
    # PROFISSIONAIS
    # ========================================================

    prof = (
        df_filtered
        .groupby("regiao")[
            [
                "medicos_internos",
                "enfermeiros",
            ]
        ]
        .sum()
        .reindex(REGIOES)
        .fillna(0)
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

    # ========================================================
    # RADAR
    # ========================================================

    df_filtered = df_filtered.copy()

    df_filtered["total_cirurgias"] = (
        df_filtered[
            [
                "no_intervencoes_cirurgicas_programadas",
                "no_intervencoes_cirurgicas_convencionais",
                "no_intervencoes_cirurgicas_urgentes",
            ]
        ]
        .sum(axis=1)
    )

    radar_df = (
        df_filtered
        .groupby("regiao")[
            [
                "total_urgencias",
                "total_cirurgias",
                "no_de_consultas_medicas_total",
            ]
        ]
        .sum()
        .reindex(REGIOES)
        .fillna(0)
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

    return (
        kpis,
        fig_gastos,
        fig_pie,
        fig_prof,
        fig_radar,
    )