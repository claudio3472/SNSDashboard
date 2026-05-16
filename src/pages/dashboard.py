# ============================================================
# dashboard.py
# ============================================================

import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from dash import html, dcc, Input, Output, callback, ctx, no_update
from pages.pages_helper import load_data, process_data, create_sparkline, kpi_card


# ============================================================
# LOAD & PROCESS DATA
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "processed", "master_dataset.csv")

df = process_data(load_data(DATA_PATH))

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

MIN_DATE = df["tempo"].min().date()
MAX_DATE = df["tempo"].max().date()

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

if "tipo_instituicao" not in df.columns:
    df["tipo_instituicao"] = "Instituição"

df = df[df["tipo_instituicao"].isin(["ULS", "IPO", "Hospital"])].copy()


# ============================================================
# SAFE COLUMNS
# ============================================================

NUMERIC_COLS = [
    "medicos_internos",
    "medicos_s_internos",
    "enfermeiros",
    "gastos_operacionais",
    "rendimentos_operacionais",
    "resultado_liquido",
    "ebitda",
    "total_urgencias",
    "no_de_consultas_medicas_total",
    "divida_total_fornecedores_externos",
    "no_intervencoes_cirurgicas_programadas",
    "no_intervencoes_cirurgicas_convencionais",
    "no_intervencoes_cirurgicas_urgentes",
    "no_intervencoes_cirurgicas_de_ambulatorio",
]

for col in NUMERIC_COLS:
    if col not in df.columns:
        df[col] = 0

for col in NUMERIC_COLS:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)


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


def empty_figure(title, text="Sem dados para os filtros selecionados"):
    fig = go.Figure()

    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center"),
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


def period_label(start_date, end_date):
    return f"{start_date} a {end_date or str(MAX_DATE)}"


# ============================================================
# LAYOUT
# ============================================================

layout = html.Div(
    className="content",
    children=[

        # ====================================================
        # HEADER
        # ====================================================

        html.Div(
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "flex-start",
                "marginBottom": "25px",
                "gap": "20px",
                "flexWrap": "wrap",
            },
            children=[

                # LEFT SIDE
                html.Div(
                    children=[
                        html.H2(
                            "Dashboard Geral",
                            style={"marginBottom": "8px"},
                        ),

                        html.P(
                            "Visão global do SNS",
                            style={
                                "color": "#6b7280",
                                "marginBottom": "0px",
                            },
                        ),
                    ]
                ),

                # RIGHT SIDE (DATES)
                html.Div(
                    style={
                        "display": "flex",
                        "gap": "14px",
                        "alignItems": "flex-end",
                        "marginTop": "10px",
                    },
                    children=[

                        html.Div(
                            children=[
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
                                    id="dashboard-start-date",
                                    min_date_allowed=MIN_DATE,
                                    max_date_allowed=MAX_DATE,
                                    date=MIN_DATE,
                                    display_format="YYYY-MM-DD",
                                    style={
                                        "borderRadius": "10px",
                                    },
                                ),
                            ]
                        ),

                        html.Div(
                            children=[
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
                                    id="dashboard-end-date",
                                    min_date_allowed=MIN_DATE,
                                    max_date_allowed=MAX_DATE,
                                    date=None,
                                    placeholder="Última disponível",
                                    display_format="YYYY-MM-DD",
                                    style={
                                        "borderRadius": "10px",
                                    },
                                ),
                            ]
                        ),
                    ],
                ),
            ],
        ),

        # ====================================================
        # FILTERS
        # ====================================================

        html.Div(
            className="filter-row",
            style={
                "display": "flex",
                "gap": "1rem",
                "flexWrap": "wrap",
                "alignItems": "center",
                "marginBottom": "25px",
            },
            children=[

                dcc.Dropdown(
                    id="dashboard-region-filter",
                    options=REGION_OPTIONS,
                    value="all",
                    clearable=False,
                    placeholder="Selecionar região",
                    style={
                        "minWidth": "260px",
                    },
                ),

                dcc.Dropdown(
                    id="dashboard-institution-filter",
                    value="all",
                    clearable=False,
                    placeholder="Selecionar instituição",
                    style={
                        "minWidth": "320px",
                    },
                ),
            ],
        ),

        html.Div(id="dashboard-kpis"),

        html.Div(
            className="grid-2x2",
            children=[
                dcc.Graph(id="dashboard-prof"),
                dcc.Graph(id="dashboard-finance"),
                dcc.Graph(id="dashboard-pie"),
                dcc.Graph(id="dashboard-radar"),
            ],
        ),
    ],
)

# ============================================================
# CHART BUILDERS
# ============================================================

