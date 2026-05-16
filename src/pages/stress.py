import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from dash import html, dcc, Input, Output, callback

# ============================================================
# DATA LOAD & PREP
# ============================================================
df = pd.read_csv("data/processed/master_dataset.csv")

df["regiao"] = df["regiao"].astype(str).str.strip()
df["instituicao"] = df["instituicao"].astype(str).str.strip()

df["tempo"] = pd.to_datetime(
    dict(
        year=df["ano"].astype(int),
        month=df["mes"].astype(int),
        day=1,
    )
)

df["total_staff"] = df["medicos_internos"] + df["enfermeiros"]

df["stress_index"] = (
    df["total_urgencias"] /
    df["total_staff"].replace(0, np.nan)
) * 10

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
# LAYOUT
# ============================================================

layout = html.Div(
    className="content",
    children=[
        html.H2("Stress Hospitalar"),
        html.P("Relação entre profissionais e atividade assistencial"),

        html.Div(
            className="filter-row",
            children=[
                dcc.Dropdown(
                    id="stress-region-filter-v2",
                    options=REGION_OPTIONS,
                    value="all",
                    clearable=False,
                    placeholder="Selecionar região",
                ),

                dcc.Dropdown(
                    id="stress-institution-filter-v2",
                    value="all",
                    clearable=False,
                    placeholder="Selecionar instituição",
                ),
            ],
        ),

        html.Div(
            className="card",
            children=dcc.Graph(id="stress-ts-v2"),
        ),

        html.Div(
            className="grid-2x2",
            children=[
                html.Div(
                    className="card",
                    children=dcc.Graph(id="stress-scatter-v2"),
                ),

                html.Div(
                    className="card",
                    children=dcc.Graph(id="stress-radar-v2"),
                ),
            ],
        ),

        html.Div(
            className="card",
            children=dcc.Graph(id="stress-staff-v2"),
        ),
    ],
)

# ============================================================
# INSTITUTION FILTER CALLBACK
# ============================================================

@callback(
    Output("stress-institution-filter-v2", "options"),
    Output("stress-institution-filter-v2", "value"),
    Input("stress-region-filter-v2", "value"),
)
def update_stress_institution_filter(region):

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
# UPDATE GRAPHS
# ============================================================

@callback(
    Output("stress-ts-v2", "figure"),
    Output("stress-scatter-v2", "figure"),
    Output("stress-radar-v2", "figure"),
    Output("stress-staff-v2", "figure"),
    Input("stress-region-filter-v2", "value"),
    Input("stress-institution-filter-v2", "value"),
)
def update_stress_graphs(
    selected_region,
    selected_institution,
):

    dff = df.copy()

    if selected_region != "all":
        dff = dff[dff["regiao"] == selected_region]

    if selected_institution != "all":
        dff = dff[dff["instituicao"] == selected_institution]

    # ========================================================
    # STRESS TEMPORAL
    # ========================================================

    stress_ts = (
        dff.groupby("tempo")["stress_index"]
        .mean()
        .reset_index()
    )

    stress_ts["rolling_6m"] = (
        stress_ts["stress_index"]
        .rolling(6)
        .mean()
    )

    benchmark = stress_ts["stress_index"].mean()

    fig_ts = go.Figure()

    fig_ts.add_trace(go.Scatter(
        x=stress_ts["tempo"],
        y=stress_ts["stress_index"],
        name="Stress",
    ))

    fig_ts.add_trace(go.Scatter(
        x=stress_ts["tempo"],
        y=stress_ts["rolling_6m"],
        name="Tendência (6m)",
        line=dict(width=3),
    ))

    if not np.isnan(benchmark):
        fig_ts.add_hline(
            y=benchmark,
            line_dash="dash",
            annotation_text="Média histórica",
        )

    fig_ts.update_layout(
        title="Evolução do Índice de Stress",
        height=360,
    )

    # ========================================================
    # SCATTER
    # ========================================================

    scatter_df = (
        dff.groupby(["instituicao", "regiao"])[
            ["total_staff", "total_urgencias"]
        ]
        .sum()
        .reset_index()
    )

    fig_scatter = px.scatter(
        scatter_df,
        x="total_staff",
        y="total_urgencias",
        color="regiao",
        hover_name="instituicao",
        title="Staff vs Urgências",
    )

    # ========================================================
    # RADAR
    # ========================================================

    radar_df = (
        dff.groupby("regiao")[
            [
                "total_urgencias",
                "medicos_internos",
                "enfermeiros",
            ]
        ]
        .sum()
        .reindex(REGIOES)
        .fillna(0)
        .reset_index()
    )

    fig_radar = px.line_polar(
        radar_df,
        r="total_urgencias",
        theta="regiao",
        line_close=True,
        title="Pressão por Região",
    )

    # ========================================================
    # STAFF TEMPORAL
    # ========================================================

    staff_ts = (
        dff.groupby("tempo")[
            [
                "medicos_internos",
                "enfermeiros",
            ]
        ]
        .sum()
        .reset_index()
    )

    fig_staff = px.line(
        staff_ts,
        x="tempo",
        y=[
            "medicos_internos",
            "enfermeiros",
        ],
        title="Evolução de Profissionais",
    )

    return (
        fig_ts,
        fig_scatter,
        fig_radar,
        fig_staff,
    )