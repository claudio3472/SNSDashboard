import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from dash import html, dcc, callback, Input, Output
from pages.pages_helper import load_data, process_data, create_sparkline, kpi_card

# ============================================================
# LOAD & PROCESS DATA
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATA_PATH = os.path.join(BASE_DIR, "..", "data", "processed", "medicamento_hospitalar.csv")
df = process_data(load_data(DEFAULT_DATA_PATH))

df["tempo"] = pd.to_datetime(
            df["ano"].astype(str) + "-" + df["mes"].astype(str).str.zfill(2) + "-01"
        )
df["mes"] = df["tempo"].dt.month

REGIOES = ["Norte", "Centro", "Lisboa e Vale do Tejo", "Alentejo", "Algarve"]
ANOS = sorted(df["ano"].astype(int).unique().tolist())
REGION_OPTIONS = [{"label": "Todas as regiões", "value": "all"}] + [
    {"label": r, "value": r} for r in REGIOES
]
MESES_PT = {1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun",
            7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}
df["mes_nome"] = df["mes"].map(MESES_PT)


# ============================================================
# LAYOUT
# ============================================================

layout = html.Div(
    className="content",
    children=[
        html.H2("Medicamentos Hospitalares"),
        html.P("Encargos SNS com medicamentos."),

        html.Div(
            className="filter-row",
            style={"display": "flex", "gap": "1rem", "flexWrap": "wrap", "alignItems": "center", "marginBottom": "1rem"},
            children=[
                dcc.Dropdown(
                    id="med-region-filter",
                    options=REGION_OPTIONS,
                    value=["all"],
                    multi=True,
                    clearable=True,
                    placeholder="Selecionar região(ões)",
                    style={"minWidth": "300px"},
                ),
            ],
        ),

        dcc.Store(id="store-range-med"),

        html.Div(id="med-kpis", className="kpi-row"),

        html.Div(
            className="card",
            style={"marginBottom": "20px"},
            children=[dcc.Graph(id="med-stream")],
        ),

        html.Div(
            className="grid-2x2",
            children=[
                html.Div(className="card", children=[dcc.Graph(id="med-violin")]),
                html.Div(className="card", children=[dcc.Graph(id="med-polar")]),
            ],
        ),
    ],
)


# ============================================================
# CHART BUILDERS
# ============================================================

def build_kpis_med(dff: pd.DataFrame) -> list:
    if dff.empty:
        return [kpi_card("Sem dados", "—")] * 3

    # Total do período ─────────────────────────────────────────────────────
    total = dff["encargos_sns_hospitalar"].sum() / 1e6

    # Tendência: primeiro mês completo vs último mês completo ──────────────
    mensais = (
        dff.groupby(["ano", "mes"])["encargos_sns_hospitalar"]
        .sum()
        .sort_index()
    )
    if len(mensais) >= 2:
        variacao = (mensais.iloc[-1] - mensais.iloc[0]) / mensais.iloc[0] * 100
        sinal = "▲" if variacao >= 0 else "▼"
        tendencia = f"{sinal} {abs(variacao):.1f}".replace(".", ",") + "% no período"
    else:
        tendencia = "Dados insuficientes"

    # Mês de pico: mês + ano + valor ───────────────────────────────────────
    idx_pico = dff.groupby(["ano", "mes"])["encargos_sns_hospitalar"].sum().idxmax()
    valor_pico = dff.groupby(["ano", "mes"])["encargos_sns_hospitalar"].sum().max() / 1e6
    pico_label = f"{MESES_PT[idx_pico[1]]} {idx_pico[0]} · {valor_pico:.0f} M€"

    return [
        kpi_card("Total do Período",  f"{total:,.0f}".replace(",", " ") + " M€"),
        kpi_card("Tendência",         tendencia),
        kpi_card("Mês de Pico",       pico_label),
    ]


def build_fig_stream(dff_base: pd.DataFrame, range_data: dict) -> go.Figure:
    """Area chart empilhada (streamgraph) — evolução dos encargos por região."""
    stream_df = (
        dff_base
        .groupby(["tempo", "regiao"])["encargos_sns_hospitalar"]
        .sum()
        .reset_index()
    )
    stream_df["encargos_sns_hospitalar"] /= 1e6
    stream_df["encargos_formatado"] = stream_df["encargos_sns_hospitalar"].apply(lambda x: f"{x:.1f}".replace(".", ","))

    ordem_regioes = (
        stream_df.groupby("regiao")["encargos_sns_hospitalar"].sum().sort_values(ascending=False).index.tolist()
    )

    fig = px.area(
        stream_df,
        x="tempo",
        y="encargos_sns_hospitalar",
        color="regiao",
        line_shape="spline",
        labels={"encargos_sns_hospitalar": "Encargos (M€)", "tempo": ""},
        category_orders={"regiao": ordem_regioes},
        custom_data=["encargos_formatado"],
    )
    fig.update_traces(
        hovertemplate="<b>%{fullData.name}</b><br>%{x|%b %Y}<br>%{customdata[0]} M€<extra></extra>",
    )

    xaxis_kwargs = dict(rangeslider=dict(visible=True), type="date")
    if range_data and "start" in range_data:
        xaxis_kwargs["range"] = [range_data["start"], range_data["end"]]

    fig.update_layout(
        title={
            "text": "Evolução de Encargos por Região",
            "x": 0.5, "xanchor": "center",
            "y": 0.97, "yanchor": "top"
        },
        legend=dict(title="Região"),
        height=400,
        margin=dict(l=40, r=20, t=50, b=40),
        xaxis=xaxis_kwargs,
        yaxis_title="Encargos (M€)",
        uirevision="med-stream",
    )
    return fig


