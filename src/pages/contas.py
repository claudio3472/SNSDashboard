from dash import html, dcc, callback, Input, Output, ctx, no_update
from pages.pages_helper import load_data, process_data, create_sparkline, kpi_card, carregar_e_processar_dados, aplicar_config_padrao, formatar_numero
import pandas as pd
import plotly.graph_objects as go

# ============================================================
# CONSTANTES E CONFIGURAÇÕES
# ============================================================

CATEGORIAS_ORCAMENTO = {
    "Pessoal":          ("orcamento_despesas_com_o_pessoal",       "mensal_despesas_com_o_pessoal"),
    "Bens e Serviços":  ("orcamento_aquisicao_de_bens_e_servicos", "mensal_aquisicao_de_bens_e_servicos"),
    "Transferências":   ("orcamento_transferencias_correntes",     "mensal_transferencias_correntes"),
    "Investimento":     ("orcamento_investimentos",                "mensal_investimentos"),
    "Outras Correntes": ("orcamento_outras_despesas_correntes",    "mensal_outras_despesas_correntes"),
}

MESES_NOMES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


# ============================================================
# DATA LOAD
# ============================================================

df_global = carregar_e_processar_dados("data/processed/contas_sns.csv")


# ============================================================
# CHART BUILDERS
# ============================================================

def build_timeline_figure(df):
    if df.empty: return go.Figure()
    
    txt_receita = [formatar_numero(v) for v in df["execucao_acumulada_receita_efectiva"]]
    txt_despesa = [formatar_numero(v) for v in df["execucao_acumulada_despesa_efectiva"]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["tempo"], y=df["execucao_acumulada_receita_efectiva"],
        name="Receita (Acumulada)", line=dict(color="#27ae60", width=2), fill="tozeroy",
        fillcolor="rgba(39,174,96,0.1)",
        text=txt_receita, hovertemplate="%{text} M€<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=df["tempo"], y=df["execucao_acumulada_despesa_efectiva"],
        name="Despesa (Acumulada)", line=dict(color="#e74c3c", width=2),
        text=txt_despesa, hovertemplate="%{text} M€<extra></extra>"
    ))
    fig.update_layout(
        title=dict(
            text="Evolução Receita vs Despesa (M€)<br><sup>Use o slider inferior para selecionar os meses</sup>",
            x=0.5, xanchor="center", y=0.95, yanchor="top",
            font=dict(size=16)
        ),
        xaxis=dict(rangeslider=dict(visible=True), type="date"),
        yaxis=dict(title="M€"),
        legend=dict(orientation="h", y=1),
        margin=dict(l=20, r=20, t=80, b=40),
        height=340,
    )
    return fig


def build_heatmap_figure(df):
    if df.empty: return go.Figure()
    
    pivot = df.pivot_table(index="ano", columns="mes", values="mensal_despesa_efectiva", aggfunc="sum")
    
    text_matrix = [[formatar_numero(val) for val in row] for row in pivot.values]
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=MESES_NOMES,
        y=pivot.index,
        text=text_matrix,
        colorscale="Reds",
        hoverongaps=False,
        hovertemplate="Ano: %{y}<br>Mês: %{x}<br>Despesa Mensal: %{text} M€<extra></extra>"
    ))
    
    fig.update_layout(
        title=dict(text="Sazonalidade da Despesa", x=0.5, xanchor="center", y=0.95, yanchor="top"),
        xaxis=dict(title="Mês", tickmode="array", tickvals=list(range(12)), ticktext=MESES_NOMES),
        yaxis=dict(title="Ano", type="category"),
        margin=dict(l=20, r=20, t=70, b=20),
        height=320,
    )
    return fig


def build_waterfall_figure(dff, total_receita, total_despesa, saldo_global):
    pessoal      = dff["mensal_despesas_com_o_pessoal"].sum()
    bens_serv    = dff["mensal_aquisicao_de_bens_e_servicos"].sum()
    transferenc  = dff["mensal_transferencias_correntes"].sum()
    investimento = dff["mensal_investimentos"].sum()
    outras       = max(total_despesa - pessoal - bens_serv - transferenc - investimento, 0)

    text_vals = [
        formatar_numero(total_receita), 
        f"-{formatar_numero(pessoal)}", 
        f"-{formatar_numero(bens_serv)}", 
        f"-{formatar_numero(transferenc)}", 
        f"-{formatar_numero(investimento)}", 
        f"-{formatar_numero(outras)}", 
        formatar_numero(saldo_global)
    ]

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "relative", "relative", "total"],
        x=["Receita", "Pessoal", "Bens & Serv.", "Transferências", "Investimento", "Outras", "Saldo Final"],
        textposition="outside",
        text=text_vals,
        y=[total_receita, -pessoal, -bens_serv, -transferenc, -investimento, -outras, saldo_global],
        connector={"line":{"color":"rgb(63, 63, 63)"}},
        decreasing={"marker":{"color":"#e74c3c"}},
        increasing={"marker":{"color":"#27ae60"}},
        totals={"marker":{"color":"#2c3e50" if saldo_global >= 0 else "#c0392b"}},
        hovertemplate="%{x}<br>Valor: %{text} M€<extra></extra>"
    ))
    fig.update_layout(
        title=dict(text="Cascata Financeira: Da Receita ao Saldo (M€)", x=0.5, xanchor="center", y=0.95, yanchor="top"),
        margin=dict(l=20, r=20, t=70, b=20),
        height=320,
        showlegend=False
    )
    return fig


