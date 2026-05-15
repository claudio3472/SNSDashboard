
from dash import html, dcc, callback, Input, Output
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

df = pd.read_csv("data/processed/master_dataset.csv")

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

REGION_OPTIONS = [{"label": "Todas as regiões", "value": "all"}] + [
    {"label": r, "value": r}
    for r in REGIOES
]


def criar_sparkline(x_data, y_data, cor):
    fig = go.Figure(
        go.Scatter(
            x=x_data,
            y=y_data,
            mode="lines",
            line=dict(color=cor, width=2.5),
            hoverinfo="skip",
        )
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=5, b=5),
        height=40,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )

    return fig


def build_main_figure(dff):
    ts = (
        dff.groupby("ano")[
            [
                "gastos_operacionais",
                "rendimentos_operacionais",
            ]
        ]
        .sum()
        / 1e6
    ).reset_index()

    ts["rolling_gastos"] = ts["gastos_operacionais"].rolling(3).mean()
    ts["rolling_rendimentos"] = ts["rendimentos_operacionais"].rolling(3).mean()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=ts["ano"],
        y=ts["rendimentos_operacionais"],
        mode="lines",
        name="Rendimentos",
    ))

    fig.add_trace(go.Scatter(
        x=ts["ano"],
        y=ts["gastos_operacionais"],
        mode="lines",
        name="Gastos",
    ))

    fig.add_trace(go.Scatter(
        x=ts["ano"],
        y=ts["rolling_rendimentos"],
        mode="lines",
        name="MM Rendimentos",
        line=dict(width=3, dash="dot"),
    ))

    fig.add_trace(go.Scatter(
        x=ts["ano"],
        y=ts["rolling_gastos"],
        mode="lines",
        name="MM Gastos",
        line=dict(width=3, dash="dot"),
    ))

    fig.update_layout(
        title="Evolução Financeira (M€)",
        height=360,
        uirevision="constant",
        xaxis=dict(rangeslider=dict(visible=True)),
    )

    return fig


layout = html.Div(
    className="content",
    children=[
        html.H2("Evolução Financeira"),
        html.P("Análise financeira do SNS"),

        html.Div(
            className="filter-row",
            children=[
                dcc.Dropdown(
                    id="finance-region-filter-v2",
                    options=REGION_OPTIONS,
                    value="all",
                    clearable=False,
                    placeholder="Selecionar região",
                ),

                dcc.Dropdown(
                    id="finance-institution-filter-v2",
                    value="all",
                    clearable=False,
                    placeholder="Selecionar instituição",
                ),
            ],
        ),

        dcc.Store(id="store-range-finance-v2"),

        html.Div(
            id="finance-kpis-v2",
            className="kpi-row",
        ),

        html.Div(
            className="grid-2x2",
            children=[
                html.Div(className="card", children=[dcc.Graph(id="finance-graph-v2")]),
                html.Div(className="card", children=[dcc.Graph(id="finance-regiao-v2")]),
                html.Div(className="card", children=[dcc.Graph(id="finance-orcamento-v2")]),
                html.Div(className="card", children=[dcc.Graph(id="finance-divida-v2")]),
            ],
        ),
    ],
)


@callback(
    Output("finance-institution-filter-v2", "options"),
    Output("finance-institution-filter-v2", "value"),
    Input("finance-region-filter-v2", "value"),
)
def update_finance_institution_filter(region):
    dff = df.copy()

    if region != "all":
        dff = dff[dff["regiao"] == region]

    options = [{"label": "Todas as instituições", "value": "all"}] + [
        {"label": inst, "value": inst}
        for inst in sorted(dff["instituicao"].dropna().unique())
    ]

    return options, "all"


@callback(
    Output("store-range-finance-v2", "data"),
    Input("finance-graph-v2", "relayoutData"),
)
def guardar_range_finance(relayoutData):
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


