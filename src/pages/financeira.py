from dash import html, dcc, callback, Input, Output
from pages.pages_helper import load_data, process_data, create_sparkline, kpi_card

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


df = process_data(load_data())

df["ano"] = df["ano"].astype(int)
df["mes"] = df["mes"].astype(int)
df["tempo"] = pd.to_datetime(dict(year=df["ano"], month=df["mes"], day=1))

REGIOES = ["Norte", "Centro", "Lisboa e Vale do Tejo", "Alentejo", "Algarve"]

COLORBLIND = [
    "#0072B2",
    "#E69F00",
    "#009E73",
    "#D55E00",
    "#CC79A7",
    "#56B4E9",
]

REGION_OPTIONS = [{"label": "Todas as regiões", "value": "all"}] + [
    {"label": r, "value": r} for r in REGIOES
]

for col in [
    "gastos_operacionais",
    "rendimentos_operacionais",
    "divida_total_fornecedores_externos",
    "total_urgencias",
]:
    if col not in df.columns:
        df[col] = 0
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

if "tipo_instituicao" not in df.columns:
    df["tipo_instituicao"] = "Instituição"

CUMULATIVE_COLS = [
    "gastos_operacionais",
    "rendimentos_operacionais",
]

df = df.sort_values(["instituicao", "ano", "mes"]).copy()

for col in CUMULATIVE_COLS:
    original = df[col].copy()

    df[col] = (
        df.groupby(["instituicao", "ano"])[col]
        .diff()
        .fillna(original)
    )

    df[col] = df[col].clip(lower=0)

def empty_fig(title):
    fig = go.Figure()
    fig.update_layout(
        title=dict(text=title, x=0.03),
        height=380,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text="Sem dados para os filtros selecionados",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
            )
        ],
        margin=dict(l=30, r=30, t=80, b=40),
    )
    return fig


def base_layout(fig, title, height=380):
    fig.update_layout(
        title=dict(text=title, x=0.03),
        height=height,
        margin=dict(l=30, r=30, t=90, b=40),
        plot_bgcolor="white",
    )
    return fig


def apply_filters(region, institution):
    dff = df.copy()

    if region != "all":
        dff = dff[dff["regiao"] == region]

    if institution != "all":
        dff = dff[dff["instituicao"] == institution]

    return dff


def apply_range(dff, range_data):
    if range_data and "start" in range_data:
        start = pd.to_datetime(range_data["start"])
        end = pd.to_datetime(range_data["end"])
        dff = dff[(dff["tempo"] >= start) & (dff["tempo"] <= end)]

    return dff


layout = html.Div(
    className="content",
    children=[
        html.H2("Evolução Financeira"),
        html.P("Análise financeira do SNS"),

        html.Div(
            className="filter-row",
            style={
                "display": "flex",
                "gap": "1rem",
                "flexWrap": "wrap",
                "alignItems": "center",
            },
            children=[
                dcc.Dropdown(
                    id="finance-region-filter-v2",
                    options=REGION_OPTIONS,
                    value="all",
                    clearable=False,
                    placeholder="Selecionar região",
                    style={"minWidth": "260px"},
                ),

                dcc.Dropdown(
                    id="finance-institution-filter-v2",
                    value="all",
                    clearable=False,
                    placeholder="Selecionar instituição",
                    style={"minWidth": "260px"},
                ),
            ],
        ),

        dcc.Store(id="store-range-finance-v2"),

        html.Div(id="finance-kpis-v2", className="kpi-row"),

        html.Div(
            className="card",
            style={"marginBottom": "20px"},
            children=[
                dcc.Graph(
                    id="finance-graph-v2",
                    config={"displayModeBar": False},
                )
            ],
        ),

        html.Div(
            className="grid-2x2",
            children=[
                html.Div(
                    className="card",
                    children=[dcc.Graph(id="finance-waterfall-v2", config={"displayModeBar": False})],
                ),
                html.Div(
                    className="card",
                    children=[dcc.Graph(id="finance-comparison-v2", config={"displayModeBar": False})],
                ),
                html.Div(
                    className="card",
                    children=[dcc.Graph(id="finance-risk-v2", config={"displayModeBar": False})],
                ),
                html.Div(
                    className="card",
                    children=[dcc.Graph(id="finance-structure-v2", config={"displayModeBar": False})],
                ),
            ],
        ),
    ],
)


