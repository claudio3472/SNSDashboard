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

try:
    df_global = carregar_e_processar_dados("data/processed/contas_sns.csv")
    assert not df_global.empty, "Dataset vazio após carregamento"
except Exception as e:
    print(f"❌ Erro ao carregar dados: {e}")
    df_global = pd.DataFrame()

if not df_global.empty:
    MIN_DATE = df_global["tempo"].min().date()
    MAX_DATE = df_global["tempo"].max().date()
else:
    MIN_DATE = None
    MAX_DATE = None


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
        title=title,
        height=320,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text="Sem dados para o período selecionado",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
            )
        ],
    )
    return fig


# ============================================================
# CHART BUILDERS
# ============================================================

def build_timeline_figure(df):
    if df.empty: return empty_figure("Evolução Receita vs Despesa")
    
    txt_receita = [formatar_numero(v) for v in df["execucao_acumulada_receita_efectiva"]]
    txt_despesa = [formatar_numero(v) for v in df["execucao_acumulada_despesa_efectiva"]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["tempo"], y=df["execucao_acumulada_receita_efectiva"],
        name="Receita (Acumulada)", line=dict(color="#27ae60", width=2), fill="tozeroy",
        fillcolor="rgba(39,174,96,0.1)",
        text=txt_receita, hovertemplate="Data: %{x|%Y-%m}<br>Receita: %{text} M€<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=df["tempo"], y=df["execucao_acumulada_despesa_efectiva"],
        name="Despesa (Acumulada)", line=dict(color="#e74c3c", width=2),
        text=txt_despesa, hovertemplate="Data: %{x|%Y-%m}<br>Despesa: %{text} M€<extra></extra>"
    ))
    fig.update_layout(
        title=dict(
            text="Evolução Receita vs Despesa Acumulada (M€)",
            x=0.5, xanchor="center", y=0.95, yanchor="top",
            font=dict(size=16)
        ),
        xaxis=dict(type="date"),
        yaxis=dict(title="M€"),
        legend=dict(orientation="h", y=1.12),
        margin=dict(l=20, r=20, t=80, b=40),
        height=340,
        plot_bgcolor="white",
    )
    return fig


def build_heatmap_figure(df):
    if df.empty: return empty_figure("Sazonalidade da Despesa")
    
    pivot = df.pivot_table(index="ano", columns="mes", values="mensal_despesa_efectiva", aggfunc="sum")
    text_matrix = [[formatar_numero(val) if pd.notna(val) else "" for val in row] for row in pivot.values]
    
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
    if dff.empty: return empty_figure("Cascata Financeira")

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
        showlegend=False,
        plot_bgcolor="white",
    )
    return fig


def build_orcamento_execucao_figure(dff):
    if dff.empty: return empty_figure("Orçamento vs Execução")
    
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
        plot_bgcolor="white",
    )
    return fig


def build_mensal_figure(dff, categoria_clicada):
    if dff.empty: return empty_figure("Despesa Mensal")

    fig = go.Figure()
    
    if not categoria_clicada:
        txt_rec = [formatar_numero(v) for v in dff["mensal_receita_efectiva"]]
        txt_desp = [formatar_numero(v) for v in dff["mensal_despesa_efectiva"]]

        fig.add_trace(go.Bar(
            x=dff["tempo"], y=dff["mensal_receita_efectiva"],
            name="Receita Mensal", marker_color="#27ae60",
            text=txt_rec, 
            textposition="none",
            hovertemplate="Data: %{x|%Y-%m}<br>Receita: %{text} M€<extra></extra>"
        ))
        fig.add_trace(go.Bar(
            x=dff["tempo"], y=dff["mensal_despesa_efectiva"],
            name="Despesa Mensal Total", marker_color="#e74c3c",
            text=txt_desp, 
            textposition="none",
            hovertemplate="Data: %{x|%Y-%m}<br>Despesa: %{text} M€<extra></extra>"
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
            hovertemplate="Data: %{x|%Y-%m}<br>Valor: %{text} M€<extra></extra>"
        ))
        titulo = f"Evolução Mensal da Despesa: <b>{categoria_clicada}</b> (M€)<br><sup>Faça duplo clique no gráfico de orçamento para limpar o filtro</sup>"

    fig.update_layout(
        title=dict(text=titulo, x=0.5, xanchor="center", y=0.95, yanchor="top"),
        barmode="group",
        yaxis=dict(title="M€", automargin=True),
        legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"),
        margin=dict(l=20, r=20, t=80, b=20),
        height=360,
        plot_bgcolor="white",
    )
    return fig


