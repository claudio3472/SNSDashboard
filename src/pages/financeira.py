from dash import html, dcc, callback, Input, Output
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# ============================================================
# DATA LOAD
# ============================================================

df = pd.read_csv("data/processed/master_dataset.csv")

df["ano"] = df["ano"].astype(int)
df["mes"] = df["mes"].astype(int)
df["regiao"] = df["regiao"].astype(str).str.strip()
df["instituicao"] = df["instituicao"].astype(str).str.strip()

df["tempo"] = pd.to_datetime(
    dict(
        year=df["ano"],
        month=df["mes"],
        day=1,
    )
)

REGIOES = [
    "Norte",
    "Centro",
    "Lisboa e Vale do Tejo",
    "Alentejo",
    "Algarve",
]

COLORBLIND = [
    "#0072B2",
    "#E69F00",
    "#009E73",
    "#D55E00",
    "#CC79A7",
    "#56B4E9",
]

REGION_OPTIONS = [{"label": "Todas as regiões", "value": "all"}] + [
    {"label": r, "value": r}
    for r in REGIOES
]

# ============================================================
# HELPERS
# ============================================================

def criar_sparkline(x_data, y_data, cor):
    fig = go.Figure()

    fig.add_trace(
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
        height=48,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )

    return fig


def kpi_card(title, value, spark=None, color=None, subtitle=None):
    children = [
        html.Div(title, className="kpi-title"),
        html.Div(
            value,
            className="kpi-value",
            style={"color": color} if color else {},
        ),
    ]

    if spark is not None:
        children.append(
            dcc.Graph(
                figure=spark,
                config={
                    "displayModeBar": False,
                    "staticPlot": True,
                },
            )
        )

    if subtitle:
        children.append(
            html.Div(
                subtitle,
                className="kpi-subtitle",
                style={
                    "marginTop": "10px",
                    "fontSize": "0.85rem",
                    "color": "#7f8c8d",
                },
            )
        )

    return html.Div(
        className="kpi-card",
        children=children,
    )


def parse_range_year(value):
    try:
        return int(float(value))
    except Exception:
        return pd.to_datetime(value).year


def empty_figure(title, text="Sem dados para os filtros selecionados"):
    fig = go.Figure()

    fig.update_layout(
        title=dict(text=title, x=0.03),
        height=380,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text=text,
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=14),
            )
        ],
        margin=dict(l=30, r=30, t=80, b=40),
    )

    return fig


