from dash import html, dcc, callback, Input, Output, ctx, no_update
from pages.pages_helper import load_data, process_data, create_sparkline, kpi_card, carregar_e_processar_dados, aplicar_config_padrao
import pandas as pd
import plotly.graph_objects as go

# ============================================================
# DATA LOAD
# ============================================================
try:
    df = carregar_e_processar_dados("data/processed/contas_sns.csv")
    assert not df.empty, "Dataset vazio após carregamento"
except Exception as e:
    print(f"❌ Erro ao carregar dados: {e}")
    df = pd.DataFrame()

# ============================================================
# CRIAR A TIMELINE ANTES DO LAYOUT
# ============================================================
fig_timeline_estatica = go.Figure()
fig_timeline_estatica.add_trace(go.Scatter(
    x=df["tempo"], y=df["execucao_acumulada_receita_efectiva"],
    name="Receita (Acumulada)", line=dict(color="#27ae60", width=2), fill="tozeroy",
    fillcolor="rgba(39,174,96,0.1)"
))
fig_timeline_estatica.add_trace(go.Scatter(
    x=df["tempo"], y=df["execucao_acumulada_despesa_efectiva"],
    name="Despesa (Acumulada)", line=dict(color="#e74c3c", width=2)
))
fig_timeline_estatica.update_layout(
    title=dict(
        text="Evolução Receita vs Despesa (M€)<br><sup>Use o slider inferior para selecionar os meses</sup>",
        font=dict(size=16)
    ),
    xaxis=dict(rangeslider=dict(visible=True), type="date"),
    yaxis=dict(title="M€"),
    legend=dict(orientation="h", y=1),
    margin=dict(l=20, r=20, t=80, b=40),
    height=340,
)

# ============================================================
# HEATMAP DE SAZONALIDADE
# ============================================================
pivot_sazonalidade = df.pivot_table(
    index="ano", 
    columns="mes", 
    values="mensal_despesa_efectiva", 
    aggfunc="sum"
)

nomes_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

fig_heatmap = go.Figure(data=go.Heatmap(
    z=pivot_sazonalidade.values,
    x=nomes_meses,
    y=pivot_sazonalidade.index,
    colorscale="Reds",
    hoverongaps=False,
    hovertemplate="Ano: %{y}<br>Mês: %{x}<br>Despesa: %{z:,.1f} M€<extra></extra>"
))

fig_heatmap.update_layout(
    title="Sazonalidade da Despesa (Mapa de Calor)",
    xaxis=dict(title="Mês", tickmode="array", tickvals=list(range(12)), ticktext=nomes_meses),
    yaxis=dict(title="Ano", type="category"),
    margin=dict(l=20, r=20, t=50, b=20),
    height=320,
)

# ============================================================
# LAYOUT
# ============================================================
layout = html.Div(
    className="content",
    children=[
        html.H2("Contas SNS"),
        html.P("Análise do orçamento e execução do Serviço Nacional de Saúde"),

        dcc.Store(id="store-range-contas"),

        html.Div(id="kpi-row-contas", className="kpi-row"),

        html.Div(
            className="grid-2x2",
            children=[
                html.Div(className="card", children=[dcc.Graph(id="fig-waterfall")]),
                html.Div(className="card", children=[dcc.Graph(id="fig-timeline", figure=fig_timeline_estatica)]),
            ],
        ),
        
        html.Div(className="card", children=[dcc.Graph(id="fig-despesa-mensal")]),
        
        html.Div(className="card", children=[dcc.Graph(id="fig-orcamento-execucao")]),

        html.Div(className="card", children=[dcc.Graph(id="fig-heatmap", figure=fig_heatmap)]),
    ],
)

# ============================================================
# CALLBACK 1 — Guarda o range do slider no Store
# ============================================================
@callback(
    Output("store-range-contas", "data"),
    Input("fig-timeline", "relayoutData")
)
def guardar_range(relayoutData):
    if not relayoutData:
        return {}

    if "xaxis.range[0]" in relayoutData:
        return {
            "start": relayoutData["xaxis.range[0]"],
            "end":   relayoutData["xaxis.range[1]"],
        }
    
    if "xaxis.range" in relayoutData:
        return {
            "start": relayoutData["xaxis.range"][0],
            "end":   relayoutData["xaxis.range"][1],
        }

    if "xaxis.autorange" in relayoutData:
        return {}

    return {}


