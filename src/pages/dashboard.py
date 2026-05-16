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
REGION_OPTIONS = [{"label": "Todas as regiões", "value": "all"}] + [{"label": r, "value": r} for r in REGIOES]

# Filter out anything that is not ULS or IPO
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
            style={
                "display": "flex",
                "gap": "1rem",
                "flexWrap": "wrap",
                "alignItems": "center",
            },
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
                            # REMOVIDO: allowCross=False (Isto é o que causa o bug de encravar)
                            updatemode="mouseup",
                            value=[
                                int(min(ANOS)),
                                int(max(ANOS)),
                            ],
                            marks={
                                int(ano): str(ano)
                                for ano in ANOS
                            },
                            tooltip={
                                "placement": "bottom"
                            },
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
# INSTITUTION FILTER CALLBACK
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

    options = [
        {"label": "Todas as instituições", "value": "all"}
    ] + [
        {
            "label": inst,
            "value": inst,
        }
        for inst in sorted(
            dff["instituicao"]
            .dropna()
            .unique()
        )
    ]

    return options, "all"

# ============================================================
# CALLBACK
# ============================================================
@callback(
    [
        Output("dashboard-kpis", "children"),
        Output("dashboard-finance", "figure"),
        Output("dashboard-pie", "figure"),
        Output("dashboard-prof", "figure"),
        Output("dashboard-radar", "figure"),
        Output("dashboard-prof", "clickData"),  # <--- Permite limpar o clique na interface
        Output("dashboard-prof", "relayoutData"),
    ],
    [
        Input("dashboard-slider", "value"),
        Input("dashboard-region-filter", "value"),
        Input("dashboard-institution-filter", "value"),
        Input("dashboard-prof", "clickData"),       # Clique simples
        Input("dashboard-prof", "relayoutData"),    # Deteta duplo clique
    ],
)
def update_dashboard(year_range, selected_region, selected_institution, click_prof, relayout_prof):

    # ========================================================
    # Cross-filtering Lógica de Reset (Duplo Clique)
    # ========================================================
    triggered_props = [t["prop_id"] for t in ctx.triggered] if ctx.triggered else []
    relayout_triggered = any("relayoutData" in prop for prop in triggered_props)

    out_click = no_update
    out_relayout = no_update

    # Se a ação foi "relayoutData" e tem "xaxis.autorange" (reset de zoom/duplo clique), limpa o clique e o relayout
    if relayout_triggered and relayout_prof and (
        "xaxis.autorange" in relayout_prof or "autosize" in relayout_prof
    ):
        click_prof = None
        out_click = None
        out_relayout = None


    if year_range is None:
        year_range = [int(min(ANOS)), int(max(ANOS))]
    elif isinstance(year_range, (int, float)):
        year_range = [int(year_range), int(year_range)]
    elif len(year_range) == 1:
        year_range = [int(year_range[0]), int(year_range[0])]

    ano_inicio = int(year_range[0])
    ano_fim = int(year_range[1])
    if ano_inicio > ano_fim:
        ano_inicio, ano_fim = ano_fim, ano_inicio

    ano_inicio = max(int(min(ANOS)), ano_inicio)
    ano_fim = min(int(max(ANOS)), ano_fim)

    df_filtered = df[
        (df["ano"] >= ano_inicio)
        & (df["ano"] <= ano_fim)
    ].copy()

    if not selected_region:
        selected_region = ["all"]
    
    if isinstance(selected_region, str):
        selected_region = [selected_region]

    if "all" not in selected_region:
        df_filtered = df_filtered[
            df_filtered["regiao"].isin(selected_region)
        ]

    if selected_institution != "all":
        df_filtered = df_filtered[
            df_filtered["instituicao"] == selected_institution
        ]

    # ========================================================
    # KPI
    # ========================================================
    idx_ultimo_mes = df_filtered.groupby(['ano', 'instituicao'])['mes'].idxmax()
    df_acumulado_final = df_filtered.loc[idx_ultimo_mes]

    anos_selecionados = ano_fim - ano_inicio + 1

    kpi_urgencias = int(
        df_acumulado_final["total_urgencias"].sum() 
    )

    kpi_consultas = int(
        df_acumulado_final["no_de_consultas_medicas_total"].sum()
    )

    kpi_divida = (
        df_acumulado_final[df_acumulado_final["ano"] == ano_fim]["divida_total_fornecedores_externos"].sum()
        / 1e6
    )

    kpi_instituicoes = df_filtered["instituicao"].nunique()

    # ========================================================
    # Bar Graph - Profissionais (Média Anual do Período Selecionado)
    # ========================================================
    staff_annual = (
        df_filtered[df_filtered["regiao"] != "Serviços Centrais"]
        .groupby(["regiao", "ano"]).agg(
            {
                "medicos_internos": "sum",
                "enfermeiros": "sum",
            }
        )
        .reset_index()
    )

    prof = (
        staff_annual
        .groupby("regiao")[
            ["medicos_internos", "enfermeiros"]
        ]
        .mean()
        .fillna(0)
    )
    prof["total_profissionais"] = prof["medicos_internos"] + prof["enfermeiros"]
    prof = prof.sort_values(by="total_profissionais", ascending=True).drop(columns=["total_profissionais"])

    fig_prof = go.Figure()

    fig_prof.add_bar(
        y=prof.index,
        x=prof["medicos_internos"],
        name="Médicos Internos",
        orientation="h",
        marker_color="#2e86de",
        hovertemplate="<b>%{y}</b><br>Média Anual de Médicos: %{x:,.0f}<extra></extra>"
    )

    fig_prof.add_bar(
        y=prof.index,
        x=prof["enfermeiros"],
        name="Enfermeiros",
        orientation="h",
        marker_color="#16a085",
        hovertemplate="<b>%{y}</b><br>Média Anual de Enfermeiros: %{x:,.0f}<extra></extra>"
    )

    titulo_prof = f"Profissionais por Região (Média {ano_inicio}-{ano_fim})" if ano_inicio != ano_fim else f"Profissionais por Região ({ano_inicio})"

    fig_prof.update_layout(
        barmode="stack",
        title=titulo_prof,
        height=360,
        margin=dict(l=80, r=20, t=50, b=40),
    )

    # ========================================================
    # Dumbbell - Gastos vs Rendimentos
    # ========================================================
    gastos_vs_rendimentos = (
        df_filtered[df_filtered["regiao"] != "Serviços Centrais"]
        .groupby("regiao")[
            [
                "gastos_operacionais",
                "rendimentos_operacionais",
            ]
        ].sum().fillna(0) / 1e6
    )

    gastos_vs_rendimentos = gastos_vs_rendimentos.sort_values(by="gastos_operacionais", ascending=True)

    fig_gastos_vs_rendimentos = go.Figure()

    for reg in gastos_vs_rendimentos.index:
        g = float(gastos_vs_rendimentos.loc[reg, "gastos_operacionais"])
        r = float(gastos_vs_rendimentos.loc[reg, "rendimentos_operacionais"])
        
        fig_gastos_vs_rendimentos.add_trace(
            go.Scatter(
                x=[g, r],
                y=[reg, reg],
                mode="lines",
                line=dict(color="#bdc3c7", width=3),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    fig_gastos_vs_rendimentos.add_trace(
        go.Scatter(
            x=gastos_vs_rendimentos["gastos_operacionais"],
            y=gastos_vs_rendimentos.index,
            mode="markers",
            name="Gastos",
            marker=dict(color="#e74c3c", size=12, line=dict(color="white", width=1)),
            hovertemplate="%{y}<br>Gastos: %{x:,.1f} M€<extra></extra>",
        )
    )

    fig_gastos_vs_rendimentos.add_trace(
        go.Scatter(
            x=gastos_vs_rendimentos["rendimentos_operacionais"],
            y=gastos_vs_rendimentos.index,
            mode="markers",
            name="Rendimentos",
            marker=dict(color="#27ae60", size=12, line=dict(color="white", width=1)),
            hovertemplate="%{y}<br>Rendimentos: %{x:,.1f} M€<extra></extra>",
        )
    )

    fig_gastos_vs_rendimentos.update_layout(
        title="Gastos vs Rendimentos por Região (M€)",
        xaxis=dict(title="M€", showgrid=True, gridcolor="lightgrey"),
        yaxis=dict(showgrid=True, gridcolor="whitesmoke"),
        height=360,
        margin=dict(l=80, r=20, t=50, b=40),
        plot_bgcolor="white"
    )

    # ========================================================
    # Sunburst - Distribuição de Gastos Operacionais
    # ========================================================
    sun_df = (
        df_filtered[df_filtered["regiao"] != "Serviços Centrais"]
        .loc[~df_filtered["tipo_instituicao"].astype(str).str.contains("Serviços Centrais", case=False, na=False)]
        .groupby(["regiao", "tipo_instituicao"])["gastos_operacionais"]
        .sum()
        .reset_index()
    )
    sun_df["Total"] = "SNS Total"

    fig_pie = px.sunburst(
        sun_df,
        path=["Total", "regiao", "tipo_instituicao"],
        values="gastos_operacionais",
        color="regiao",
        title="Distribuição de Gastos Operacionais",
    )

    fig_pie.update_traces(textinfo="label+percent parent", insidetextorientation="radial")
    fig_pie.update_layout(
        uirevision="sunburst_lock",  # Tranca o estado visual
        autosize=False,              # Desliga o recálculo automático que esmaga o gráfico
        title={
            "text": "Distribuição de Gastos Operacionais",
            "x": 0.5,
            "xanchor": "center",
            "y": 0.95,
            "yanchor": "top",
        },
        margin=dict(t=70, l=10, r=10, b=10),
        height=520,
    )

    # ========================================================
    # Parallel Coordinates - Padrões de Atividade Assistencial por Instituição
    # ========================================================
    df_filtered["total_cirurgias"] = (
        df_filtered[
            [
                "no_intervencoes_cirurgicas_programadas",
                "no_intervencoes_cirurgicas_convencionais",
                "no_intervencoes_cirurgicas_urgentes",
            ]
        ].sum(axis=1)
    )

    pc_df = (
        df_filtered[df_filtered["regiao"] != "Serviços Centrais"]
        .groupby(["instituicao", "regiao"])[
            [
                "total_urgencias",
                "total_cirurgias",
                "no_de_consultas_medicas_total",
            ]
        ]
        .sum()
        .reset_index()
    )

    # Obter a região que foi clicada no gráfico de profissionais
    highlight_region = None
    if click_prof:
        # Pelo facto de o gráfico de profissionais ser orientation="h", o nome da região está no "y"
        highlight_region = click_prof["points"][0]["y"]

    regioes_unicas = pc_df["regiao"].unique().tolist()
    
    if highlight_region and highlight_region in regioes_unicas:
        # Se há uma região destacada
        pc_df["regiao_id"] = pc_df["regiao"].apply(lambda x: 1 if x == highlight_region else 0)
        colorscale = [[0, "#ecf0f1"], [1, "#2e86de"]]  # 0 = Cinza, 1 = Azul
        cmax = 1
        colorbar_dict = dict(title="Região", tickmode="array", tickvals=[0, 1], ticktext=["Outras", highlight_region])
    else:
        # Sem seleção (Comportamento normal)
        pc_df["regiao_id"] = pc_df["regiao"].apply(lambda x: regioes_unicas.index(x))
        colorscale = px.colors.qualitative.Bold
        cmax = max(0, len(regioes_unicas) - 1)
        colorbar_dict = dict(title="Região", tickmode="array", tickvals=list(range(len(regioes_unicas))), ticktext=regioes_unicas)

    fig_radar = go.Figure(data=go.Parcoords(
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

    fig_radar.update_layout(
        title={
            "text": "Padrões de Atividade Assistencial por Instituição",
            "x": 0.5,
            "xanchor": "center",
            "y": 0.95,
            "yanchor": "top",
        },
        autosize=True,
        height=520,
        margin=dict(l=60, r=40, t=90, b=40)
    )

    # ==================================================
    # Sparklines Creation
    # ==================================================
    spark_data = (
        df_filtered
        .groupby(["ano", "mes"])[
            [
                "gastos_operacionais",
                "rendimentos_operacionais",
                "total_urgencias",
                "no_de_consultas_medicas_total",
                "divida_total_fornecedores_externos",
            ]
        ]
        .sum()
        .reset_index()
    )
    
    spark_data = spark_data.sort_values(by=["ano", "mes"])
    spark_data["periodo"] = spark_data["ano"].astype(str) + "-" + spark_data["mes"].astype(str).str.zfill(2)

    for col in [
        "total_urgencias",
        "no_de_consultas_medicas_total",
        "divida_total_fornecedores_externos",
    ]:
        # 1. Guarda os valores acumulados originais
        valores_originais = spark_data[col].copy()
        
        # 2. Faz a diferença mensal
        spark_data[col] = spark_data.groupby("ano")[col].diff()
        
        # 3. Onde o diff gerou NaN (que corresponde sempre ao 1º mês, janeiro),
        # usamos o valor acumulado original (que é efetivamente o valor apenas de janeiro)
        spark_data[col] = spark_data[col].fillna(valores_originais)

    fig_spark_urgencias = create_sparkline(spark_data["periodo"], spark_data["total_urgencias"], "#5c1b02")
    fig_spark_consultas = create_sparkline(spark_data["periodo"], spark_data["no_de_consultas_medicas_total"], "#3e91e4")
    fig_spark_divida = create_sparkline(spark_data["periodo"], spark_data["divida_total_fornecedores_externos"], "#6e3088")

    # ==================================================
    # Build KPI cards embedding sparklines
    # ==================================================
    texto_instituicoes = html.Div(
        "Entidades ativas a reportar dados no período e filtros selecionados.", 
        style={"color": "#7f8c8d", "fontSize": "0.85rem", "marginTop": "15px", "lineHeight": "1.4"}
    )
    
    kpis = html.Div(
        className="kpi-row",
        children=[
            kpi_card(
                "Urgências Totais", 
                f"{kpi_urgencias:,}".replace(",", " "), 
                dcc.Graph(figure=fig_spark_urgencias, config={"displayModeBar": False, "staticPlot": True})
            ),
            kpi_card(
                "Consultas Médicas", 
                f"{kpi_consultas:,}".replace(",", " "), 
                dcc.Graph(figure=fig_spark_consultas, config={"displayModeBar": False, "staticPlot": True})
            ),
            kpi_card(
                "Dívida Total (M€)", 
                f"{kpi_divida:,.0f}".replace(",", " "), 
                dcc.Graph(figure=fig_spark_divida, config={"displayModeBar": False, "staticPlot": True})
            ),
            kpi_card(
                "Instituições", 
                f"{kpi_instituicoes}", 
                texto_instituicoes
            ),
        ],
    )

    return (kpis, fig_gastos_vs_rendimentos, fig_pie, fig_prof, fig_radar, out_click, out_relayout)