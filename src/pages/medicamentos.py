# ============================================================
# medicamentos.py
# ============================================================

from dash import (
    html,
    dcc,
    callback,
    Input,
    Output,
)

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ============================================================
# DATA
# ============================================================

df = pd.read_csv(
    "data/processed/medicamento_hospitalar.csv"
)

df["tempo"] = pd.to_datetime(
    df["tempo"]
)

df["ano"] = df["ano"].astype(int)
df["regiao"] = df["regiao"].astype(str).str.strip()

REGIOES = [
    "Norte",
    "Centro",
    "Lisboa e Vale do Tejo",
    "Alentejo",
    "Algarve",
]

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
# MAIN GRAPH FUNCTION
# ============================================================

def build_main_graph(dff):

    ts = (
        dff.groupby("tempo")[
            "encargos_sns_hospitalar"
        ]
        .sum()
        .reset_index()
    )

    ts["encargos_sns_hospitalar"] /= 1e6

    ts["rolling_3m"] = (
        ts["encargos_sns_hospitalar"]
        .rolling(3)
        .mean()
    )

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=ts["tempo"],
        y=ts["encargos_sns_hospitalar"],
        mode="lines",
        name="Encargos",
    ))

    fig.add_trace(go.Scatter(
        x=ts["tempo"],
        y=ts["rolling_3m"],
        mode="lines",
        name="Média Móvel",
        line=dict(
            width=3,
            dash="dot",
        ),
    ))

    fig.update_layout(
        title="Evolução Temporal dos Encargos",
        height=360,
        uirevision="constant",
        xaxis=dict(
            rangeslider=dict(
                visible=True
            ),
            type="date",
        ),
    )

    return fig

# ============================================================
# LAYOUT
# ============================================================

layout = html.Div(
    className="content",
    children=[

        html.H2("Medicamentos Hospitalares"),

        html.P("Encargos SNS com medicamentos"),

        html.Div(
            className="filter-row",
            children=[
                dcc.Dropdown(
                    id="med-region-filter",
                    options=REGION_OPTIONS,
                    value="all",
                    clearable=False,
                    placeholder="Selecionar região",
                ),
            ],
        ),

        dcc.Store(
            id="store-range-med"
        ),

        html.Div(
            id="med-kpis",
            className="kpi-row",
        ),

        html.Div(
            className="grid-2x2",
            children=[
                html.Div(
                    className="card",
                    children=[
                        dcc.Graph(id="med-graph")
                    ],
                ),

                html.Div(
                    className="card",
                    children=[
                        dcc.Graph(id="med-regiao")
                    ],
                ),

                html.Div(
                    className="card",
                    children=[
                        dcc.Graph(id="med-anual")
                    ],
                ),

                html.Div(
                    className="card",
                    children=[
                        dcc.Graph(id="med-comp")
                    ],
                ),
            ],
        ),
    ],
)

# ============================================================
# CALLBACK 1
# GUARDA RANGE
# ============================================================

@callback(
    Output("store-range-med", "data"),
    Input("med-graph", "relayoutData"),
)
def guardar_range(relayoutData):

    if not relayoutData:
        return {}

    if "xaxis.range[0]" in relayoutData:
        return {
            "start": relayoutData["xaxis.range[0]"],
            "end": relayoutData["xaxis.range[1]"],
        }

    if "xaxis.range" in relayoutData:
        return {
            "start": relayoutData["xaxis.range"][0],
            "end": relayoutData["xaxis.range"][1],
        }

    if "xaxis.autorange" in relayoutData:
        return {}

    return {}

# ============================================================
# CALLBACK 2
# UPDATE
# ============================================================

@callback(
    Output("med-kpis", "children"),
    Output("med-graph", "figure"),
    Output("med-regiao", "figure"),
    Output("med-anual", "figure"),
    Output("med-comp", "figure"),
    Input("store-range-med", "data"),
    Input("med-region-filter", "value"),
)
def update_dashboard(
    range_data,
    selected_region,
):

    dff_base = df.copy()

    if selected_region != "all":
        dff_base = dff_base[
            dff_base["regiao"] == selected_region
        ]

    dff = dff_base.copy()

    if (
        range_data
        and "start" in range_data
    ):
        start = pd.to_datetime(
            range_data["start"]
        )

        end = pd.to_datetime(
            range_data["end"]
        )

        dff = dff[
            (dff["tempo"] >= start)
            & (dff["tempo"] <= end)
        ]

    # ========================================================
    # KPIs
    # ========================================================

    total_encargos = (
        dff["encargos_sns_hospitalar"].sum()
        / 1e6
    )

    num_periodos = (
        dff["tempo"].nunique()
    )

    media_mensal = (
        dff["encargos_sns_hospitalar"].mean()
        / 1e6
    )

    kpis = [
        kpi_card(
            "Total Encargos",
            f"{total_encargos:,.1f} M €"
        ),

        kpi_card(
            "Períodos",
            f"{num_periodos}"
        ),

        kpi_card(
            "Média Mensal",
            f"{media_mensal:,.1f} M €"
        ),
    ]

    # ========================================================
    # MAIN GRAPH
    # ========================================================

    fig_main = build_main_graph(dff_base)

    # ========================================================
    # REGIÃO
    # ========================================================

    regiao = (
        dff.groupby("regiao")[
            "encargos_sns_hospitalar"
        ]
        .sum()
        .reindex(REGIOES)
        .fillna(0)
        / 1e6
    ).reset_index()

    fig_regiao = px.pie(
        regiao,
        names="regiao",
        values="encargos_sns_hospitalar",
        hole=0.4,
        title="Distribuição por Região",
    )

    # ========================================================
    # ANUAL
    # ========================================================

    anual = (
        dff.groupby("ano")[
            "encargos_sns_hospitalar"
        ]
        .sum()
        / 1e6
    ).reset_index()

    fig_anual = px.bar(
        anual,
        x="ano",
        y="encargos_sns_hospitalar",
        title="Evolução Anual",
    )

    # ========================================================
    # COMPARAÇÃO
    # ========================================================

    comp = (
        dff.groupby(
            [
                "ano",
                "regiao",
            ]
        )[
            "encargos_sns_hospitalar"
        ]
        .sum()
        / 1e6
    ).reset_index()

    fig_comp = px.line(
        comp,
        x="ano",
        y="encargos_sns_hospitalar",
        color="regiao",
        title="Comparação por Região",
    )

    return (
        kpis,
        fig_main,
        fig_regiao,
        fig_anual,
        fig_comp,
    )