def build_orcamento_execucao_figure(dff):
    if dff.empty: return go.Figure()
    
    nomes = list(CATEGORIAS_ORCAMENTO.keys())
    orc_vals = []
    exe_vals = []

    for col_orc, col_exe in CATEGORIAS_ORCAMENTO.values():
        
        orc_total_acumulado = 0
        for ano in dff["ano"].unique():
            dff_ano = dff[dff["ano"] == ano]
            
            num_meses_ano = dff_ano["mes"].nunique()
            
            orc_anual_deste_ano = dff_ano[col_orc].iloc[-1]
            
            orc_total_acumulado += (orc_anual_deste_ano / 12) * num_meses_ano
            
        orc_vals.append(orc_total_acumulado)
        
        exe_vals.append(dff[col_exe].sum())

    txt_orc = [formatar_numero(v) for v in orc_vals]
    txt_exe = [formatar_numero(v) for v in exe_vals]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Orçamento (Período sel.)", x=nomes, y=orc_vals,
        marker_color="rgba(52,152,219,0.6)",
        marker_line=dict(color="rgba(52,152,219,1)", width=1.5),
        text=txt_orc, textposition='outside', hovertemplate="%{text} M€<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        name="Execução (Período sel.)", x=nomes, y=exe_vals,
        marker_color="rgba(231,76,60,0.8)",
        text=txt_exe, textposition='outside', hovertemplate="%{text} M€<extra></extra>"
    ))
    fig.update_layout(
        title=dict(text="Orçamento vs Execução no Período por Categoria (M€)", x=0.5, xanchor="center", y=0.95, yanchor="top"),
        barmode="group",
        yaxis=dict(title="M€", automargin=True),
        legend=dict(orientation="h", y=1.2, x=0.5, xanchor="center"),
        margin=dict(l=20, r=20, t=120, b=20),
        height=360,
    )
    return fig


def build_mensal_figure(dff, categoria_clicada):
    fig = go.Figure()
    
    if not categoria_clicada:
        txt_rec = [formatar_numero(v) for v in dff["mensal_receita_efectiva"]]
        txt_desp = [formatar_numero(v) for v in dff["mensal_despesa_efectiva"]]

        fig.add_trace(go.Bar(
            x=dff["tempo"], y=dff["mensal_receita_efectiva"],
            name="Receita Mensal", marker_color="#27ae60",
            text=txt_rec, 
            textposition="none",
            hovertemplate="%{text} M€<extra></extra>"
        ))
        fig.add_trace(go.Bar(
            x=dff["tempo"], y=dff["mensal_despesa_efectiva"],
            name="Despesa Mensal Total", marker_color="#e74c3c",
            text=txt_desp, 
            textposition="none",
            hovertemplate="%{text} M€<extra></extra>"
        ))
        titulo = "Receita e Despesa Mensal Total (M€)<br><sup>Clique numa categoria no gráfico de Orçamento para filtrar</sup>"
    else:
        coluna_mensal = CATEGORIAS_ORCAMENTO[categoria_clicada][1] 
        txt_cat = [formatar_numero(v) for v in dff[coluna_mensal]]

        fig.add_trace(go.Bar(
            x=dff["tempo"], y=dff[coluna_mensal],
            name=categoria_clicada, marker_color="#3498db",
            text=txt_cat, 
            textposition="none",
            hovertemplate="%{text} M€<extra></extra>"
        ))
        titulo = f"Evolução Mensal da Despesa: <b>{categoria_clicada}</b> (M€)<br><sup>Faça duplo clique no gráfico de orçamento para limpar o filtro</sup>"

    fig.update_layout(
        title=dict(text=titulo, x=0.5, xanchor="center", y=0.95, yanchor="top"),
        barmode="group",
        yaxis=dict(title="M€", automargin=True),
        legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"),
        margin=dict(l=20, r=20, t=80, b=20),
        height=360,
    )
    return fig


# ============================================================
# FUNÇÃO CONSTRUTORA DE KPIs
# ============================================================

