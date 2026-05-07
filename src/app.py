import pandas as pd
import numpy as np

from dash import Dash, html, dcc
import plotly.graph_objects as go
import plotly.express as px

# ============================================================
# 1. LOAD DATA
# ============================================================
df = pd.read_csv("data/processed/master_dataset.csv")

# último ano disponível
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
# 2. KPIs
# ============================================================
kpi_urgencias = int(df_year["total_urgencias"].sum())

kpi_consultas = int(df_year["no_de_consultas_medicas_total"].sum())

kpi_divida = (
    df_year["divida_total_fornecedores_externos"].sum() / 1e6
)

kpi_instituicoes = df["instituicao"].nunique()

# ============================================================
# 3. GASTOS vs RENDIMENTOS (BAR)
# ============================================================
finance = (
    df_year
    .groupby("regiao")[[
        "gastos_operacionais",
        "rendimentos_operacionais"
    ]]
    .sum()
    .reindex(REGIOES)
    / 1e6
)

fig_gastos = go.Figure()

fig_gastos.add_bar(
    x=finance.index,
    y=finance["gastos_operacionais"],
    name="Gastos",
    marker_color="#ef4444"
)

fig_gastos.add_bar(
    x=finance.index,
    y=finance["rendimentos_operacionais"],
    name="Rendimentos",
    marker_color="#0f172a"
)

fig_gastos.update_layout(
    barmode="group",
    title="Gastos vs Rendimentos por Região (M€)",
    height=360,
    margin=dict(l=40, r=20, t=50, b=40),
)

# ============================================================
# 4. ENCARGOS MEDICAMENTOS (PIE) → aproximação via gastos
# ============================================================
fig_medicamentos = px.pie(
    finance.reset_index(),
    names="regiao",
    values="gastos_operacionais",
    title="Encargos com Medicamentos / Custos Operacionais",
    hole=0.35,
)

# ============================================================
# 5. PROFISSIONAIS POR REGIÃO (STACKED BAR)
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
    marker_color="#2563eb",
)

fig_prof.add_bar(
    y=prof.index,
    x=prof["enfermeiros"],
    name="Enfermeiros",
    orientation="h",
    marker_color="#16a34a",
)

fig_prof.update_layout(
    barmode="stack",
    title="Profissionais por Região",
    height=360,
    margin=dict(l=60, r=20, t=50, b=40),
)

# ============================================================
# 6. RADAR — ATIVIDADE POR REGIÃO
# ============================================================
# Cirurgias totais = soma dos vários tipos
df_year["total_cirurgias"] = (
    df_year[
        [
            "no_intervencoes_cirurgicas_programadas",
            "no_intervencoes_cirurgicas_convencionais",
            "no_intervencoes_cirurgicas_urgentes",
        ]
    ]
    .sum(axis=1)
)

radar_df = (
    df_year
    .groupby("regiao")[
        [
            "total_urgencias",
            "total_cirurgias",
            "no_de_consultas_medicas_total",
        ]
    ]
    .sum()
    .reindex(REGIOES)
)

radar_df.columns = [
    "Urgências",
    "Cirurgias",
    "Consultas",
]

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
    polar=dict(radialaxis=dict(visible=True)),
    title="Atividade Assistencial por Região",
    height=360,
)

# ============================================================
# 7. APP LAYOUT
# ============================================================
app = Dash(__name__)

def kpi_card(title, value):
    return html.Div(
        className="kpi-card",
        children=[
            html.Div(title, className="kpi-title"),
            html.Div(value, className="kpi-value"),
        ],
    )



app.layout = html.Div(
    className="app-container",
    children=[

        html.Div(
            className="content",
            children=[
                html.H2("Dashboard Geral"),
                html.P(f"Dados referentes a {year}"),

                # ---------- KPIs ----------
                html.Div(
                    className="kpi-row",
                    children=[
                        kpi_card("Urgências Totais", f"{kpi_urgencias:,.0f}".replace(",", " ")),
                        kpi_card("Consultas Médicas", f"{kpi_consultas:,.0f}".replace(",", " ")),
                        kpi_card("Dívida Total (M€)", f"{kpi_divida:,.1f}"),
                        kpi_card("Instituições", kpi_instituicoes),
                    ],
                ),

                # ---------- GRELHA DE GRÁFICOS (2 POR LINHA) ----------
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
    ]
)



# ============================================================
# 8. RUN
# ============================================================
if __name__ == "__main__":
    app.run(debug=True)