# ============================================================
# CALLBACK 2 — Atualiza o dashboard com base no Store e Cliques
# ============================================================
@callback(
    Output("kpi-row-contas",         "children"),
    Output("fig-orcamento-execucao", "figure"),
    Output("fig-despesa-mensal",     "figure"),
    Output("fig-waterfall",          "figure"),
    Output("fig-orcamento-execucao", "clickData"),
    Output("fig-orcamento-execucao", "relayoutData"), # <--- 1. NOVO OUTPUT AQUI!
    Input("store-range-contas",      "data"),
    Input("fig-orcamento-execucao",  "clickData"),
    Input("fig-orcamento-execucao",  "relayoutData")
)
def update_dashboard(range_data, click_orcamento, relayout_orcamento):
    
    # ----------------------------------------------------------
    # LÓGICA DE RESET VIA DUPLO CLIQUE
    # ----------------------------------------------------------
    out_click = no_update
    out_relayout = no_update # <--- 2. NOVA VARIÁVEL PARA PROTEGER O RELAYOUT
    categoria_clicada = None
    
    trigger_prop = ctx.triggered[0]["prop_id"] if ctx.triggered else ""

    # Se a ação foi o duplo clique (autorange)
    if "relayoutData" in trigger_prop and relayout_orcamento and "xaxis.autorange" in relayout_orcamento:
        out_click = None         # Apagamos o clique
        out_relayout = None      # <--- 3. APAGAMOS O RELAYOUT (para o próximo duplo clique funcionar!)
        categoria_clicada = None
    else:
        # Se foi um clique normal
        if click_orcamento:
            categoria_clicada = click_orcamento["points"][0]["x"]

    # ----------------------------------------------------------
    # DADOS E FILTRO TEMPORAL
    # ----------------------------------------------------------
    dff = df.copy()

    if range_data and "start" in range_data:
        start_date = pd.to_datetime(range_data["start"])
        end_date   = pd.to_datetime(range_data["end"])
        dff = dff[
            (dff["tempo"] >= start_date) &
            (dff["tempo"] <= end_date)
        ]

    last = dff.iloc[-1] if not dff.empty else df.iloc[-1]

    # ----------------------------------------------------------
    # KPIs
    # ----------------------------------------------------------
    total_receita = dff["mensal_receita_efectiva"].sum()
    total_despesa = dff["mensal_despesa_efectiva"].sum()
    saldo_global  = total_receita - total_despesa
    num_periodos  = dff["tempo"].nunique()

    saldo_mensal = dff["mensal_receita_efectiva"] - dff["mensal_despesa_efectiva"]
    cor_saldo = "#e74c3c" if saldo_global < 0 else "#27ae60"

    spark_receita = create_sparkline(dff["tempo"], dff["mensal_receita_efectiva"], "#27ae60")
    spark_despesa = create_sparkline(dff["tempo"], dff["mensal_despesa_efectiva"], "#e74c3c")
    spark_saldo   = create_sparkline(dff["tempo"], saldo_mensal, cor_saldo)

    kpis = [
        html.Div([
            html.Div("Receita do Período", className="kpi-title"),
            html.Div(f"{total_receita:,.1f} M€", className="kpi-value"),
            dcc.Graph(figure=spark_receita, config={'displayModeBar': False})
        ], className="kpi-card"),
        
        html.Div([
            html.Div("Despesa do Período", className="kpi-title"),
            html.Div(f"{total_despesa:,.1f} M€", className="kpi-value"),
            dcc.Graph(figure=spark_despesa, config={'displayModeBar': False})
        ], className="kpi-card"),
        
        html.Div([
            html.Div("Saldo Global", className="kpi-title"),
            html.Div(f"{saldo_global:,.1f} M€", className="kpi-value", style={"color": cor_saldo}),
            dcc.Graph(figure=spark_saldo, config={'displayModeBar': False})
        ], className="kpi-card"),
        
        html.Div([
            html.Div("Períodos Analisados", className="kpi-title"),
            html.Div(f"{num_periodos}", className="kpi-value"),
            html.Div("Meses selecionados", className="kpi-subtitle", style={"marginTop": "10px"}),
        ], className="kpi-card"),
    ]

    # ----------------------------------------------------------
    # ORÇAMENTO VS EXECUÇÃO
    # ----------------------------------------------------------
    categorias = {
        "Pessoal":             ("orcamento_despesas_com_o_pessoal",       "mensal_despesas_com_o_pessoal"),
        "Bens e Serviços":     ("orcamento_aquisicao_de_bens_e_servicos", "mensal_aquisicao_de_bens_e_servicos"),
        "Transferências":      ("orcamento_transferencias_correntes",     "mensal_transferencias_correntes"),
        "Investimento":        ("orcamento_investimentos",                "mensal_investimentos"),
        "Outras Correntes":    ("orcamento_outras_despesas_correntes",    "mensal_outras_despesas_correntes"),
    }

    nomes = list(categorias.keys())
    orc_vals = [last[v[0]] for v in categorias.values()]
    exe_vals = [dff[v[1]].sum() for v in categorias.values()]

    fig_oc = go.Figure()
    fig_oc.add_trace(go.Bar(
        name="Orçamento (Ano todo)", x=nomes, y=orc_vals,
        marker_color="rgba(52,152,219,0.6)",
        marker_line=dict(color="rgba(52,152,219,1)", width=1.5),
        text=[f"{v:,.1f}" for v in orc_vals],
        textposition='outside'
    ))
    fig_oc.add_trace(go.Bar(
        name="Execução (Período sel.)", x=nomes, y=exe_vals,
        marker_color="rgba(231,76,60,0.8)",
        text=[f"{v:,.1f}" for v in exe_vals],
        textposition='outside'
    ))
    fig_oc.update_layout(
        title=dict(
            text="Orçamento Anual vs Execução no Período por Categoria (M€)",
            x=0.5,
            xanchor="center",
            y=0.95,
            yanchor="top",
        ),
        barmode="group",
        yaxis=dict(title="M€", automargin=True),
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=20, r=20, t=100, b=20),
        height=360,
    )

    # ----------------------------------------------------------
    # DESPESA MENSAL COM CROSS-FILTERING (Ajustado)
    # ----------------------------------------------------------
    fig_mensal = go.Figure()
    
    # Substituímos a verificação aqui para usar a variável segura que criámos lá em cima
    if not categoria_clicada:
        fig_mensal.add_trace(go.Bar(
            x=dff["tempo"], y=dff["mensal_receita_efectiva"],
            name="Receita Mensal", marker_color="#27ae60"
        ))
        fig_mensal.add_trace(go.Bar(
            x=dff["tempo"], y=dff["mensal_despesa_efectiva"],
            name="Despesa Mensal Total", marker_color="#e74c3c"
        ))
        titulo_mensal = "Receita e Despesa Mensal Total (M€)<br><sup>Clique numa categoria no gráfico de Orçamento para filtrar</sup>"
    
    else:
        coluna_mensal = categorias[categoria_clicada][1] 
        fig_mensal.add_trace(go.Bar(
            x=dff["tempo"], y=dff[coluna_mensal],
            name=categoria_clicada, marker_color="#3498db" 
        ))
        titulo_mensal = f"Evolução Mensal da Despesa: <b>{categoria_clicada}</b> (M€)<br><sup>Faça duplo clique no gráfico de orçamento para limpar o filtro</sup>"

    fig_mensal.update_layout(
        title=dict(
            text=titulo_mensal,
            x=0.5,
            xanchor="center",
            y=0.95,
            yanchor="top",
        ),
        barmode="group",
        yaxis=dict(title="M€", automargin=True),
        legend=dict(orientation="h", y=1.15),
        margin=dict(l=20, r=20, t=70, b=20),
        height=360,
    )

    # ----------------------------------------------------------
    # WATERFALL 
    # ----------------------------------------------------------
    pessoal      = dff["mensal_despesas_com_o_pessoal"].sum()
    bens_serv    = dff["mensal_aquisicao_de_bens_e_servicos"].sum()
    transferenc  = dff["mensal_transferencias_correntes"].sum()
    investimento = dff["mensal_investimentos"].sum()
    outras       = max(total_despesa - pessoal - bens_serv - transferenc - investimento, 0)

    fig_waterfall = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "relative", "relative", "total"],
        x=["Receita", "Pessoal", "Bens & Serv.", "Transferências", "Investimento", "Outras", "Saldo Final"],
        textposition="outside",
        text=[f"{total_receita:,.0f}", f"-{pessoal:,.0f}", f"-{bens_serv:,.0f}", f"-{transferenc:,.0f}", f"-{investimento:,.0f}", f"-{outras:,.0f}", f"{saldo_global:,.0f}"],
        y=[total_receita, -pessoal, -bens_serv, -transferenc, -investimento, -outras, saldo_global],
        connector={"line":{"color":"rgb(63, 63, 63)"}},
        decreasing={"marker":{"color":"#e74c3c"}},
        increasing={"marker":{"color":"#27ae60"}},
        totals={"marker":{"color":"#2c3e50" if saldo_global >= 0 else "#c0392b"}}
    ))
    
    fig_waterfall.update_layout(
        title="Cascata Financeira: Da Receita ao Saldo (M€)",
        margin=dict(l=20, r=20, t=50, b=20),
        height=320,
        showlegend=False
    )

    return kpis, fig_oc, fig_mensal, fig_waterfall, out_click, out_relayout # <--- 4. NOVO RETURN