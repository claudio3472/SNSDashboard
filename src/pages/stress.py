import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from dash import html, dcc

# ============================================================
# DATA LOAD
# ============================================================
df = pd.read_csv("data/processed/master_dataset.csv")

# ============================================================
# CLEAN DATA
# ============================================================
df["regiao"] = df["regiao"].astype(str).str.strip()
df["instituicao"] = df["instituicao"].astype(str).str.strip()

numeric_cols = [
    "ano",
    "mes",
    "medicos_internos",
    "enfermeiros",
    "total_urgencias",
]

for c in numeric_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df = df.dropna(subset=["ano", "mes", "regiao", "instituicao"])

df["tempo"] = pd.to_datetime(
    dict(
        year=df["ano"].astype(int),
        month=df["mes"].astype(int),
        day=1,
    )
)

df["total_staff"] = (
    df["medicos_internos"].fillna(0)
    + df["enfermeiros"].fillna(0)
)

df["stress_index"] = (
    df["total_urgencias"]
    / df["total_staff"].replace(0, np.nan)
) * 10

# ============================================================
# FILTER OPTIONS
# ============================================================
ALL_YEARS = sorted(df["ano"].dropna().astype(int).unique())
ALL_REGIONS = sorted(df["regiao"].unique())
ALL_INSTS = sorted(df["instituicao"].unique())

# ============================================================
# FILTERS (STATIC FOR NOW — NO CALLBACKS IN THIS ARCHITECTURE)
# ============================================================
def filters_block():
    return html.Div(
        className="filter-bar",
        children=[

            dcc.Dropdown(
                id="stress-year",
                options=[{"label": "All Years", "value": "ALL"}]
                + [{"label": str(y), "value": int(y)} for y in ALL_YEARS],
                value="ALL",
                multi=True,
            ),

            dcc.Dropdown(
                id="stress-region",
                options=[{"label": "All Regions", "value": "ALL"}]
                + [{"label": r, "value": r} for r in ALL_REGIONS],
                value="ALL",
                multi=True,
            ),

            dcc.Dropdown(
                id="stress-inst",
                options=[{"label": "All Institutions", "value": "ALL"}]
                + [{"label": i, "value": i} for i in ALL_INSTS],
                value="ALL",
                multi=True,
            ),
        ],
    )

# ============================================================
# APPLY FILTERS (LOCAL ONLY — NO DASH CALLBACK)
# ============================================================
def apply_filters(years, regions, insts):
    dff = df.copy()

    if years and "ALL" not in years:
        dff = dff[dff["ano"].isin(years)]

    if regions and "ALL" not in regions:
        dff = dff[dff["regiao"].isin(regions)]

    if insts and "ALL" not in insts:
        dff = dff[dff["instituicao"].isin(insts)]

    return dff

# ============================================================
# DEFAULT DATA (NO CALLBACK ARCHITECTURE)
# ============================================================
dff = df.copy()

# ============================================================
# CHARTS
# ============================================================

stress_ts = (
    dff.groupby("tempo")["stress_index"]
    .mean()
    .reset_index()
)

fig_ts = px.area(
    stress_ts,
    x="tempo",
    y="stress_index",
    title="Evolução do Índice de Stress",
)

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
    title="Staff vs Urgências",
)

radar_df = (
    dff.groupby("regiao")[
        ["total_urgencias", "medicos_internos", "enfermeiros"]
    ]
    .sum()
    .reset_index()
)

fig_radar = px.line_polar(
    radar_df,
    r="total_urgencias",
    theta="regiao",
    line_close=True,
    title="Pressão por Região",
)

staff_ts = (
    dff.groupby("tempo")[
        ["medicos_internos", "enfermeiros"]
    ]
    .sum()
    .reset_index()
)

fig_staff = px.line(
    staff_ts,
    x="tempo",
    y=["medicos_internos", "enfermeiros"],
    title="Evolução de Profissionais",
)

# ============================================================
# FINAL LAYOUT
# ============================================================
layout = html.Div(
    className="content",
    children=[

        html.H2("Stress Hospitalar"),
        html.P("Relação entre profissionais e atividade assistencial"),

        filters_block(),

        html.Div(
            className="card",
            children=dcc.Graph(figure=fig_ts),
        ),

        html.Div(
            className="grid-2x2",
            children=[
                html.Div(
                    className="card",
                    children=dcc.Graph(figure=fig_scatter),
                ),
                html.Div(
                    className="card",
                    children=dcc.Graph(figure=fig_radar),
                ),
            ],
        ),

        html.Div(
            className="card",
            children=dcc.Graph(figure=fig_staff),
        ),
    ],
)