def build_kpi_cards(dff, total_receita, total_despesa, saldo_global):
    num_periodos = dff["tempo"].nunique()
    saldo_mensal = dff["mensal_receita_efectiva"] - dff["mensal_despesa_efectiva"]
    cor_saldo = "#e74c3c" if saldo_global < 0 else "#27ae60"

    spark_receita = create_sparkline(dff["tempo"], dff["mensal_receita_efectiva"], "#27ae60")
    spark_despesa = create_sparkline(dff["tempo"], dff["mensal_despesa_efectiva"], "#e74c3c")
    spark_saldo   = create_sparkline(dff["tempo"], saldo_mensal, cor_saldo)

    return [
        html.Div([
            html.Div("Receita do Período", className="kpi-title"),
            html.Div(f"{formatar_numero(total_receita)} M€", className="kpi-value"),
            dcc.Graph(figure=spark_receita, config={'displayModeBar': False})
        ], className="kpi-card"),
        
        html.Div([
            html.Div("Despesa do Período", className="kpi-title"),
            html.Div(f"{formatar_numero(total_despesa)} M€", className="kpi-value"),
            dcc.Graph(figure=spark_despesa, config={'displayModeBar': False})
        ], className="kpi-card"),
        
        html.Div([
            html.Div("Saldo Global", className="kpi-title"),
            html.Div(f"{formatar_numero(saldo_global)} M€", className="kpi-value", style={"color": cor_saldo}),
            dcc.Graph(figure=spark_saldo, config={'displayModeBar': False})
        ], className="kpi-card"),
        
        html.Div([
            html.Div("Períodos Analisados", className="kpi-title"),
            html.Div(f"{num_periodos}", className="kpi-value"),
            html.Div("Meses selecionados", className="kpi-subtitle", style={"marginTop": "10px"}),
        ], className="kpi-card"),
    ]


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
                html.Div(className="card", children=[dcc.Graph(id="fig-timeline", figure=build_timeline_figure(df_global))]),
            ],
        ),
        
        html.Div(className="card", children=[dcc.Graph(id="fig-despesa-mensal")]),
        html.Div(className="card", children=[dcc.Graph(id="fig-orcamento-execucao")]),
        html.Div(className="card", children=[dcc.Graph(id="fig-heatmap", figure=build_heatmap_figure(df_global))]),
    ],
)


# ============================================================
# CALLBACKS
# ============================================================

@callback(
    Output("store-range-contas", "data"),
    Input("fig-timeline", "relayoutData")
)
def guardar_range(relayoutData):
    if not relayoutData or "xaxis.autorange" in relayoutData:
        return {}
    if "xaxis.range[0]" in relayoutData:
        return {"start": relayoutData["xaxis.range[0]"], "end": relayoutData["xaxis.range[1]"]}
    if "xaxis.range" in relayoutData:
        return {"start": relayoutData["xaxis.range"][0], "end": relayoutData["xaxis.range"][1]}
    return {}


@callback(
    Output("kpi-row-contas",         "children"),
    Output("fig-orcamento-execucao", "figure"),
    Output("fig-despesa-mensal",     "figure"),
    Output("fig-waterfall",          "figure"),
    Output("fig-orcamento-execucao", "clickData"),
    Output("fig-orcamento-execucao", "relayoutData"),
    Input("store-range-contas",      "data"),
    Input("fig-orcamento-execucao",  "clickData"),
    Input("fig-orcamento-execucao",  "relayoutData")
)
def update_dashboard(range_data, click_orcamento, relayout_orcamento):
    out_click, out_relayout, categoria_clicada = no_update, no_update, None
    trigger_prop = ctx.triggered[0]["prop_id"] if ctx.triggered else ""

    if "relayoutData" in trigger_prop and relayout_orcamento and "xaxis.autorange" in relayout_orcamento:
        out_click, out_relayout, categoria_clicada = None, None, None
    elif click_orcamento:
        categoria_clicada = click_orcamento["points"][0]["x"]

    dff = df_global.copy()
    if range_data and "start" in range_data:
        dff = dff[
            (dff["tempo"] >= pd.to_datetime(range_data["start"])) & 
            (dff["tempo"] <= pd.to_datetime(range_data["end"]))
        ]
    
    total_receita = dff["mensal_receita_efectiva"].sum()
    total_despesa = dff["mensal_despesa_efectiva"].sum()
    saldo_global  = total_receita - total_despesa
 
    # Construção
    kpis          = build_kpi_cards(dff, total_receita, total_despesa, saldo_global)
    fig_oc        = build_orcamento_execucao_figure(dff)
    fig_mensal    = build_mensal_figure(dff, categoria_clicada)
    fig_waterfall = build_waterfall_figure(dff, total_receita, total_despesa, saldo_global)

    return kpis, fig_oc, fig_mensal, fig_waterfall, out_click, out_relayout