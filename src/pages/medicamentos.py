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

try:
    df = process_data(load_data(DEFAULT_DATA_PATH))
    df["tempo"] = pd.to_datetime(
                df["ano"].astype(str) + "-" + df["mes"].astype(str).str.zfill(2) + "-01"
            )
    df["mes"] = df["tempo"].dt.month
except Exception as e:
    print(f"❌ Erro ao carregar dados: {e}")
    df = pd.DataFrame()

if not df.empty:
    MIN_DATE = df["tempo"].min().date()
    MAX_DATE = df["tempo"].max().date()
    ANOS = sorted(df["ano"].astype(int).unique().tolist())
else:
    MIN_DATE = None
    MAX_DATE = None
    ANOS = []

REGIOES = ["Norte", "Centro", "Lisboa e Vale do Tejo", "Alentejo", "Algarve"]
REGION_OPTIONS = [{"label": "Todas as regiões", "value": "all"}] + [
    {"label": r, "value": r} for r in REGIOES
]
MESES_PT = {1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun",
            7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}

if not df.empty:
    df["mes_nome"] = df["mes"].map(MESES_PT)


# ============================================================
# HELPERS
# ============================================================

def filter_period(data, start_date, end_date):
    dff = data.copy()

    if not end_date:
        end_date = dff["tempo"].max()

    end_date = pd.to_datetime(end_date)

    if start_date:
        start_date = pd.to_datetime(start_date)
        dff = dff[dff["tempo"] >= start_date]

    dff = dff[dff["tempo"] <= end_date]

    return dff

def empty_figure(title):
    fig = go.Figure()
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "y": 0.97, "yanchor": "top"},
        height=400,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text="Sem dados para os filtros selecionados",
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                showarrow=False,
            )
        ],
    )
    return fig


# ============================================================
# LAYOUT
# ============================================================

layout = html.Div(
    className="content",
    children=[
        html.Div(
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "flex-start",
                "gap": "20px",
                "flexWrap": "wrap",
                "marginBottom": "25px",
            },
            children=[

                html.Div([
                    html.H2("Medicamentos Hospitalares", style={"marginBottom": "8px"}),
                    html.P("Encargos SNS com medicamentos.", style={"color": "#6b7280", "marginBottom": "0"}),
                ]),

                html.Div(
                    style={
                        "display": "flex",
                        "gap": "14px",
                        "alignItems": "flex-end",
                        "marginTop": "10px",
                        "flexWrap": "wrap",
                    },
                    children=[
                        html.Div([
                            html.Div(
                                "Região",
                                style={
                                    "fontSize": "12px",
                                    "fontWeight": "600",
                                    "marginBottom": "5px",
                                    "color": "#374151",
                                },
                            ),
                            dcc.Dropdown(
                                id="med-region-filter",
                                options=REGION_OPTIONS,
                                value=["all"],
                                multi=True,
                                clearable=True,
                                placeholder="Selecionar região(ões)",
                                style={"minWidth": "250px"},
                            ),
                        ]),
                        
                        html.Div([
                            html.Div(
                                "Data Inicial",
                                style={
                                    "fontSize": "12px",
                                    "fontWeight": "600",
                                    "marginBottom": "5px",
                                    "color": "#374151",
                                },
                            ),
                            dcc.DatePickerSingle(
                                id="med-start-date",
                                min_date_allowed=MIN_DATE,
                                max_date_allowed=MAX_DATE,
                                date=MIN_DATE,
                                display_format="YYYY-MM-DD",
                            ),
                        ]),

                        html.Div([
                            html.Div(
                                "Data Final",
                                style={
                                    "fontSize": "12px",
                                    "fontWeight": "600",
                                    "marginBottom": "5px",
                                    "color": "#374151",
                                },
                            ),
                            dcc.DatePickerSingle(
                                id="med-end-date",
                                min_date_allowed=MIN_DATE,
                                max_date_allowed=MAX_DATE,
                                date=None,
                                placeholder="Última disponível",
                                display_format="YYYY-MM-DD",
                            ),
                        ]),
                    ],
                ),
            ],
        ),

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
        return [kpi_card("Total do Período", "—"), kpi_card("Tendência", "—"), kpi_card("Mês de Pico", "—")]

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


def build_fig_stream(dff: pd.DataFrame) -> go.Figure:
    if dff.empty: return empty_figure("Evolução de Encargos por Região")

    stream_df = (
        dff
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

    fig.update_layout(
        title={
            "text": "Evolução de Encargos por Região",
            "x": 0.5, "xanchor": "center",
            "y": 0.97, "yanchor": "top"
        },
        legend=dict(title="Região"),
        height=400,
        margin=dict(l=40, r=20, t=50, b=40),
        xaxis=dict(type="date"),
        yaxis_title="Encargos (M€)",
        uirevision="med-stream",
    )
    return fig


def build_fig_violin(dff: pd.DataFrame) -> go.Figure:
    if dff.empty: return empty_figure("Distribuição e Volatilidade Mensal de Encargos")

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
    if dff.empty: return empty_figure("Sazonalidade de Encargos por Ano")

    polar_df = (
        dff
        .groupby(["ano", "mes", "mes_nome"])["encargos_sns_hospitalar"]
        .sum()
        .reset_index()
    )

    meses_por_ano = polar_df.groupby("ano")["mes"].nunique()
    anos_completos = meses_por_ano[meses_por_ano == 12].index
    polar_df = polar_df[polar_df["ano"].isin(anos_completos)]

    if polar_df.empty: 
        return empty_figure("Sazonalidade de Encargos por Ano<br><sup>Selecione pelo menos 1 ano completo</sup>")

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
            "text": "Sazonalidade de Encargos por Ano<br><sup>Requer seleção de pelo menos 1 ano completo</sup>",
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
    Output("med-kpis",   "children"),
    Output("med-stream", "figure"),
    Output("med-violin", "figure"),
    Output("med-polar",  "figure"),
    Input("med-start-date", "date"),
    Input("med-end-date", "date"),
    Input("med-region-filter", "value"),
)
def update_dashboard(start_date, end_date, selected_region):
    # Aplica Filtro Temporal
    dff = filter_period(df, start_date, end_date)

    # Aplica Filtro de Região
    if not selected_region:
        selected_region = ["all"]
    if isinstance(selected_region, str):
        selected_region = [selected_region]

    if "all" not in selected_region:
        dff = dff[dff["regiao"].isin(selected_region)]

    return (
        build_kpis_med(dff),
        build_fig_stream(dff),
        build_fig_violin(dff),
        build_fig_polar(dff),
    )