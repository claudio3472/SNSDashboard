import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from dash import html, dcc, Input, Output, callback, ctx, no_update
from pages.pages_helper import load_data, process_data, create_sparkline, kpi_card

# ============================================================
# LOAD & PROCESS DATA
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATA_PATH = os.path.join(BASE_DIR, "..", "data", "processed", "master_dataset.csv")
df = process_data(load_data(DEFAULT_DATA_PATH))

REGIOES = ["Norte", "Centro", "Lisboa e Vale do Tejo", "Alentejo", "Algarve"]
ANOS = sorted(df["ano"].astype(int).unique().tolist())
REGION_OPTIONS = [{"label": "Todas as regiões", "value": "all"}] + [
    {"label": r, "value": r} for r in REGIOES
]

df = df[df["tipo_instituicao"].isin(["ULS", "IPO", "Hospital"])]


# ============================================================
# LAYOUT
# ============================================================

layout = html.Div(
    className="content",
    children=[
        html.H2("Dashboard Geral"),
        html.P("Visão global do SNS"),

        html.Div(
            className="filter-row",
            style={"display": "flex", "gap": "1rem", "flexWrap": "wrap", "alignItems": "center"},
            children=[
                dcc.Dropdown(
                    id="dashboard-region-filter",
                    options=REGION_OPTIONS,
                    value=["all"],
                    multi=True,
                    clearable=True,
                    placeholder="Selecionar região(ões)",
                    style={"minWidth": "240px"},
                ),
                dcc.Dropdown(
                    id="dashboard-institution-filter",
                    value="all",
                    clearable=False,
                    placeholder="Selecionar instituição",
                    style={"minWidth": "240px"},
                ),
                html.Div(
                    className="slider-container",
                    style={"marginBottom": "2rem", "width": "60%"},
                    children=[
                        html.Label("Filtrar por Ano", style={"marginBottom": "0.5rem", "display": "block"}),
                        dcc.RangeSlider(
                            id="dashboard-slider",
                            min=int(min(ANOS)),
                            max=int(max(ANOS)),
                            step=1,
                            value=[int(min(ANOS)), int(max(ANOS))],
                            marks={int(ano): str(ano) for ano in ANOS},
                            tooltip={"placement": "bottom"},
                            allowCross=False,
                            updatemode="mouseup",
                            persistence=True,
                            persistence_type="session",
                        ),
                    ],
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

def build_fig_profissionais(df_filtered: pd.DataFrame, ano_inicio: int, ano_fim: int) -> go.Figure:
    """Stacked horizontal bar — médicos e enfermeiros por região."""
    df_filtered = df_filtered.copy()
    df_filtered["total_medicos"] = (
        df_filtered["medicos_internos"] + df_filtered["medicos_s_internos"]
    )

    monthly_totals = (
        df_filtered
        .groupby(["regiao", "ano", "mes"])[["total_medicos", "enfermeiros"]]
        .sum()
        .reset_index()
    )
    annual_avg = (
        monthly_totals
        .groupby(["regiao", "ano"])[["total_medicos", "enfermeiros"]]
        .mean()
        .reset_index()
    )
    prof = (
        annual_avg
        .groupby("regiao")[["total_medicos", "enfermeiros"]]
        .mean()
        .fillna(0)
    )
    prof["total_profissionais"] = prof["total_medicos"] + prof["enfermeiros"]
    prof = prof.sort_values("total_profissionais", ascending=True).drop(columns=["total_profissionais"])

    fig = go.Figure()
    fig.add_bar(
        y=prof.index,
        x=prof["total_medicos"],
        name="Médicos",
        orientation="h",
        marker_color="#2e86de",
        hovertemplate="<b>%{y}</b><br>Média Anual de Médicos: %{x:.0f}<extra></extra>",
    )
    fig.add_bar(
        y=prof.index,
        x=prof["enfermeiros"],
        name="Enfermeiros",
        orientation="h",
        marker_color="#16a085",
        hovertemplate="<b>%{y}</b><br>Média Anual de Enfermeiros: %{x:.0f}<extra></extra>",
    )

    titulo = (
        f"Profissionais por Região (Média {ano_inicio}-{ano_fim})"
        if ano_inicio != ano_fim
        else f"Profissionais por Região ({ano_inicio})"
    )
    fig.update_layout(
        barmode="stack",
        title={
            "text": titulo,
            "x": 0.5, "xanchor": "center",
            "y": 0.97, "yanchor": "top"
        },
        height=360,
        margin=dict(l=80, r=20, t=50, b=40),
    )
    return fig


def build_fig_gastos_rendimentos(df_filtered: pd.DataFrame) -> go.Figure:
    """Dumbbell chart — gastos vs rendimentos operacionais por região."""
    idx_last = df_filtered.groupby(["instituicao", "ano"])["mes"].idxmax()
    df_annual = df_filtered.loc[idx_last]

    gvr = (
        df_annual
        .groupby(["regiao", "ano"])[["gastos_operacionais", "rendimentos_operacionais"]]
        .sum()
        .reset_index()
        .groupby("regiao")[["gastos_operacionais", "rendimentos_operacionais"]]
        .mean()
        .fillna(0) / 1e6
    )
    gvr = gvr.sort_values("gastos_operacionais", ascending=True)

    fig = go.Figure()

    for reg in gvr.index:
        g = float(gvr.loc[reg, "gastos_operacionais"])
        r = float(gvr.loc[reg, "rendimentos_operacionais"])
        fig.add_trace(go.Scatter(
            x=[g, r],
            y=[reg, reg],
            mode="lines",
            line=dict(color="#bdc3c7", width=3),
            showlegend=False,
            hoverinfo="skip",
        ))

    fig.add_trace(go.Scatter(
        x=gvr["gastos_operacionais"],
        y=gvr.index,
        mode="markers",
        name="Gastos",
        marker=dict(color="#e74c3c", size=12, line=dict(color="white", width=1)),
        hovertemplate="%{y}<br>Gastos: %{x:.0f} M€<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=gvr["rendimentos_operacionais"],
        y=gvr.index,
        mode="markers",
        name="Rendimentos",
        marker=dict(color="#27ae60", size=12, line=dict(color="white", width=1)),
        hovertemplate="%{y}<br>Rendimentos: %{x:.0f} M€<extra></extra>",
    ))

    fig.update_layout(
        title={
            "text": "Gastos vs Rendimentos por Região - Média Anual (M€)",
            "x": 0.5, "xanchor": "center",
            "y": 0.97, "yanchor": "top"
        },
        xaxis=dict(title="M€", showgrid=True, gridcolor="lightgrey"),
        yaxis=dict(showgrid=True, gridcolor="whitesmoke"),
        height=360,
        margin=dict(l=80, r=20, t=50, b=40),
        plot_bgcolor="white",
    )
    return fig


def build_fig_sunburst(df_filtered: pd.DataFrame) -> go.Figure:
    """Sunburst — gastos por região/tipo, cor por resultado líquido, hover enriquecido."""
    cols = ["gastos_operacionais", "rendimentos_operacionais", "resultado_liquido", "ebitda"]

    idx_last = df_filtered.groupby(["instituicao", "ano"])["mes"].idxmax()
    df_annual = df_filtered.loc[idx_last]

    sun_df = (
        df_annual
        .loc[~df_annual["tipo_instituicao"].astype(str).str.contains(
            "Serviços Centrais", case=False, na=False
        )]
        .groupby(["regiao", "tipo_instituicao"])[cols]
        .sum()
        .reset_index()
    )

    reg_df = sun_df.groupby("regiao")[cols].sum().reset_index()

    total = sun_df[cols].sum()

    ids, labels, parents, values, colors, customdata = [], [], [], [], [], []

    def row(id_, label, parent, gastos, rendimentos, res_liq, ebitda):
        ids.append(id_)
        labels.append(label)
        parents.append(parent)
        values.append(gastos / 1e6)
        colors.append(res_liq / 1e6)
        customdata.append([rendimentos / 1e6, res_liq / 1e6, ebitda / 1e6])

    # Raiz
    row("SNS", "SNS Total", "",
        total["gastos_operacionais"],
        total["rendimentos_operacionais"],
        total["resultado_liquido"],
        total["ebitda"])

    # Regiões
    for _, r in reg_df.iterrows():
        row(r["regiao"], r["regiao"], "SNS",
            r["gastos_operacionais"],
            r["rendimentos_operacionais"],
            r["resultado_liquido"],
            r["ebitda"])

    # Folhas (região + tipo)
    for _, r in sun_df.iterrows():
        row(f"{r['regiao']}|{r['tipo_instituicao']}", r["tipo_instituicao"], r["regiao"],
            r["gastos_operacionais"],
            r["rendimentos_operacionais"],
            r["resultado_liquido"],
            r["ebitda"])

    # Figura ───────────────────────────────────────────────────────────────
    fig = go.Figure(go.Sunburst(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(
            colors=colors,
            colorscale="RdYlGn",
            cmid=0,
            showscale=True,
            colorbar=dict(title="Res. Líquido (M€)", thickness=14, len=0.6, tickformat=".0f"),
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
    ))

    fig.update_layout(
        uirevision="sunburst_lock",
        autosize=False,
        title={
            "text": "Distribuição de Gastos Operacionais",
            "x": 0.5, "xanchor": "center",
            "y": 0.97, "yanchor": "top"
        },
        margin=dict(t=60, l=10, r=10, b=10),
        height=520,
    )
    return fig


def build_fig_parallel(df_filtered: pd.DataFrame, click_prof: dict | None) -> go.Figure:
    """Parallel coordinates — padrões de atividade assistencial por instituição."""
    idx_last = df_filtered.groupby(["instituicao", "regiao", "ano"])["mes"].idxmax()
    df_annual = df_filtered.loc[idx_last].copy()

    df_annual["total_cirurgias"] = df_annual[[
        "no_intervencoes_cirurgicas_programadas",
        "no_intervencoes_cirurgicas_convencionais",
        "no_intervencoes_cirurgicas_urgentes",
        "no_intervencoes_cirurgicas_de_ambulatorio",
    ]].sum(axis=1)

    pc_df = (
        df_annual
        .groupby(["instituicao", "regiao"])[
            ["total_urgencias", "total_cirurgias", "no_de_consultas_medicas_total"]
        ]
        .mean()
        .reset_index()
    )

    highlight_region = click_prof["points"][0]["y"] if click_prof else None
    regioes_unicas = pc_df["regiao"].unique().tolist()

    if highlight_region and highlight_region in regioes_unicas:
        pc_df["regiao_id"] = pc_df["regiao"].apply(lambda x: 1 if x == highlight_region else 0)
        colorscale = [[0, "#ecf0f1"], [1, "#2e86de"]]
        cmax = 1
        colorbar_dict = dict(
            title="Região",
            tickmode="array",
            tickvals=[0, 1],
            ticktext=["Outras", highlight_region],
        )
    else:
        pc_df["regiao_id"] = pc_df["regiao"].apply(lambda x: regioes_unicas.index(x))
        colorscale = px.colors.qualitative.Bold
        cmax = max(0, len(regioes_unicas) - 1)
        colorbar_dict = dict(
            title="Região",
            tickmode="array",
            tickvals=list(range(len(regioes_unicas))),
            ticktext=regioes_unicas,
        )

    fig = go.Figure(data=go.Parcoords(
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
    ))
    fig.update_layout(
        title={"text": "Padrões de Atividade Assistencial por Instituição",
            "x": 0.5, "xanchor": "center",
            "y": 0.97, "yanchor": "top"
        },
        autosize=True,
        height=520,
        margin=dict(l=60, r=40, t=90, b=40),
    )
    return fig


def build_kpis(df_filtered: pd.DataFrame, ano_fim: int) -> html.Div:
    """KPI cards com sparklines embutidas."""

    idx_ultimo_mes = df_filtered.groupby(["ano", "instituicao"])["mes"].idxmax()
    df_acumulado = df_filtered.loc[idx_ultimo_mes]

    kpi_urgencias   = int(df_acumulado["total_urgencias"].sum())
    kpi_consultas   = int(df_acumulado["no_de_consultas_medicas_total"].sum())
    kpi_divida      = df_acumulado["divida_total_fornecedores_externos"].sum() / 1e6
    kpi_instituicoes = df_filtered["instituicao"].nunique()

    # Sparklines ───────────────────────────────────────────────────────────
    cumulative_cols = [
        "total_urgencias",
        "no_de_consultas_medicas_total",
        "divida_total_fornecedores_externos",
    ]

    spark_raw = (
        df_filtered
        .sort_values(["instituicao", "ano", "mes"])
        .copy()
    )

    for col in cumulative_cols:
        originais = spark_raw[col].copy()
        spark_raw[col] = (
            spark_raw
            .groupby(["instituicao", "ano"])[col]
            .diff()
            .fillna(originais)
        )

    spark_data = (
        spark_raw
        .groupby(["ano", "mes"])[cumulative_cols]
        .sum()
        .reset_index()
        .sort_values(["ano", "mes"])
    )
    spark_data["periodo"] = (
        spark_data["ano"].astype(str) + "-"
        + spark_data["mes"].astype(str).str.zfill(2)
    )

    fig_spark_urgencias = create_sparkline(spark_data["periodo"], spark_data["total_urgencias"], "#5c1b02")
    fig_spark_consultas = create_sparkline(spark_data["periodo"], spark_data["no_de_consultas_medicas_total"], "#3e91e4")
    fig_spark_divida    = create_sparkline(spark_data["periodo"], spark_data["divida_total_fornecedores_externos"], "#6e3088")

    # Layout ───────────────────────────────────────────────────────────────
    texto_instituicoes = html.Div(
        "Entidades ativas a reportar dados no período e filtros selecionados.",
        style={"color": "#7f8c8d", "fontSize": "0.85rem", "marginTop": "15px", "lineHeight": "1.4"},
    )

    return html.Div(
        className="kpi-row",
        children=[
            kpi_card(
                "Urgências Totais",
                f"{kpi_urgencias:,}".replace(",", " "),
                dcc.Graph(figure=fig_spark_urgencias, config={"displayModeBar": False, "staticPlot": True}),
            ),
            kpi_card(
                "Consultas Médicas",
                f"{kpi_consultas:,}".replace(",", " "),
                dcc.Graph(figure=fig_spark_consultas, config={"displayModeBar": False, "staticPlot": True}),
            ),
            kpi_card(
                "Dívida Total (M€)",
                f"{kpi_divida:,.0f}".replace(",", " "),
                dcc.Graph(figure=fig_spark_divida, config={"displayModeBar": False, "staticPlot": True}),
            ),
            kpi_card("Instituições", f"{kpi_instituicoes}", texto_instituicoes),
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

    if region and "all" not in region:
        if isinstance(region, str):
            region = [region]
        dff = dff[dff["regiao"].isin(region)]

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
        Input("dashboard-slider", "value"),
        Input("dashboard-region-filter", "value"),
        Input("dashboard-institution-filter", "value"),
        Input("dashboard-prof", "clickData"),
        Input("dashboard-prof", "relayoutData"),
    ],
)
def update_dashboard(year_range, selected_region, selected_institution, click_prof, relayout_prof):
    # Cross-filter reset (double-click / zoom reset) ──────────────────────
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

    # Year range sanitisation ─────────────────────────────────────────────
    if year_range is None:
        year_range = [int(min(ANOS)), int(max(ANOS))]

    ano_inicio, ano_fim = sorted(map(int, year_range))
    ano_inicio = max(int(min(ANOS)), ano_inicio)
    ano_fim = min(int(max(ANOS)), ano_fim)

    # Filter dataframe ────────────────────────────────────────────────────
    df_filtered = df[(df["ano"] >= ano_inicio) & (df["ano"] <= ano_fim)].copy()

    if not selected_region:
        selected_region = ["all"]
    if isinstance(selected_region, str):
        selected_region = [selected_region]
    if "all" not in selected_region:
        df_filtered = df_filtered[df_filtered["regiao"].isin(selected_region)]

    if selected_institution != "all":
        df_filtered = df_filtered[df_filtered["instituicao"] == selected_institution]

    # Build outputs ───────────────────────────────────────────────────────
    kpis          = build_kpis(df_filtered, ano_fim)
    fig_prof      = build_fig_profissionais(df_filtered, ano_inicio, ano_fim)
    fig_finance   = build_fig_gastos_rendimentos(df_filtered)
    fig_sun       = build_fig_sunburst(df_filtered)
    fig_parallel  = build_fig_parallel(df_filtered, click_prof)

    return kpis, fig_prof, fig_finance, fig_sun, fig_parallel, out_click, out_relayout