@callback(
    Output("finance-kpis-v2", "children"),
    Output("finance-graph-v2", "figure"),
    Output("finance-regiao-v2", "figure"),
    Output("finance-orcamento-v2", "figure"),
    Output("finance-divida-v2", "figure"),
    Input("store-range-finance-v2", "data"),
    Input("finance-region-filter-v2", "value"),
    Input("finance-institution-filter-v2", "value"),
)
def update_finance_dashboard(
    range_data,
    selected_region,
    selected_institution,
):
    dff_base = df.copy()

    if selected_region != "all":
        dff_base = dff_base[dff_base["regiao"] == selected_region]

    if selected_institution != "all":
        dff_base = dff_base[dff_base["instituicao"] == selected_institution]

    dff = dff_base.copy()

    if range_data and "start" in range_data:
        start = float(range_data["start"])
        end = float(range_data["end"])

        dff = dff[
            (dff["ano"] >= start)
            & (dff["ano"] <= end)
        ]

    total_gastos = dff["gastos_operacionais"].sum() / 1e6
    total_rendimentos = dff["rendimentos_operacionais"].sum() / 1e6
    balanco = total_rendimentos - total_gastos
    regioes = dff["regiao"].nunique()

    saldo_series = dff["rendimentos_operacionais"] - dff["gastos_operacionais"]
    cor_saldo = "#27ae60" if balanco >= 0 else "#e74c3c"

    spark_gastos = criar_sparkline(
        dff["ano"],
        dff["gastos_operacionais"],
        "#e74c3c",
    )

    spark_rend = criar_sparkline(
        dff["ano"],
        dff["rendimentos_operacionais"],
        "#27ae60",
    )

    spark_saldo = criar_sparkline(
        dff["ano"],
        saldo_series,
        cor_saldo,
    )

    kpis = [
        html.Div(
            [
                html.Div("Total Gastos", className="kpi-title"),
                html.Div(f"{total_gastos:,.1f} M €", className="kpi-value"),
                dcc.Graph(
                    figure=spark_gastos,
                    config={"displayModeBar": False},
                ),
            ],
            className="kpi-card",
        ),

        html.Div(
            [
                html.Div("Total Rendimentos", className="kpi-title"),
                html.Div(f"{total_rendimentos:,.1f} M €", className="kpi-value"),
                dcc.Graph(
                    figure=spark_rend,
                    config={"displayModeBar": False},
                ),
            ],
            className="kpi-card",
        ),

        html.Div(
            [
                html.Div("Balanço", className="kpi-title"),
                html.Div(
                    f"{balanco:,.1f} M €",
                    className="kpi-value",
                    style={"color": cor_saldo},
                ),
                dcc.Graph(
                    figure=spark_saldo,
                    config={"displayModeBar": False},
                ),
            ],
            className="kpi-card",
        ),

        html.Div(
            [
                html.Div("Regiões", className="kpi-title"),
                html.Div(f"{regioes}", className="kpi-value"),
                html.Div(
                    "Regiões analisadas",
                    className="kpi-subtitle",
                    style={"marginTop": "10px"},
                ),
            ],
            className="kpi-card",
        ),
    ]

    fig_main = build_main_figure(dff_base)

    gastos_regiao = (
        dff.groupby("regiao")["gastos_operacionais"]
        .sum()
        .reindex(REGIOES)
        .fillna(0)
        / 1e6
    ).reset_index()

    fig_regiao = px.pie(
        gastos_regiao,
        names="regiao",
        values="gastos_operacionais",
        hole=0.4,
        title="Distribuição por Região",
    )

    orc = (
        dff.groupby("ano")[
            [
                "gastos_operacionais",
                "rendimentos_operacionais",
            ]
        ]
        .sum()
        / 1e6
    ).reset_index()

    fig_orc = go.Figure()

    fig_orc.add_trace(go.Bar(
        x=orc["ano"],
        y=orc["rendimentos_operacionais"],
        name="Rendimentos",
    ))

    fig_orc.add_trace(go.Bar(
        x=orc["ano"],
        y=orc["gastos_operacionais"],
        name="Gastos",
    ))

    fig_orc.update_layout(
        title="Orçamento vs Execução",
        barmode="group",
        height=360,
    )

    divida = (
        dff.groupby("regiao")["divida_total_fornecedores_externos"]
        .sum()
        .reindex(REGIOES)
        .fillna(0)
        / 1e6
    ).reset_index()

    fig_divida = px.pie(
        divida,
        names="regiao",
        values="divida_total_fornecedores_externos",
        hole=0.45,
        title="Dívida por Região",
    )

    return (
        kpis,
        fig_main,
        fig_regiao,
        fig_orc,
        fig_divida,
    )