def build_fig_profissionais(dff, label_periodo):
    if dff.empty:
        return empty_figure("Profissionais por Região")

    dff = dff.copy()
    dff["total_medicos"] = dff["medicos_internos"] + dff["medicos_s_internos"]

    prof = (
        dff.groupby("regiao")[["total_medicos", "enfermeiros"]]
        .mean()
        .fillna(0)
    )

    prof["total_profissionais"] = prof["total_medicos"] + prof["enfermeiros"]
    prof = prof.sort_values("total_profissionais", ascending=True)

    fig = go.Figure()

    fig.add_bar(
        y=prof.index,
        x=prof["total_medicos"],
        name="Médicos",
        orientation="h",
        marker_color="#2e86de",
        hovertemplate="<b>%{y}</b><br>Médicos: %{x:.0f}<extra></extra>",
    )

    fig.add_bar(
        y=prof.index,
        x=prof["enfermeiros"],
        name="Enfermeiros",
        orientation="h",
        marker_color="#16a085",
        hovertemplate="<b>%{y}</b><br>Enfermeiros: %{x:.0f}<extra></extra>",
    )

    fig.update_layout(
        barmode="stack",
        title=dict(
            text=f"Profissionais por Região<br><sup>{label_periodo}</sup>",
            x=0.5,
        ),
        height=360,
        margin=dict(l=80, r=20, t=70, b=40),
        legend=dict(orientation="h", y=1.08),
        plot_bgcolor="white",
    )

    return fig


def build_fig_gastos_rendimentos(dff):
    if dff.empty:
        return empty_figure("Gastos vs Rendimentos")

    gvr = (
        dff.groupby("regiao")[["gastos_operacionais", "rendimentos_operacionais"]]
        .sum()
        .fillna(0)
        / 1e6
    )

    gvr = gvr.sort_values("gastos_operacionais", ascending=True)

    fig = go.Figure()

    for reg in gvr.index:
        fig.add_trace(
            go.Scatter(
                x=[
                    gvr.loc[reg, "gastos_operacionais"],
                    gvr.loc[reg, "rendimentos_operacionais"],
                ],
                y=[reg, reg],
                mode="lines",
                line=dict(color="#bdc3c7", width=3),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=gvr["gastos_operacionais"],
            y=gvr.index,
            mode="markers",
            name="Gastos",
            marker=dict(
                color="#e74c3c",
                size=12,
                line=dict(color="white", width=1),
            ),
            hovertemplate="%{y}<br>Gastos: %{x:.1f} M€<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=gvr["rendimentos_operacionais"],
            y=gvr.index,
            mode="markers",
            name="Rendimentos",
            marker=dict(
                color="#27ae60",
                size=12,
                line=dict(color="white", width=1),
            ),
            hovertemplate="%{y}<br>Rendimentos: %{x:.1f} M€<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text="Gastos vs Rendimentos por Região",
            x=0.5,
        ),
        xaxis=dict(title="M€", showgrid=True, gridcolor="lightgrey"),
        yaxis=dict(showgrid=True, gridcolor="whitesmoke"),
        height=360,
        margin=dict(l=80, r=20, t=60, b=40),
        legend=dict(orientation="h", y=1.08),
        plot_bgcolor="white",
    )

    return fig