def build_temporal_figure(dff):
    ts = (
        dff.groupby("tempo")
        .agg(
            gastos=("gastos_operacionais", "sum"),
            rendimentos=("rendimentos_operacionais", "sum"),
            divida=("divida_total_fornecedores_externos", "sum"),
        )
        .reset_index()
        .sort_values("tempo")
    )

    if ts.empty:
        return empty_figure("Evolução Financeira")

    ts["gastos_m"] = ts["gastos"] / 1e6
    ts["rendimentos_m"] = ts["rendimentos"] / 1e6
    ts["divida_m"] = ts["divida"] / 1e6
    ts["saldo_m"] = ts["rendimentos_m"] - ts["gastos_m"]

    ts["mm_gastos"] = ts["gastos_m"].rolling(3).mean()
    ts["mm_rendimentos"] = ts["rendimentos_m"].rolling(3).mean()

    fig = go.Figure()

    fig.add_trace(
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

    fig.add_trace(
        go.Scatter(
            x=ts["tempo"],
            y=ts["gastos_m"],
            name="Gastos",
            mode="lines",
            line=dict(color="#D55E00", width=2),
            hovertemplate="Data: %{x|%Y-%m}<br>Gastos: %{y:.1f} M€<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=ts["tempo"],
            y=ts["saldo_m"],
            name="Saldo",
            mode="lines",
            line=dict(color="#0072B2", width=3),
            hovertemplate="Data: %{x|%Y-%m}<br>Saldo: %{y:.1f} M€<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=ts["tempo"],
            y=ts["mm_rendimentos"],
            name="MM Rendimentos 3m",
            mode="lines",
            line=dict(color="#009E73", width=3, dash="dot"),
            hovertemplate="Data: %{x|%Y-%m}<br>MM Rendimentos: %{y:.1f} M€<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=ts["tempo"],
            y=ts["mm_gastos"],
            name="MM Gastos 3m",
            mode="lines",
            line=dict(color="#D55E00", width=3, dash="dot"),
            hovertemplate="Data: %{x|%Y-%m}<br>MM Gastos: %{y:.1f} M€<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text="Evolução Financeira<br><sup>Use o slider inferior para selecionar o período</sup>",
            x=0.03,
            font=dict(size=16),
        ),
        height=420,
        uirevision="finance-temporal",
        xaxis=dict(
            rangeslider=dict(visible=True),
            type="date",
            title=None,
        ),
        yaxis=dict(title="M€"),
        legend=dict(orientation="h", y=1.12, x=0),
        margin=dict(l=30, r=30, t=95, b=40),
        plot_bgcolor="white",
    )

    return fig


# ============================================================
# LAYOUT
# ============================================================

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

        html.Div(
            id="finance-kpis-v2",
            className="kpi-row",
        ),

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
                    children=[
                        dcc.Graph(
                            id="finance-waterfall-v2",
                            config={"displayModeBar": False},
                        )
                    ],
                ),

                html.Div(
                    className="card",
                    children=[
                        dcc.Graph(
                            id="finance-comparison-v2",
                            config={"displayModeBar": False},
                        )
                    ],
                ),

                html.Div(
                    className="card",
                    children=[
                        dcc.Graph(
                            id="finance-risk-v2",
                            config={"displayModeBar": False},
                        )
                    ],
                ),

                html.Div(
                    className="card",
                    children=[
                        dcc.Graph(
                            id="finance-structure-v2",
                            config={"displayModeBar": False},
                        )
                    ],
                ),
            ],
        ),
    ],
)

# ============================================================
# FILTER CALLBACK
# ============================================================

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

# ============================================================
# RANGE SLIDER CALLBACK
# ============================================================

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

