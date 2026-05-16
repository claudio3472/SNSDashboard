import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from dash import (
    html,
    dcc,
    callback,
    Input,
    Output,
)

# ============================================================
# DATA
# ============================================================

df = pd.read_csv("data/processed/medicamento_hospitalar.csv")

df["tempo"] = pd.to_datetime(df["tempo"])
df["ano"] = df["ano"].astype(int)
df["regiao"] = df["regiao"].astype(str).str.strip()

# Para o gráfico Polar (Sazonalidade), precisamos do mês
df["mes"] = df["tempo"].dt.month
meses_pt = {1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}
df["mes_nome"] = df["mes"].map(meses_pt)

REGIOES = [
    "Norte",
    "Centro",
    "Lisboa e Vale do Tejo",
    "Alentejo",
    "Algarve",
]

REGION_OPTIONS = [{"label": "Todas as regiões", "value": "all"}] + [{"label": r, "value": r} for r in REGIOES]

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
        html.H2("Medicamentos Hospitalares"),
        html.P("Encargos SNS com medicamentos: Evolução, Ranking e Sazonalidade"),

        html.Div(
            className="filter-row",
            children=[
                dcc.Dropdown(
                    id="med-region-filter",
                    options=REGION_OPTIONS,
                    value=["all"],
                    multi=True,
                    clearable=True,
                    placeholder="Selecionar região(ões)",
                    style={"minWidth": "300px"}
                ),
            ],
        ),

        dcc.Store(id="store-range-med"),

        html.Div(
            id="med-kpis",
            className="kpi-row",
        ),

        # Streamgraph ganha destaque (Ocupa a largura toda)
        html.Div(
            className="card",
            style={"marginBottom": "20px"},
            children=[
                dcc.Graph(id="med-stream")
            ],
        ),

        # Grid 2x2 para o Violin Chart e o Polar Chart
        html.Div(
            className="grid-2x2",
            children=[
                html.Div(
                    className="card",
                    children=[dcc.Graph(id="med-violin")],
                ),
                html.Div(
                    className="card",
                    children=[dcc.Graph(id="med-polar")],
                ),
            ],
        ),
    ],
)

# ============================================================
# CALLBACK 1: GUARDA RANGE (Do Streamgraph)
# ============================================================

@callback(
    Output("store-range-med", "data"),
    Input("med-stream", "relayoutData"),
)
def guardar_range(relayoutData):
    if not relayoutData:
        return {}
    if "xaxis.range[0]" in relayoutData:
        return {"start": relayoutData["xaxis.range[0]"], "end": relayoutData["xaxis.range[1]"]}
    if "xaxis.range" in relayoutData:
        return {"start": relayoutData["xaxis.range"][0], "end": relayoutData["xaxis.range"][1]}
    if "xaxis.autorange" in relayoutData:
        return {}
    return {}

# ============================================================
# CALLBACK 2: UPDATE DASHBOARD
# ============================================================

@callback(
    Output("med-kpis", "children"),
    Output("med-stream", "figure"),
    Output("med-violin", "figure"),
    Output("med-polar", "figure"),
    Input("store-range-med", "data"),
    Input("med-region-filter", "value"),
)
def update_dashboard(range_data, selected_region):

    dff_base = df.copy()

    # Filtro de Região Multi-select
    if not selected_region:
        selected_region = ["all"]
    if isinstance(selected_region, str):
        selected_region = [selected_region]

    if "all" not in selected_region:
        dff_base = dff_base[dff_base["regiao"].isin(selected_region)]

    # DFF Filtrado no Tempo (Usado para KPIs, Bump e Polar)
    dff = dff_base.copy()
    if range_data and "start" in range_data:
        start = pd.to_datetime(range_data["start"])
        end = pd.to_datetime(range_data["end"])
        dff = dff[(dff["tempo"] >= start) & (dff["tempo"] <= end)]

    # ========================================================
    # KPIs
    # ========================================================
    total_encargos = dff["encargos_sns_hospitalar"].sum() / 1e6
    num_periodos = dff["tempo"].nunique()
    media_mensal = dff["encargos_sns_hospitalar"].mean() / 1e6 if not dff.empty else 0

    kpis = [
        kpi_card("Total Encargos", f"{total_encargos:,.1f} M €"),
        kpi_card("Períodos Analisados", f"{num_periodos}"),
        kpi_card("Média Mensal", f"{media_mensal:,.1f} M €"),
    ]

    # ========================================================
    # 1. STREAMGRAPH (Evolução Contínua) - Ocupa dff_base para manter o slider útil
    # ========================================================
    stream_df = dff_base.groupby(["tempo", "regiao"])["encargos_sns_hospitalar"].sum().reset_index()
    stream_df["encargos_sns_hospitalar"] /= 1e6

    # O formato Spline com Area é o que cria o aspeto fluido de um Streamgraph
    fig_stream = px.area(
        stream_df, 
        x="tempo", 
        y="encargos_sns_hospitalar", 
        color="regiao",
        line_shape="spline", 
        title="Volume de Encargos por Região (Streamgraph)"
    )
    xaxis_kwargs = dict(rangeslider=dict(visible=True), type="date")
    if range_data and "start" in range_data:
        xaxis_kwargs["range"] = [range_data["start"], range_data["end"]]

    fig_stream.update_layout(
        height=400,
        margin=dict(l=40, r=20, t=50, b=40),
        xaxis=xaxis_kwargs,
        uirevision="med-stream",
    )

    # ========================================================
    # 2. VIOLIN PLOT (Distribuição Mensal e Outliers)
    # ========================================================
    # Usamos o dff diretamente porque já tem os dados mensais detalhados
    violin_df = dff.copy()
    violin_df["encargos_sns_hospitalar"] /= 1e6

    fig_violin = px.violin(
        violin_df,
        x="regiao",
        y="encargos_sns_hospitalar",
        color="regiao",
        box=True, # Adiciona um mini box-plot no interior
        points="outliers", # Mostra apenas os meses que fugiram muito ao padrão
        title="Distribuição Mensal e Volatilidade de Encargos",
    )

    fig_violin.update_traces(width=0.8)
    fig_violin.update_layout(
        height=400,
        yaxis_title="M€",
        xaxis_title="Região",
        showlegend=False, # Oculta a legenda porque o eixo X já tem os nomes
        margin=dict(l=40, r=20, t=50, b=40),
    )

    # ========================================================
    # 3. POLAR LINE CHART (Sazonalidade Mensal)
    # ========================================================
    # Agrupar por ano e mês
    polar_df = dff.groupby(["ano", "mes", "mes_nome"])["encargos_sns_hospitalar"].sum().reset_index()
    polar_df["encargos_sns_hospitalar"] /= 1e6
    polar_df = polar_df.sort_values(by=["ano", "mes"]) # Garantir ordem cronológica (Jan -> Dez)
    
    # Converter ano para string para o Plotly usar cores discretas
    polar_df["ano"] = polar_df["ano"].astype(str)

    fig_polar = px.line_polar(
        polar_df, 
        r="encargos_sns_hospitalar", 
        theta="mes_nome", 
        color="ano",
        line_close=True, # Fecha a linha de Dezembro com Janeiro
        title="Sazonalidade de Encargos (Gráfico Polar)"
    )
    
    fig_polar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, showticklabels=True),
            angularaxis=dict(direction="clockwise")
        ),
        height=400,
    )

    return (kpis, fig_stream, fig_violin, fig_polar)