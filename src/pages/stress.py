import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from dash import html, dcc

# ============================================================
# DATA LOAD & PREP
# ============================================================
df = pd.read_csv("data/processed/master_dataset.csv")

df["regiao"] = df["regiao"].astype(str).str.strip()
df["instituicao"] = df["instituicao"].astype(str).str.strip()

df["tempo"] = pd.to_datetime(
    dict(year=df["ano"].astype(int), month=df["mes"].astype(int), day=1)
)

df["total_staff"] = df["medicos_internos"] + df["enfermeiros"]
df["stress_index"] = (df["total_urgencias"] / df["total_staff"].replace(0, np.nan)) * 10

# ============================================================
# STRESS TEMPORAL
# ============================================================
stress_ts = (
    df.groupby("tempo")["stress_index"]
    .mean()
    .reset_index()
)

stress_ts["rolling_6m"] = stress_ts["stress_index"].rolling(6).mean()
benchmark = stress_ts["stress_index"].mean()

fig_ts = go.Figure()
fig_ts.add_trace(go.Scatter(
    x=stress_ts["tempo"],
    y=stress_ts["stress_index"],
    name="Stress"
))
fig_ts.add_trace(go.Scatter(
    x=stress_ts["tempo"],
    y=stress_ts["rolling_6m"],
    name="Tendência (6m)",
    line=dict(width=3)
))
fig_ts.add_hline(
    y=benchmark,
    line_dash="dash",
    annotation_text="Média histórica"
)

fig_ts.update_layout(
    title="Evolução do Índice de Stress",
    height=360
)

# ============================================================
# SUPPORTING CHARTS 
# ============================================================
scatter_df = (
    df.groupby(["instituicao", "regiao"])[
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
    df.groupby("regiao")[
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
    df.groupby("tempo")[["medicos_internos", "enfermeiros"]]
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
# LAYOUT
# ============================================================
layout = html.Div(
    className="content",
    children=[
        html.H2("Stress Hospitalar"),
        html.P("Relação entre profissionais e atividade assistencial"),

        html.Div(className="card", children=dcc.Graph(figure=fig_ts)),

        html.Div(
            className="grid-2x2",
            children=[
                html.Div(className="card", children=dcc.Graph(figure=fig_scatter)),
                html.Div(className="card", children=dcc.Graph(figure=fig_radar)),
            ],
        ),

        html.Div(className="card", children=dcc.Graph(figure=fig_staff)),
    ],
)