@callback(
    Output("finance-institution-filter-v2", "options"),
    Output("finance-institution-filter-v2", "value"),
    Input("finance-region-filter-v2", "value"),
)
def update_inst_filter(region):
    dff = df.copy()

    if region != "all":
        dff = dff[dff["regiao"] == region]

    return (
        [{"label": "Todas as instituições", "value": "all"}]
        + [{"label": i, "value": i} for i in sorted(dff["instituicao"].dropna().unique())],
        "all",
    )


@callback(
    Output("store-range-finance-v2", "data"),
    Input("finance-graph-v2", "relayoutData"),
)
def save_range(relayout):
    if not relayout:
        return {}

    if "xaxis.range[0]" in relayout:
        return {
            "start": relayout["xaxis.range[0]"],
            "end": relayout["xaxis.range[1]"],
        }

    if "xaxis.range" in relayout:
        return {
            "start": relayout["xaxis.range"][0],
            "end": relayout["xaxis.range"][1],
        }

    if "xaxis.autorange" in relayout:
        return {}

    return {}


@callback(
    Output("finance-kpis-v2", "children"),
    Output("finance-graph-v2", "figure"),
    Output("finance-waterfall-v2", "figure"),
    Output("finance-comparison-v2", "figure"),
    Output("finance-risk-v2", "figure"),
    Output("finance-structure-v2", "figure"),
    Input("store-range-finance-v2", "data"),
    Input("finance-region-filter-v2", "value"),
    Input("finance-institution-filter-v2", "value"),
)
def update_finance(range_data, region, institution):
    base = apply_filters(region, institution)
    dff = apply_range(base, range_data)

    if dff.empty:
        return (
            [
                kpi_card("Total Gastos", "0.0 M€"),
                kpi_card("Total Rendimentos", "0.0 M€"),
                kpi_card("Balanço", "0.0 M€"),
                kpi_card("Dívida", "0.0 M€"),
            ],
            empty_fig("Evolução Financeira"),
            empty_fig("Cascata Financeira"),
            empty_fig("Comparação Financeira"),
            empty_fig("Risco Financeiro"),
            empty_fig("Estrutura Financeira"),
        )

    # ========================================================
    # KPIS
    # ========================================================

    total_gastos = dff["gastos_operacionais"].sum() / 1e6
    total_rend = dff["rendimentos_operacionais"].sum() / 1e6
    total_divida = dff["divida_total_fornecedores_externos"].sum() / 1e6
    saldo = total_rend - total_gastos
    cor_saldo = "#009E73" if saldo >= 0 else "#D55E00"

    spark = (
        dff.groupby("tempo")
        .agg(
            gastos=("gastos_operacionais", "sum"),
            rendimentos=("rendimentos_operacionais", "sum"),
            divida=("divida_total_fornecedores_externos", "sum"),
        )
        .reset_index()
        .sort_values("tempo")
    )

    spark["saldo"] = spark["rendimentos"] - spark["gastos"]

    kpis = [
        kpi_card(
            "Total Gastos",
            f"{total_gastos:,.1f} M€",
            dcc.Graph(
                figure=create_sparkline(spark["tempo"], spark["gastos"], "#D55E00"),
                config={"displayModeBar": False, "staticPlot": True},
            ),
        ),
        kpi_card(
            "Total Rendimentos",
            f"{total_rend:,.1f} M€",
            dcc.Graph(
                figure=create_sparkline(spark["tempo"], spark["rendimentos"], "#009E73"),
                config={"displayModeBar": False, "staticPlot": True},
            ),
        ),
        html.Div(
            className="kpi-card",
            children=[
                html.Div("Balanço", className="kpi-title"),
                html.Div(
                    f"{saldo:,.1f} M€",
                    className="kpi-value",
                    style={"color": cor_saldo},
                ),
                dcc.Graph(
                    figure=create_sparkline(spark["tempo"], spark["saldo"], cor_saldo),
                    config={"displayModeBar": False, "staticPlot": True},
                ),
            ],
        ),
        kpi_card(
            "Dívida / Instituições",
            f"{total_divida:,.1f} M€",
            html.Div(
                f"{dff['instituicao'].nunique()} instituições | {dff['tempo'].nunique()} períodos",
                className="kpi-subtitle",
                style={"marginTop": "10px"},
            ),
        ),
    ]

    # ========================================================
    # MAIN TIMELINE
    # ========================================================

    ts = (
        base.groupby("tempo")
        .agg(
            gastos=("gastos_operacionais", "sum"),
            rendimentos=("rendimentos_operacionais", "sum"),
            divida=("divida_total_fornecedores_externos", "sum"),
        )
        .reset_index()
        .sort_values("tempo")
    )

    ts["gastos_m"] = ts["gastos"] / 1e6
    ts["rendimentos_m"] = ts["rendimentos"] / 1e6
    ts["saldo_m"] = ts["rendimentos_m"] - ts["gastos_m"]

    fig_main = go.Figure()

    fig_main.add_trace(
        go.Scatter(
            x=ts["tempo"],
            y=ts["rendimentos_m"],
            name="Rendimentos",
            mode="lines",
            line=dict(color="#009E73", width=2),
            fill="tozeroy",
            fillcolor="rgba(0,158,115,0.10)",
            hovertemplate="Data: %{x|%Y-%m}<br>Rendimentos: %{y:.1f} M€<extra></extra>",
        )
    )

    fig_main.add_trace(
        go.Scatter(
            x=ts["tempo"],
            y=ts["gastos_m"],
            name="Gastos",
            mode="lines",
            line=dict(color="#D55E00", width=2),
            hovertemplate="Data: %{x|%Y-%m}<br>Gastos: %{y:.1f} M€<extra></extra>",
        )
    )

    fig_main.add_trace(
        go.Scatter(
            x=ts["tempo"],
            y=ts["saldo_m"],
            name="Saldo",
            mode="lines",
            line=dict(color="#0072B2", width=3),
            hovertemplate="Data: %{x|%Y-%m}<br>Saldo: %{y:.1f} M€<extra></extra>",
        )
    )

    fig_main.update_layout(
        title=dict(
            text="Evolução Financeira<br><sup>Use o slider inferior para selecionar o período</sup>",
            x=0.03,
            y=0.97,
        ),

        height=460,

        uirevision="finance-temporal",

        xaxis=dict(
            rangeslider=dict(visible=True),
            type="date",
            title=None,
        ),

        yaxis=dict(
            title="M€"
        ),

        legend=dict(
            orientation="h",
            y=1.03,
            x=0,
            bgcolor="rgba(255,255,255,0)",
        ),

        margin=dict(
            l=40,
            r=30,
            t=125,
            b=40,
        ),

        plot_bgcolor="white",
    )
    # ========================================================
    # WATERFALL
    # ========================================================

    fig_waterfall = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "relative", "total"],
            x=["Rendimentos", "Gastos", "Dívida", "Saldo"],
            y=[total_rend, -total_gastos, -total_divida, saldo],
            text=[
                f"{total_rend:,.1f}",
                f"-{total_gastos:,.1f}",
                f"-{total_divida:,.1f}",
                f"{saldo:,.1f}",
            ],
            textposition="outside",
            connector={"line": {"color": "#6B7280"}},
            increasing={"marker": {"color": "#009E73"}},
            decreasing={"marker": {"color": "#D55E00"}},
            totals={"marker": {"color": "#0072B2"}},
            hovertemplate="%{x}<br>%{y:.1f} M€<extra></extra>",
        )
    )

    fig_waterfall = base_layout(
        fig_waterfall,
        "Cascata Financeira do Período",
    )

    fig_waterfall.update_layout(
        yaxis=dict(title="M€"),
        showlegend=False,
    )

    # ========================================================
    # COMPARISON
    # ========================================================

    if institution != "all":
        comp = (
            dff.groupby("tempo")
            .agg(
                gastos=("gastos_operacionais", "sum"),
                rendimentos=("rendimentos_operacionais", "sum"),
            )
            .reset_index()
            .sort_values("tempo")
        )

        comp["gastos_m"] = comp["gastos"] / 1e6
        comp["rendimentos_m"] = comp["rendimentos"] / 1e6
        comp["saldo_m"] = comp["rendimentos_m"] - comp["gastos_m"]

        fig_comp = go.Figure()

        fig_comp.add_bar(
            x=comp["tempo"],
            y=comp["rendimentos_m"],
            name="Rendimentos",
            marker_color="#009E73",
        )

        fig_comp.add_bar(
            x=comp["tempo"],
            y=comp["gastos_m"],
            name="Gastos",
            marker_color="#D55E00",
        )

        fig_comp.add_trace(
            go.Scatter(
                x=comp["tempo"],
                y=comp["saldo_m"],
                name="Saldo",
                mode="lines+markers",
                line=dict(color="#0072B2", width=3),
            )
        )

        fig_comp.update_layout(
            barmode="group",
            yaxis=dict(title="M€"),
            legend=dict(orientation="h", y=1.12),
        )

        fig_comp = base_layout(fig_comp, "Evolução Mensal da Instituição")

    else:
        group_col = "instituicao" if region != "all" else "regiao"
        label = "Instituição" if region != "all" else "Região"

        comp = (
            dff.groupby(group_col)
            .agg(
                gastos=("gastos_operacionais", "sum"),
                rendimentos=("rendimentos_operacionais", "sum"),
            )
            .reset_index()
        )

        comp["gastos_m"] = comp["gastos"] / 1e6
        comp["rendimentos_m"] = comp["rendimentos"] / 1e6

        if group_col == "instituicao":
            comp = comp.sort_values("gastos_m", ascending=False).head(12)

        comp = comp.sort_values("gastos_m")

        fig_comp = go.Figure()

        for _, row in comp.iterrows():
            fig_comp.add_trace(
                go.Scatter(
                    x=[row["gastos_m"], row["rendimentos_m"]],
                    y=[row[group_col], row[group_col]],
                    mode="lines",
                    line=dict(color="#bdc3c7", width=3),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

        fig_comp.add_trace(
            go.Scatter(
                x=comp["gastos_m"],
                y=comp[group_col],
                mode="markers",
                name="Gastos",
                marker=dict(
                    color="#D55E00",
                    size=12,
                    line=dict(color="white", width=1),
                ),
            )
        )

        fig_comp.add_trace(
            go.Scatter(
                x=comp["rendimentos_m"],
                y=comp[group_col],
                mode="markers",
                name="Rendimentos",
                marker=dict(
                    color="#009E73",
                    size=12,
                    line=dict(color="white", width=1),
                ),
            )
        )

        fig_comp.update_layout(
            xaxis=dict(title="M€"),
            yaxis=dict(title=None, automargin=True),
            legend=dict(orientation="h", y=1.12),
        )

        fig_comp = base_layout(
            fig_comp,
            f"Gastos vs Rendimentos por {label}",
            height=420,
        )

    # ========================================================
    # RISK
    # ========================================================

    group_col = "instituicao" if region != "all" else "regiao"

    risk = (
        dff.groupby(group_col)
        .agg(
            gastos=("gastos_operacionais", "sum"),
            divida=("divida_total_fornecedores_externos", "sum"),
            urgencias=("total_urgencias", "sum"),
        )
        .reset_index()
    )

    risk["gastos_m"] = risk["gastos"] / 1e6
    risk["divida_m"] = risk["divida"] / 1e6

    max_urg = risk["urgencias"].max()

    if max_urg > 0:
        risk["size"] = (risk["urgencias"] / max_urg * 40) + 8
    else:
        risk["size"] = 12

    fig_risk = go.Figure()

    fig_risk.add_trace(
        go.Scatter(
            x=risk["gastos_m"],
            y=risk["divida_m"],
            mode="markers",
            marker=dict(
                size=risk["size"],
                color="#0072B2" if region != "all" else "#CC79A7",
                opacity=0.75,
                line=dict(color="white", width=1),
            ),
            customdata=risk[[group_col, "urgencias"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Gastos: %{x:.1f} M€<br>"
                "Dívida: %{y:.1f} M€<br>"
                "Urgências: %{customdata[1]:,.0f}"
                "<extra></extra>"
            ),
        )
    )

    if not risk.empty:
        fig_risk.add_vline(
            x=risk["gastos_m"].mean(),
            line_dash="dash",
            line_color="#6B7280",
        )
        fig_risk.add_hline(
            y=risk["divida_m"].mean(),
            line_dash="dash",
            line_color="#6B7280",
        )

    fig_risk.update_layout(
        xaxis=dict(title="Gastos (M€)"),
        yaxis=dict(title="Dívida (M€)"),
    )

    fig_risk = base_layout(
        fig_risk,
        "Risco Financeiro",
    )

    # ========================================================
    # STRUCTURE
    # ========================================================

    struct = (
        dff.groupby(["regiao", "tipo_instituicao"])
        .agg(gastos=("gastos_operacionais", "sum"))
        .reset_index()
    )

    struct = struct[struct["gastos"] > 0]

    if struct.empty:
        fig_struct = empty_fig("Distribuição de Gastos Operacionais")
    else:
        fig_struct = px.sunburst(
            struct,
            path=["regiao", "tipo_instituicao"],
            values="gastos",
            color="regiao",
            color_discrete_sequence=COLORBLIND,
            title="Distribuição de Gastos Operacionais",
        )

        fig_struct.update_traces(
            textinfo="label+percent parent",
            insidetextorientation="radial",
            hovertemplate="<b>%{label}</b><br>Gastos: %{value:,.0f}€<extra></extra>",
        )

        fig_struct.update_layout(
            height=420,
            margin=dict(t=80, l=10, r=10, b=10),
            title=dict(x=0.5),
        )

    return (
        kpis,
        fig_main,
        fig_waterfall,
        fig_comp,
        fig_risk,
        fig_struct,
    )