# ============================================================
# UPDATE DASHBOARD
# ============================================================

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
        start_date = pd.to_datetime(range_data["start"])
        end_date = pd.to_datetime(range_data["end"])

        dff = dff[
            (dff["tempo"] >= start_date)
            & (dff["tempo"] <= end_date)
        ]

    if dff.empty:
        return (
            [
                kpi_card("Total Gastos", "0.0 M€"),
                kpi_card("Total Rendimentos", "0.0 M€"),
                kpi_card("Balanço", "0.0 M€"),
                kpi_card("Instituições", "0"),
            ],
            empty_figure("Evolução Financeira"),
            empty_figure("Cascata Financeira"),
            empty_figure("Comparação Financeira"),
            empty_figure("Risco Financeiro"),
            empty_figure("Estrutura Financeira"),
        )

    # ========================================================
    # KPIs
    # ========================================================

    total_gastos = dff["gastos_operacionais"].sum() / 1e6
    total_rendimentos = dff["rendimentos_operacionais"].sum() / 1e6
    total_divida = dff["divida_total_fornecedores_externos"].sum() / 1e6
    balanco = total_rendimentos - total_gastos
    instituicoes = dff["instituicao"].nunique()
    periodos = dff["tempo"].nunique()

    spark_data = (
        dff.groupby("tempo")
        .agg(
            gastos=("gastos_operacionais", "sum"),
            rendimentos=("rendimentos_operacionais", "sum"),
            divida=("divida_total_fornecedores_externos", "sum"),
        )
        .reset_index()
        .sort_values("tempo")
    )

    spark_data["saldo"] = spark_data["rendimentos"] - spark_data["gastos"]

    cor_saldo = "#009E73" if balanco >= 0 else "#D55E00"

    kpis = [
        kpi_card(
            "Total Gastos",
            f"{total_gastos:,.1f} M€",
            criar_sparkline(spark_data["tempo"], spark_data["gastos"], "#D55E00"),
        ),

        kpi_card(
            "Total Rendimentos",
            f"{total_rendimentos:,.1f} M€",
            criar_sparkline(spark_data["tempo"], spark_data["rendimentos"], "#009E73"),
        ),

        kpi_card(
            "Balanço",
            f"{balanco:,.1f} M€",
            criar_sparkline(spark_data["tempo"], spark_data["saldo"], cor_saldo),
            color=cor_saldo,
        ),

        kpi_card(
            "Dívida / Instituições",
            f"{total_divida:,.1f} M€",
            subtitle=f"{instituicoes} instituições | {periodos} períodos",
        ),
    ]

    # ========================================================
    # HERO GRAPH
    # ========================================================

    fig_main = build_temporal_figure(dff_base)

    # ========================================================
    # WATERFALL
    # ========================================================

    fig_waterfall = go.Figure()

    fig_waterfall.add_trace(
        go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "relative", "total"],
            x=["Rendimentos", "Gastos", "Dívida", "Saldo"],
            y=[
                total_rendimentos,
                -total_gastos,
                -total_divida,
                balanco,
            ],
            text=[
                f"{total_rendimentos:,.1f}",
                f"-{total_gastos:,.1f}",
                f"-{total_divida:,.1f}",
                f"{balanco:,.1f}",
            ],
            textposition="outside",
            connector={"line": {"color": "#6B7280"}},
            increasing={"marker": {"color": "#009E73"}},
            decreasing={"marker": {"color": "#D55E00"}},
            totals={"marker": {"color": "#0072B2"}},
            hovertemplate="%{x}<br>%{y:.1f} M€<extra></extra>",
        )
    )

    fig_waterfall.update_layout(
        title=dict(
            text="Cascata Financeira do Período",
            x=0.03,
        ),
        height=380,
        margin=dict(l=30, r=30, t=90, b=40),
        yaxis=dict(title="M€"),
        showlegend=False,
        plot_bgcolor="white",
    )

    # ========================================================
    # CONTEXT-AWARE COMPARISON
    # ========================================================

    if selected_institution != "all":
        annual = (
            dff.groupby("tempo")
            .agg(
                gastos=("gastos_operacionais", "sum"),
                rendimentos=("rendimentos_operacionais", "sum"),
            )
            .reset_index()
            .sort_values("tempo")
        )

        annual["gastos_m"] = annual["gastos"] / 1e6
        annual["rendimentos_m"] = annual["rendimentos"] / 1e6
        annual["saldo_m"] = annual["rendimentos_m"] - annual["gastos_m"]

        fig_comparison = go.Figure()

        fig_comparison.add_trace(
            go.Bar(
                x=annual["tempo"],
                y=annual["rendimentos_m"],
                name="Rendimentos",
                marker_color="#009E73",
                hovertemplate="Data: %{x|%Y-%m}<br>Rendimentos: %{y:.1f} M€<extra></extra>",
            )
        )

        fig_comparison.add_trace(
            go.Bar(
                x=annual["tempo"],
                y=annual["gastos_m"],
                name="Gastos",
                marker_color="#D55E00",
                hovertemplate="Data: %{x|%Y-%m}<br>Gastos: %{y:.1f} M€<extra></extra>",
            )
        )

        fig_comparison.add_trace(
            go.Scatter(
                x=annual["tempo"],
                y=annual["saldo_m"],
                name="Saldo",
                mode="lines+markers",
                line=dict(color="#0072B2", width=3),
                hovertemplate="Data: %{x|%Y-%m}<br>Saldo: %{y:.1f} M€<extra></extra>",
            )
        )

        fig_comparison.update_layout(
            title=dict(
                text="Evolução Mensal da Instituição",
                x=0.03,
            ),
            height=380,
            barmode="group",
            margin=dict(l=30, r=30, t=90, b=40),
            yaxis=dict(title="M€"),
            legend=dict(orientation="h", y=1.12),
            plot_bgcolor="white",
        )

    elif selected_region != "all":
        inst_df = (
            dff.groupby("instituicao")
            .agg(
                gastos=("gastos_operacionais", "sum"),
                rendimentos=("rendimentos_operacionais", "sum"),
            )
            .reset_index()
        )

        inst_df["gastos_m"] = inst_df["gastos"] / 1e6
        inst_df["rendimentos_m"] = inst_df["rendimentos"] / 1e6
        inst_df["saldo_m"] = inst_df["rendimentos_m"] - inst_df["gastos_m"]

        inst_df = (
            inst_df.sort_values("gastos_m", ascending=False)
            .head(12)
            .sort_values("gastos_m")
        )

        fig_comparison = go.Figure()

        for _, row in inst_df.iterrows():
            fig_comparison.add_trace(
                go.Scatter(
                    x=[row["gastos_m"], row["rendimentos_m"]],
                    y=[row["instituicao"], row["instituicao"]],
                    mode="lines",
                    line=dict(color="#bdc3c7", width=3),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

        fig_comparison.add_trace(
            go.Scatter(
                x=inst_df["gastos_m"],
                y=inst_df["instituicao"],
                mode="markers",
                name="Gastos",
                marker=dict(color="#D55E00", size=12, line=dict(color="white", width=1)),
                hovertemplate="<b>%{y}</b><br>Gastos: %{x:.1f} M€<extra></extra>",
            )
        )

        fig_comparison.add_trace(
            go.Scatter(
                x=inst_df["rendimentos_m"],
                y=inst_df["instituicao"],
                mode="markers",
                name="Rendimentos",
                marker=dict(color="#009E73", size=12, line=dict(color="white", width=1)),
                hovertemplate="<b>%{y}</b><br>Rendimentos: %{x:.1f} M€<extra></extra>",
            )
        )

        fig_comparison.update_layout(
            title=dict(
                text="Dumbbell: Gastos vs Rendimentos por Instituição",
                x=0.03,
            ),
            height=420,
            margin=dict(l=90, r=30, t=90, b=40),
            xaxis=dict(title="M€", showgrid=True, gridcolor="lightgrey"),
            yaxis=dict(title=None, automargin=True),
            legend=dict(orientation="h", y=1.12),
            plot_bgcolor="white",
        )

    else:
        regional_df = (
            dff.groupby("regiao")
            .agg(
                gastos=("gastos_operacionais", "sum"),
                rendimentos=("rendimentos_operacionais", "sum"),
            )
            .reindex(REGIOES)
            .fillna(0)
            .reset_index()
        )

        regional_df["gastos_m"] = regional_df["gastos"] / 1e6
        regional_df["rendimentos_m"] = regional_df["rendimentos"] / 1e6
        regional_df["saldo_m"] = regional_df["rendimentos_m"] - regional_df["gastos_m"]

        regional_df = regional_df.sort_values("gastos_m", ascending=True)

        fig_comparison = go.Figure()

        for _, row in regional_df.iterrows():
            fig_comparison.add_trace(
                go.Scatter(
                    x=[row["gastos_m"], row["rendimentos_m"]],
                    y=[row["regiao"], row["regiao"]],
                    mode="lines",
                    line=dict(color="#bdc3c7", width=3),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

        fig_comparison.add_trace(
            go.Scatter(
                x=regional_df["gastos_m"],
                y=regional_df["regiao"],
                mode="markers",
                name="Gastos",
                marker=dict(color="#D55E00", size=13, line=dict(color="white", width=1)),
                hovertemplate="<b>%{y}</b><br>Gastos: %{x:.1f} M€<extra></extra>",
            )
        )

        fig_comparison.add_trace(
            go.Scatter(
                x=regional_df["rendimentos_m"],
                y=regional_df["regiao"],
                mode="markers",
                name="Rendimentos",
                marker=dict(color="#009E73", size=13, line=dict(color="white", width=1)),
                hovertemplate="<b>%{y}</b><br>Rendimentos: %{x:.1f} M€<extra></extra>",
            )
        )

        fig_comparison.update_layout(
            title=dict(
                text="Dumbbell: Gastos vs Rendimentos por Região",
                x=0.03,
            ),
            height=380,
            margin=dict(l=90, r=30, t=90, b=40),
            xaxis=dict(title="M€", showgrid=True, gridcolor="lightgrey"),
            yaxis=dict(title=None),
            legend=dict(orientation="h", y=1.12),
            plot_bgcolor="white",
        )

    # ========================================================
    # FINANCIAL RISK / DEBT
    # ========================================================

    if selected_institution != "all":
        debt = (
            dff.groupby("tempo")
            .agg(
                divida=("divida_total_fornecedores_externos", "sum"),
                gastos=("gastos_operacionais", "sum"),
            )
            .reset_index()
            .sort_values("tempo")
        )

        debt["divida_m"] = debt["divida"] / 1e6
        debt["gastos_m"] = debt["gastos"] / 1e6

        fig_risk = go.Figure()

        fig_risk.add_trace(
            go.Bar(
                x=debt["tempo"],
                y=debt["divida_m"],
                name="Dívida",
                marker_color="#CC79A7",
                hovertemplate="Data: %{x|%Y-%m}<br>Dívida: %{y:.1f} M€<extra></extra>",
            )
        )

        fig_risk.add_trace(
            go.Scatter(
                x=debt["tempo"],
                y=debt["gastos_m"],
                mode="lines+markers",
                name="Gastos",
                line=dict(color="#D55E00", width=3),
                hovertemplate="Data: %{x|%Y-%m}<br>Gastos: %{y:.1f} M€<extra></extra>",
            )
        )

        fig_risk.update_layout(
            title=dict(text="Dívida e Gastos da Instituição", x=0.03),
            height=380,
            margin=dict(l=30, r=30, t=90, b=40),
            yaxis=dict(title="M€"),
            legend=dict(orientation="h", y=1.12),
            plot_bgcolor="white",
        )

    elif selected_region != "all":
        risk_df = (
            dff.groupby("instituicao")
            .agg(
                gastos=("gastos_operacionais", "sum"),
                divida=("divida_total_fornecedores_externos", "sum"),
                urgencias=("total_urgencias", "sum"),
            )
            .reset_index()
        )

        risk_df["gastos_m"] = risk_df["gastos"] / 1e6
        risk_df["divida_m"] = risk_df["divida"] / 1e6
        risk_df["urgencias"] = risk_df["urgencias"].replace([np.inf, -np.inf], np.nan).fillna(0)

        max_urg = risk_df["urgencias"].max()
        if max_urg > 0:
            risk_df["size"] = (risk_df["urgencias"] / max_urg * 40) + 8
        else:
            risk_df["size"] = 12

        fig_risk = go.Figure()

        fig_risk.add_trace(
            go.Scatter(
                x=risk_df["gastos_m"],
                y=risk_df["divida_m"],
                mode="markers",
                marker=dict(
                    size=risk_df["size"],
                    color="#0072B2",
                    opacity=0.75,
                    line=dict(color="white", width=1),
                ),
                customdata=risk_df[["instituicao", "urgencias"]],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Gastos: %{x:.1f} M€<br>"
                    "Dívida: %{y:.1f} M€<br>"
                    "Urgências: %{customdata[1]:,.0f}"
                    "<extra></extra>"
                ),
            )
        )

        if len(risk_df) > 0:
            fig_risk.add_vline(
                x=risk_df["gastos_m"].mean(),
                line_dash="dash",
                line_color="#6B7280",
                annotation_text="Média gastos",
            )
            fig_risk.add_hline(
                y=risk_df["divida_m"].mean(),
                line_dash="dash",
                line_color="#6B7280",
                annotation_text="Média dívida",
            )

        fig_risk.update_layout(
            title=dict(text="Risco Financeiro das Instituições", x=0.03),
            height=380,
            margin=dict(l=30, r=30, t=90, b=40),
            xaxis=dict(title="Gastos (M€)"),
            yaxis=dict(title="Dívida (M€)"),
            plot_bgcolor="white",
        )

    else:
        regional_debt = (
            dff.groupby("regiao")
            .agg(
                divida=("divida_total_fornecedores_externos", "sum"),
                gastos=("gastos_operacionais", "sum"),
            )
            .reindex(REGIOES)
            .fillna(0)
            .reset_index()
        )

        regional_debt["divida_m"] = regional_debt["divida"] / 1e6
        regional_debt["gastos_m"] = regional_debt["gastos"] / 1e6

        fig_risk = go.Figure()

        fig_risk.add_trace(
            go.Bar(
                x=regional_debt["regiao"],
                y=regional_debt["divida_m"],
                name="Dívida",
                marker_color="#CC79A7",
                customdata=regional_debt[["gastos_m"]],
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Dívida: %{y:.1f} M€<br>"
                    "Gastos: %{customdata[0]:.1f} M€"
                    "<extra></extra>"
                ),
            )
        )

        fig_risk.update_layout(
            title=dict(text="Dívida Total por Região", x=0.03),
            height=380,
            margin=dict(l=30, r=30, t=90, b=40),
            yaxis=dict(title="Dívida (M€)"),
            showlegend=False,
            plot_bgcolor="white",
        )

    # ========================================================
    # STRUCTURE GRAPH — SUNBURST
    # ========================================================

    if "tipo_instituicao" in dff.columns:
        struct_df = (
            dff[dff["regiao"] != "Serviços Centrais"]
            .groupby(["regiao", "tipo_instituicao"])
            .agg(gastos=("gastos_operacionais", "sum"))
            .reset_index()
        )

        struct_df["Total"] = "SNS Total"

        if struct_df.empty:
            fig_structure = empty_figure("Estrutura dos Gastos")
        else:
            fig_structure = px.sunburst(
                struct_df,
                path=["Total", "regiao", "tipo_instituicao"],
                values="gastos",
                color="regiao",
                color_discrete_sequence=COLORBLIND,
                title="Distribuição de Gastos Operacionais",
            )

            fig_structure.update_traces(
                textinfo="label+percent parent",
                insidetextorientation="radial",
                hovertemplate="<b>%{label}</b><br>Gastos: %{value:,.0f}€<extra></extra>",
            )

            fig_structure.update_layout(
                height=420,
                margin=dict(t=80, l=10, r=10, b=10),
                title=dict(text="Distribuição de Gastos Operacionais", x=0.5),
            )

    else:
        struct_df = (
            dff.groupby(["regiao", "instituicao"])
            .agg(gastos=("gastos_operacionais", "sum"))
            .reset_index()
        )

        struct_df["Total"] = "SNS Total"

        fig_structure = px.sunburst(
            struct_df,
            path=["Total", "regiao", "instituicao"],
            values="gastos",
            color="regiao",
            color_discrete_sequence=COLORBLIND,
            title="Distribuição de Gastos Operacionais",
        )

        fig_structure.update_layout(
            height=420,
            margin=dict(t=80, l=10, r=10, b=10),
            title=dict(text="Distribuição de Gastos Operacionais", x=0.5),
        )

    return (
        kpis,
        fig_main,
        fig_waterfall,
        fig_comparison,
        fig_risk,
        fig_structure,
    )