from dash import html, dcc, callback, Input, Output
import pandas as pd
import plotly.graph_objects as go

# ============================================================
# DATA LOAD & TRANSFORMAÇÃO
# ============================================================
df = pd.read_csv("data/processed/contas_sns.csv")
df["ano"] = df["ano"].astype(int)


# 1. Converter tempo para datetime verdadeiro (resolve bugs de comparação no slider)
df["tempo"] = pd.to_datetime(df["tempo"])
df = df.sort_values("tempo").reset_index(drop=True)
df["mes"] = df["tempo"].dt.month
# 2. Desacumular os dados (calcular o valor gasto ESPECIFICAMENTE em cada mês)
colunas_para_desacumular = [
    "execucao_acumulada_receita_efectiva",
    "execucao_acumulada_despesa_efectiva",
    "execucao_acumulada_despesas_com_o_pessoal",
    "execucao_acumulada_aquisicao_de_bens_e_servicos",
    "execucao_acumulada_transferencias_correntes",
    "execucao_acumulada_investimentos",
    "execucao_acumulada_outras_despesas_correntes"
]

for col in colunas_para_desacumular:
    # Cria uma nova coluna substituindo "execucao_acumulada_" por "mensal_"
    nova_col = col.replace("execucao_acumulada_", "mensal_")
    # Calcula a diferença para o mês anterior dentro do mesmo ano
    df[nova_col] = df.groupby(df["tempo"].dt.year)[col].diff().fillna(df[col])

# ============================================================
# FUNÇÃO PARA CRIAR SPARKLINES NOS KPIS
# ============================================================
def criar_sparkline(x_data, y_data, cor):
    fig = go.Figure(go.Scatter(
        x=x_data, y=y_data, 
        mode="lines", 
        line=dict(color=cor, width=2.5),
        hoverinfo="skip" # Desativa o hover para não atrapalhar no KPI
    ))
    
    fig.update_layout(
        margin=dict(l=0, r=0, t=5, b=5), # Margens quase a zero
        height=40,                       # Altura minúscula
        paper_bgcolor="rgba(0,0,0,0)",   # Fundo transparente
        plot_bgcolor="rgba(0,0,0,0)",    # Fundo transparente
        xaxis=dict(visible=False),       # Esconder eixo X
        yaxis=dict(visible=False),       # Esconder eixo Y
        showlegend=False
    )
    return fig

# ============================================================
# CRIAR A TIMELINE ANTES DO LAYOUT (Evita os glitches do slider)
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
        font=dict(size=16) # Podes diminuir este valor se ainda achares grande
    ),
    xaxis=dict(rangeslider=dict(visible=True), type="date"),
    yaxis=dict(title="M€"),
    legend=dict(orientation="h", y=1), # Subi a legenda um bocadinho (de 1.1 para 1.15)
    margin=dict(l=20, r=20, t=80, b=40),  # <--- Aumentámos o Topo (t) para 80 e a Base (b) para 40
    height=340,                           # Aumentei ligeiramente a altura geral para compensar as margens maiores
)

# ============================================================
# HEATMAP DE SAZONALIDADE
# ============================================================
# Criar uma matriz (pivot table): Anos nas linhas, Meses nas colunas
pivot_sazonalidade = df.pivot_table(
    index="ano", 
    columns="mes", 
    values="mensal_despesa_efectiva", 
    aggfunc="sum"
)

# Nomes dos meses para o eixo X
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
    yaxis=dict(title="Ano", type="category"), # Forçar o ano a ser texto para não aparecer "2,020"
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

        # Store para passar o range selecionado sem dependência circular
        dcc.Store(id="store-range-contas"),

        html.Div(id="kpi-row-contas", className="kpi-row"),

        # 1. Os dois gráficos em cima (Grelha Waterfall + Timeline)
        html.Div(
            className="grid-2x2",
            children=[
                html.Div(className="card", children=[dcc.Graph(id="fig-waterfall")]),
                html.Div(className="card", children=[dcc.Graph(id="fig-timeline", figure=fig_timeline_estatica)]),
            ],
        ),
        
        # 2. O gráfico de barras que já estava no meio
        html.Div(className="card", children=[dcc.Graph(id="fig-despesa-mensal")]),
        
        # 3. O gráfico que estava em cima passa para baixo
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

    # 1. Seleção no gráfico principal (Zoom box)
    if "xaxis.range[0]" in relayoutData:
        return {
            "start": relayoutData["xaxis.range[0]"],
            "end":   relayoutData["xaxis.range[1]"],
        }
    
    # 2. Uso do Range Slider inferior
    if "xaxis.range" in relayoutData:
        return {
            "start": relayoutData["xaxis.range"][0],
            "end":   relayoutData["xaxis.range"][1],
        }

    # 3. Duplo clique no gráfico para limpar os filtros (autorange)
    if "xaxis.autorange" in relayoutData:
        return {}

    return {}