def build_fig_violin(dff: pd.DataFrame) -> go.Figure:
    violin_df = dff.copy()
    violin_df["encargos_sns_hospitalar"] /= 1e6
    violin_df['encargos_formatado'] = violin_df['encargos_sns_hospitalar'].apply(lambda x: f"{x:.1f}".replace(".", ","))

    ordem = (
        violin_df.groupby("regiao")["encargos_sns_hospitalar"]
        .median()
        .sort_values(ascending=False)
        .index.tolist()
    )

    fig = px.violin(
        violin_df,
        x="regiao",
        y="encargos_sns_hospitalar",
        color="regiao",
        box=True,
        points="outliers",
        category_orders={"regiao": ordem},
        title="",
        labels={"encargos_sns_hospitalar": "Encargos (M€)", "regiao": "Região"},
        custom_data=['encargos_formatado'],
    )
    fig.update_traces(
        hovertemplate="<b>%{fullData.name}</b><br>%{customdata[0]} M€<extra></extra>",
        width=0.8
    )
    fig.update_layout(
        title={
            "text": "Distribuição e Volatilidade Mensal de Encargos",
            "x": 0.5, "xanchor": "center",
            "y": 0.97, "yanchor": "top"
        },
        height=400,
        yaxis_title="Encargos (M€)",
        xaxis_title="",
        showlegend=False,
        margin=dict(l=40, r=20, t=50, b=60),
        xaxis=dict(tickangle=-20),
    )
    return fig


def build_fig_polar(dff: pd.DataFrame) -> go.Figure:
    polar_df = (
        dff
        .groupby(["ano", "mes", "mes_nome"])["encargos_sns_hospitalar"]
        .sum()
        .reset_index()
    )

    meses_por_ano = polar_df.groupby("ano")["mes"].nunique()
    anos_completos = meses_por_ano[meses_por_ano == 12].index
    polar_df = polar_df[polar_df["ano"].isin(anos_completos)]

    polar_df["encargos_sns_hospitalar"] /= 1e6
    polar_df = polar_df.sort_values(["ano", "mes"])
    polar_df["ano"] = polar_df["ano"].astype(str)
    polar_df['encargos_formatado'] = polar_df['encargos_sns_hospitalar'].apply(lambda x: f"{x:.1f}".replace(".", ","))

    fig = px.line_polar(
        polar_df,
        r="encargos_sns_hospitalar",
        theta="mes_nome",
        color="ano",
        line_close=True,
        labels={"encargos_sns_hospitalar": "Encargos (M€)", "mes_nome": "Mês"},
        custom_data=["encargos_formatado"],
    )
    fig.update_traces(
        hovertemplate="<b>%{theta}</b><br>Encargos: %{customdata[0]} M€<extra></extra>",
    )
    fig.update_layout(
        title={
            "text": "Sazonalidade de Encargos por Ano<br><sup>Selecione pelo menos 1 ano completo no gráfico de evolução</sup>",
            "x": 0.5, "xanchor": "center",
            "y": 0.97, "yanchor": "top"
        },
        legend=dict(title="Ano"),
        polar=dict(
            radialaxis=dict(
                visible=True,
                showticklabels=True,
                ticks='inside',
                tickfont=dict(size=10),
                title=None,
            ),
            angularaxis=dict(direction="clockwise"),
        ),
        height=400,
    )
    fig.add_annotation(
        x=0.97,
        y=0.47,
        xref="paper",
        yref="paper",
        text="Encargos (M€)",
        showarrow=False,
        font=dict(size=11),
    )
    return fig


# ============================================================
# CALLBACKS
# ============================================================

@callback(
    Output("store-range-med", "data"),
    Input("med-stream", "relayoutData"),
)
def guardar_range(relayoutData):
    """Guarda o intervalo de zoom do streamgraph para filtrar os restantes gráficos."""
    if not relayoutData:
        return {}
    if "xaxis.range[0]" in relayoutData:
        return {"start": relayoutData["xaxis.range[0]"], "end": relayoutData["xaxis.range[1]"]}
    if "xaxis.range" in relayoutData:
        return {"start": relayoutData["xaxis.range"][0], "end": relayoutData["xaxis.range"][1]}
    if "xaxis.autorange" in relayoutData:
        return {}
    return {}


@callback(
    Output("med-kpis",   "children"),
    Output("med-stream", "figure"),
    Output("med-violin", "figure"),
    Output("med-polar",  "figure"),
    Input("store-range-med",   "data"),
    Input("med-region-filter", "value"),
)
def update_dashboard(range_data, selected_region):
    # Filtro de região ─────────────────────────────────────────────────────
    if not selected_region:
        selected_region = ["all"]
    if isinstance(selected_region, str):
        selected_region = [selected_region]

    dff_base = df.copy()
    if "all" not in selected_region:
        dff_base = dff_base[dff_base["regiao"].isin(selected_region)]

    # Filtro temporal (zoom do streamgraph → violin e polar) ───────────────
    dff = dff_base.copy()
    if range_data and "start" in range_data:
        start = pd.to_datetime(range_data["start"])
        end   = pd.to_datetime(range_data["end"])
        dff = dff[(dff["tempo"] >= start) & (dff["tempo"] <= end)]

    return (
        build_kpis_med(dff),
        build_fig_stream(dff_base, range_data),
        build_fig_violin(dff),
        build_fig_polar(dff),
    )