def build_fig_sunburst(dff):
    if dff.empty:
        return empty_figure("Distribuição de Gastos Operacionais")

    cols = [
        "gastos_operacionais",
        "rendimentos_operacionais",
        "resultado_liquido",
        "ebitda",
    ]

    sun_df = (
        dff
        .loc[
            ~dff["tipo_instituicao"]
            .astype(str)
            .str.contains("Serviços Centrais", case=False, na=False)
        ]
        .groupby(["regiao", "tipo_instituicao"])[cols]
        .sum()
        .reset_index()
    )

    if sun_df.empty:
        return empty_figure("Distribuição de Gastos Operacionais")

    reg_df = sun_df.groupby("regiao")[cols].sum().reset_index()
    total = sun_df[cols].sum()

    ids, labels, parents, values, colors, customdata = [], [], [], [], [], []

    def add_row(id_, label, parent, gastos, rendimentos, res_liq, ebitda):
        ids.append(str(id_))
        labels.append(str(label))
        parents.append(str(parent))
        values.append(float(gastos) / 1e6)
        colors.append(float(res_liq) / 1e6)
        customdata.append([
            float(rendimentos) / 1e6,
            float(res_liq) / 1e6,
            float(ebitda) / 1e6,
        ])

    add_row(
        "SNS",
        "SNS Total",
        "",
        total["gastos_operacionais"],
        total["rendimentos_operacionais"],
        total["resultado_liquido"],
        total["ebitda"],
    )

    for _, r in reg_df.iterrows():
        add_row(
            r["regiao"],
            r["regiao"],
            "SNS",
            r["gastos_operacionais"],
            r["rendimentos_operacionais"],
            r["resultado_liquido"],
            r["ebitda"],
        )

    for _, r in sun_df.iterrows():
        add_row(
            f"{r['regiao']}|{r['tipo_instituicao']}",
            r["tipo_instituicao"],
            r["regiao"],
            r["gastos_operacionais"],
            r["rendimentos_operacionais"],
            r["resultado_liquido"],
            r["ebitda"],
        )

    fig = go.Figure(
        go.Sunburst(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            marker=dict(
                colors=colors,
                colorscale="RdYlGn",
                cmid=0,
                showscale=True,
                colorbar=dict(
                    title="Res. Líquido (M€)",
                    thickness=14,
                    len=0.6,
                    tickformat=".0f",
                ),
            ),
            customdata=customdata,
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Gastos: %{value:.1f} M€<br>"
                "Rendimentos: %{customdata[0]:.1f} M€<br>"
                "Resultado Líquido: %{customdata[1]:.1f} M€<br>"
                "EBITDA: %{customdata[2]:.1f} M€<br>"
                "% do total: %{percentRoot:.1%}<br>"
                "<extra></extra>"
            ),
            textinfo="label+percent parent",
            insidetextorientation="radial",
            branchvalues="total",
        )
    )

    fig.update_layout(
        title=dict(
            text="Distribuição de Gastos Operacionais",
            x=0.5,
        ),
        margin=dict(t=70, l=10, r=10, b=10),
        height=520,
    )

    return fig


def build_fig_parallel(dff, click_prof):
    if dff.empty:
        return empty_figure("Padrões de Atividade Assistencial por Instituição")

    dff = dff.copy()

    dff["total_cirurgias"] = dff[
        [
            "no_intervencoes_cirurgicas_programadas",
            "no_intervencoes_cirurgicas_convencionais",
            "no_intervencoes_cirurgicas_urgentes",
            "no_intervencoes_cirurgicas_de_ambulatorio",
        ]
    ].sum(axis=1)

    pc_df = (
        dff.groupby(["instituicao", "regiao"])[
            [
                "total_urgencias",
                "total_cirurgias",
                "no_de_consultas_medicas_total",
            ]
        ]
        .sum()
        .reset_index()
    )

    pc_df = pc_df.replace([np.inf, -np.inf], np.nan).fillna(0)

    if pc_df.empty:
        return empty_figure("Padrões de Atividade Assistencial por Instituição")

    highlight_region = click_prof["points"][0]["y"] if click_prof else None
    regioes_unicas = pc_df["regiao"].unique().tolist()

    if highlight_region and highlight_region in regioes_unicas:
        pc_df["regiao_id"] = pc_df["regiao"].apply(
            lambda x: 1 if x == highlight_region else 0
        )

        colorscale = [[0, "#ecf0f1"], [1, "#2e86de"]]
        cmax = 1

        colorbar_dict = dict(
            title="Região",
            tickmode="array",
            tickvals=[0, 1],
            ticktext=["Outras", highlight_region],
        )

    else:
        pc_df["regiao_id"] = pc_df["regiao"].apply(
            lambda x: regioes_unicas.index(x)
        )

        colorscale = px.colors.qualitative.Bold
        cmax = max(0, len(regioes_unicas) - 1)

        colorbar_dict = dict(
            title="Região",
            tickmode="array",
            tickvals=list(range(len(regioes_unicas))),
            ticktext=regioes_unicas,
        )

    fig = go.Figure(
        data=go.Parcoords(
            line=dict(
                color=pc_df["regiao_id"],
                colorscale=colorscale,
                showscale=True,
                cmin=0,
                cmax=cmax,
                colorbar=colorbar_dict,
            ),
            dimensions=[
                dict(label="Urgências", values=pc_df["total_urgencias"]),
                dict(label="Cirurgias", values=pc_df["total_cirurgias"]),
                dict(label="Consultas", values=pc_df["no_de_consultas_medicas_total"]),
            ],
        )
    )

    fig.update_layout(
        title=dict(
            text="Padrões de Atividade Assistencial por Instituição",
            x=0.5,
        ),
        height=520,
        margin=dict(l=60, r=40, t=90, b=40),
    )

    return fig