# ============================================================
# CALLBACK 2 — Atualiza o dashboard com base no Store
# ============================================================
@callback(
    Output("kpi-row-contas",         "children"),
    Output("fig-orcamento-execucao", "figure"),
    Output("fig-despesa-mensal",     "figure"),
    Output("fig-waterfall",          "figure"), # Alterado de sankey
    Input("store-range-contas",      "data"),
    Input("fig-orcamento-execucao",  "clickData"), # <--- NOVO INPUT!
)
def update_dashboard(range_data, click_orcamento): # <--- NOVO ARGUMENTO
    dff = df.copy()

    if range_data and "start" in range_data:
        start_date = pd.to_datetime(range_data["start"])
        end_date   = pd.to_datetime(range_data["end"])
        dff = dff[
            (dff["tempo"] >= start_date) &
            (dff["tempo"] <= end_date)
        ]

    # Usamos o último registo apenas para as métricas anuais fixas (Orçamento)
    last = dff.iloc[-1] if not dff.empty else df.iloc[-1]

    # ----------------------------------------------------------
    # KPIs (Agora com Sparklines!)
    # ----------------------------------------------------------
    total_receita = dff["mensal_receita_efectiva"].sum()
    total_despesa = dff["mensal_despesa_efectiva"].sum()
    saldo_global  = total_receita - total_despesa
    num_periodos  = dff["tempo"].nunique()

    # Calcular o saldo mensal para a linha do terceiro KPI
    saldo_mensal = dff["mensal_receita_efectiva"] - dff["mensal_despesa_efectiva"]

    cor_saldo = "#e74c3c" if saldo_global < 0 else "#27ae60"

    # Criar os gráficos pequeninos
    spark_receita = criar_sparkline(dff["tempo"], dff["mensal_receita_efectiva"], "#27ae60")
    spark_despesa = criar_sparkline(dff["tempo"], dff["mensal_despesa_efectiva"], "#e74c3c")
    spark_saldo   = criar_sparkline(dff["tempo"], saldo_mensal, cor_saldo)

    # Inserir o dcc.Graph dentro de cada Div (com displayModeBar=False para esconder o menu do Plotly)
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
    # ORÇAMENTO VS EXECUÇÃO (Agora reage perfeitamente ao slider)
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
        title="Orçamento Anual vs Execução no Período por Categoria (M€)",
        barmode="group",
        yaxis=dict(title="M€"),
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=20, r=20, t=70, b=20), # Margem de topo aumentada por causa dos textos 'outside'
        height=320,
    )

    # ----------------------------------------------------------
    # DESPESA MENSAL COM CROSS-FILTERING
    # ----------------------------------------------------------
    fig_mensal = go.Figure()
    
    # 1. Verificar se alguém clicou numa barra
    categoria_clicada = None
    if click_orcamento:
        categoria_clicada = click_orcamento["points"][0]["x"] # Apanha o nome (ex: "Pessoal")

    # 2. Se não clicou em nada (ou clicou no vazio), mostra o gráfico original (Receita vs Despesa Total)
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
    
    # 3. Se clicou numa categoria específica, mostra apenas essa linha
    else:
        # Procurar o nome da coluna no nosso dicionário 'categorias' (que já existe no teu código)
        coluna_mensal = categorias[categoria_clicada][1] 
        
        fig_mensal.add_trace(go.Bar(
            x=dff["tempo"], y=dff[coluna_mensal],
            name=categoria_clicada, marker_color="#3498db" # Azul para realçar que está filtrado
        ))
        titulo_mensal = f"Evolução Mensal da Despesa: <b>{categoria_clicada}</b> (M€)<br><sup>Faça duplo clique no gráfico de orçamento para limpar o filtro</sup>"

    fig_mensal.update_layout(
        title=titulo_mensal,
        barmode="group",
        yaxis=dict(title="M€"),
        legend=dict(orientation="h", y=1.15),
        margin=dict(l=20, r=20, t=80, b=20),
        height=320,
    )

    # ----------------------------------------------------------
    # WATERFALL (Substitui o Sankey)
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

    return kpis, fig_oc, fig_mensal, fig_waterfall