# ============================================================
# FUNÇÃO CONSTRUTORA DE KPIs
# ============================================================

def build_kpi_cards(dff, total_receita, total_despesa, saldo_global):
    if dff.empty: return []

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
            dcc.Graph(figure=spark_receita, config={'displayModeBar': False, 'staticPlot': True})
        ], className="kpi-card"),
        
        html.Div([
            html.Div("Despesa do Período", className="kpi-title"),
            html.Div(f"{formatar_numero(total_despesa)} M€", className="kpi-value"),
            dcc.Graph(figure=spark_despesa, config={'displayModeBar': False, 'staticPlot': True})
        ], className="kpi-card"),
        
        html.Div([
            html.Div("Saldo Global", className="kpi-title"),
            html.Div(f"{formatar_numero(saldo_global)} M€", className="kpi-value", style={"color": cor_saldo}),
            dcc.Graph(figure=spark_saldo, config={'displayModeBar': False, 'staticPlot': True})
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
                    html.H2("Contas SNS", style={"marginBottom": "8px"}),
                    html.P(
                        "Análise do orçamento e execução do Serviço Nacional de Saúde",
                        style={"color": "#6b7280", "marginBottom": "0"},
                    ),
                ]),

                html.Div(
                    style={
                        "display": "flex",
                        "gap": "14px",
                        "alignItems": "flex-end",
                        "marginTop": "10px",
                    },
                    children=[
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
                                id="contas-start-date",
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
                                id="contas-end-date",
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

        html.Div(id="kpi-row-contas", className="kpi-row"),

        html.Div(
            className="grid-2x2",
            children=[
                html.Div(className="card", children=[dcc.Graph(id="fig-waterfall")]),
                html.Div(className="card", children=[dcc.Graph(id="fig-timeline")]),
            ],
        ),
        
        html.Div(className="card", children=[dcc.Graph(id="fig-despesa-mensal")]),
        html.Div(className="card", children=[dcc.Graph(id="fig-orcamento-execucao")]),
        html.Div(className="card", children=[dcc.Graph(id="fig-heatmap")]),
    ],
)


# ============================================================
# CALLBACKS
# ============================================================

@callback(
    Output("kpi-row-contas",         "children"),
    Output("fig-timeline",           "figure"),
    Output("fig-orcamento-execucao", "figure"),
    Output("fig-despesa-mensal",     "figure"),
    Output("fig-waterfall",          "figure"),
    Output("fig-heatmap",            "figure"),
    Output("fig-orcamento-execucao", "clickData"),
    Output("fig-orcamento-execucao", "relayoutData"),
    
    Input("contas-start-date",       "date"),
    Input("contas-end-date",         "date"),
    Input("fig-orcamento-execucao",  "clickData"),
    Input("fig-orcamento-execucao",  "relayoutData")
)
def update_dashboard(start_date, end_date, click_orcamento, relayout_orcamento):
    out_click, out_relayout, categoria_clicada = no_update, no_update, None
    trigger_prop = ctx.triggered[0]["prop_id"] if ctx.triggered else ""

    if "relayoutData" in trigger_prop and relayout_orcamento and "xaxis.autorange" in relayout_orcamento:
        out_click, out_relayout, categoria_clicada = None, None, None
    elif click_orcamento:
        categoria_clicada = click_orcamento["points"][0]["x"]

    dff = filter_period(df_global, start_date, end_date)

    if dff.empty:
        return (
            [],
            empty_figure("Evolução Receita vs Despesa Acumulada (M€)"),
            empty_figure("Orçamento vs Execução"),
            empty_figure("Despesa Mensal"),
            empty_figure("Cascata Financeira"),
            empty_figure("Sazonalidade da Despesa"),
            out_click,
            out_relayout,
        )
    
    total_receita = dff["mensal_receita_efectiva"].sum()
    total_despesa = dff["mensal_despesa_efectiva"].sum()
    saldo_global  = total_receita - total_despesa
 
    # Construção com as lógicas refatoradas
    kpis          = build_kpi_cards(dff, total_receita, total_despesa, saldo_global)
    fig_timeline  = build_timeline_figure(dff)
    fig_oc        = build_orcamento_execucao_figure(dff)
    fig_mensal    = build_mensal_figure(dff, categoria_clicada)
    fig_waterfall = build_waterfall_figure(dff, total_receita, total_despesa, saldo_global)
    fig_heatmap   = build_heatmap_figure(dff)

    return (
        kpis, 
        fig_timeline, 
        fig_oc, 
        fig_mensal, 
        fig_waterfall, 
        fig_heatmap, 
        out_click, 
        out_relayout
    )