def build_kpis(dff):
    if dff.empty:
        return html.Div(
            className="kpi-row",
            children=[
                kpi_card("Urgências Totais", "0"),
                kpi_card("Consultas Médicas", "0"),
                kpi_card("Dívida Total (M€)", "0"),
                kpi_card("Instituições", "0"),
            ],
        )

    kpi_urgencias = int(dff["total_urgencias"].sum())
    kpi_consultas = int(dff["no_de_consultas_medicas_total"].sum())
    kpi_divida = dff["divida_total_fornecedores_externos"].sum() / 1e6
    kpi_instituicoes = dff["instituicao"].nunique()

    spark_data = (
        dff.groupby("tempo")[
            [
                "total_urgencias",
                "no_de_consultas_medicas_total",
                "divida_total_fornecedores_externos",
            ]
        ]
        .sum()
        .reset_index()
        .sort_values("tempo")
    )

    return html.Div(
        className="kpi-row",
        children=[
            kpi_card(
                "Urgências Totais",
                f"{kpi_urgencias:,}".replace(",", " "),
                dcc.Graph(
                    figure=create_sparkline(
                        spark_data["tempo"],
                        spark_data["total_urgencias"],
                        "#5c1b02",
                    ),
                    config={"displayModeBar": False, "staticPlot": True},
                ),
            ),
            kpi_card(
                "Consultas Médicas",
                f"{kpi_consultas:,}".replace(",", " "),
                dcc.Graph(
                    figure=create_sparkline(
                        spark_data["tempo"],
                        spark_data["no_de_consultas_medicas_total"],
                        "#3e91e4",
                    ),
                    config={"displayModeBar": False, "staticPlot": True},
                ),
            ),
            kpi_card(
                "Dívida Total (M€)",
                f"{kpi_divida:,.0f}".replace(",", " "),
                dcc.Graph(
                    figure=create_sparkline(
                        spark_data["tempo"],
                        spark_data["divida_total_fornecedores_externos"],
                        "#6e3088",
                    ),
                    config={"displayModeBar": False, "staticPlot": True},
                ),
            ),
            kpi_card(
                "Instituições",
                f"{kpi_instituicoes}",
                html.Div(
                    "Entidades ativas a reportar dados no período e filtros selecionados.",
                    style={
                        "color": "#7f8c8d",
                        "fontSize": "0.85rem",
                        "marginTop": "15px",
                        "lineHeight": "1.4",
                    },
                ),
            ),
        ],
    )


# ============================================================
# CALLBACKS
# ============================================================

@callback(
    Output("dashboard-institution-filter", "options"),
    Output("dashboard-institution-filter", "value"),
    Input("dashboard-region-filter", "value"),
)
def update_dashboard_institution_filter(region):
    dff = df.copy()

    if region != "all":
        dff = dff[dff["regiao"] == region]

    options = [{"label": "Todas as instituições", "value": "all"}] + [
        {"label": inst, "value": inst}
        for inst in sorted(dff["instituicao"].dropna().unique())
    ]

    return options, "all"


@callback(
    [
        Output("dashboard-kpis", "children"),
        Output("dashboard-prof", "figure"),
        Output("dashboard-finance", "figure"),
        Output("dashboard-pie", "figure"),
        Output("dashboard-radar", "figure"),
        Output("dashboard-prof", "clickData"),
        Output("dashboard-prof", "relayoutData"),
    ],
    [
        Input("dashboard-start-date", "date"),
        Input("dashboard-end-date", "date"),
        Input("dashboard-region-filter", "value"),
        Input("dashboard-institution-filter", "value"),
        Input("dashboard-prof", "clickData"),
        Input("dashboard-prof", "relayoutData"),
    ],
)
def update_dashboard(
    start_date,
    end_date,
    selected_region,
    selected_institution,
    click_prof,
    relayout_prof,
):
    triggered_props = [t["prop_id"] for t in ctx.triggered] if ctx.triggered else []
    relayout_triggered = any("relayoutData" in p for p in triggered_props)

    out_click = no_update
    out_relayout = no_update

    if relayout_triggered and relayout_prof and (
        "xaxis.autorange" in relayout_prof or "autosize" in relayout_prof
    ):
        click_prof = None
        out_click = None
        out_relayout = None

    dff = filter_period(df, start_date, end_date)

    if selected_region != "all":
        dff = dff[dff["regiao"] == selected_region]

    if selected_institution != "all":
        dff = dff[dff["instituicao"] == selected_institution]

    label_periodo = period_label(start_date, end_date)

    return (
        build_kpis(dff),
        build_fig_profissionais(dff, label_periodo),
        build_fig_gastos_rendimentos(dff),
        build_fig_sunburst(dff),
        build_fig_parallel(dff, click_prof),
        out_click,
        out_relayout,
    )