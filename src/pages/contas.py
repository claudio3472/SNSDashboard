from dash import html, dcc, callback, Input, Output, ctx, no_update
from pages.pages_helper import create_sparkline, kpi_card, carregar_e_processar_dados
import pandas as pd
import plotly.graph_objects as go

# ============================================================
# DATA
# ============================================================

try:
    df = carregar_e_processar_dados("data/processed/contas_sns.csv")
    assert not df.empty, "Dataset vazio após carregamento"
except Exception as e:
    print(f"❌ Erro ao carregar dados: {e}")
    df = pd.DataFrame()

MIN_DATE = df["tempo"].min().date()
MAX_DATE = df["tempo"].max().date()

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


def build_timeline(data):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=data["tempo"],
        y=data["execucao_acumulada_receita_efectiva"],
        name="Receita Acumulada",
        mode="lines",
        line=dict(color="#27ae60", width=2),
        fill="tozeroy",
        fillcolor="rgba(39,174,96,0.1)",
        hovertemplate="Data: %{x|%Y-%m}<br>Receita: %{y:,.1f} M€<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=data["tempo"],
        y=data["execucao_acumulada_despesa_efectiva"],
        name="Despesa Acumulada",
        mode="lines",
        line=dict(color="#e74c3c", width=2),
        hovertemplate="Data: %{x|%Y-%m}<br>Despesa: %{y:,.1f} M€<extra></extra>",
    ))

    fig.update_layout(
        title=dict(
            text="Evolução Receita vs Despesa Acumulada (M€)",
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(type="date"),
        yaxis=dict(title="M€"),
        legend=dict(orientation="h", y=1.12),
        margin=dict(l=20, r=20, t=80, b=40),
        height=360,
        plot_bgcolor="white",
    )

    return fig


def build_heatmap(data):
    pivot = data.pivot_table(
        index="ano",
        columns="mes",
        values="mensal_despesa_efectiva",
        aggfunc="sum",
    )

    nomes_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=nomes_meses,
        y=pivot.index,
        colorscale="Reds",
        hoverongaps=False,
        hovertemplate="Ano: %{y}<br>Mês: %{x}<br>Despesa: %{z:,.1f} M€<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="Sazonalidade da Despesa", x=0.5),
        xaxis=dict(title="Mês"),
        yaxis=dict(title="Ano", type="category"),
        margin=dict(l=20, r=20, t=60, b=30),
        height=340,
    )

    return fig


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
# CALLBACK
# ============================================================

@callback(
    Output("kpi-row-contas", "children"),
    Output("fig-timeline", "figure"),
    Output("fig-orcamento-execucao", "figure"),
    Output("fig-despesa-mensal", "figure"),
    Output("fig-waterfall", "figure"),
    Output("fig-heatmap", "figure"),
    Output("fig-orcamento-execucao", "clickData"),
    Output("fig-orcamento-execucao", "relayoutData"),

    Input("contas-start-date", "date"),
    Input("contas-end-date", "date"),
    Input("fig-orcamento-execucao", "clickData"),
    Input("fig-orcamento-execucao", "relayoutData"),
)
def update_dashboard(start_date, end_date, click_orcamento, relayout_orcamento):

    out_click = no_update
    out_relayout = no_update
    categoria_clicada = None

    trigger_prop = ctx.triggered[0]["prop_id"] if ctx.triggered else ""

    if (
        "relayoutData" in trigger_prop
        and relayout_orcamento
        and "xaxis.autorange" in relayout_orcamento
    ):
        out_click = None
        out_relayout = None
    elif click_orcamento:
        categoria_clicada = click_orcamento["points"][0]["x"]

    dff = filter_period(df, start_date, end_date)

    if dff.empty:
        return (
            [],
            empty_figure("Evolução Receita vs Despesa"),
            empty_figure("Orçamento vs Execução"),
            empty_figure("Despesa Mensal"),
            empty_figure("Cascata Financeira"),
            empty_figure("Sazonalidade"),
            out_click,
            out_relayout,
        )

    last = dff.iloc[-1]

    # ========================================================
    # KPIs
    # ========================================================

    total_receita = dff["mensal_receita_efectiva"].sum()
    total_despesa = dff["mensal_despesa_efectiva"].sum()
    saldo_global = total_receita - total_despesa
    num_periodos = dff["tempo"].nunique()

    saldo_mensal = dff["mensal_receita_efectiva"] - dff["mensal_despesa_efectiva"]
    cor_saldo = "#e74c3c" if saldo_global < 0 else "#27ae60"

    kpis = [
        kpi_card(
            "Receita do Período",
            f"{total_receita:,.1f} M€",
            dcc.Graph(
                figure=create_sparkline(dff["tempo"], dff["mensal_receita_efectiva"], "#27ae60"),
                config={"displayModeBar": False, "staticPlot": True},
            ),
        ),

        kpi_card(
            "Despesa do Período",
            f"{total_despesa:,.1f} M€",
            dcc.Graph(
                figure=create_sparkline(dff["tempo"], dff["mensal_despesa_efectiva"], "#e74c3c"),
                config={"displayModeBar": False, "staticPlot": True},
            ),
        ),

        html.Div(
            className="kpi-card",
            children=[
                html.Div("Saldo Global", className="kpi-title"),
                html.Div(
                    f"{saldo_global:,.1f} M€",
                    className="kpi-value",
                    style={"color": cor_saldo},
                ),
                dcc.Graph(
                    figure=create_sparkline(dff["tempo"], saldo_mensal, cor_saldo),
                    config={"displayModeBar": False, "staticPlot": True},
                ),
            ],
        ),

        kpi_card(
            "Períodos Analisados",
            f"{num_periodos}",
            html.Div(
                "Meses selecionados",
                className="kpi-subtitle",
                style={"marginTop": "10px"},
            ),
        ),
    ]

    # ========================================================
    # TIMELINE
    # ========================================================

    fig_timeline = build_timeline(dff)

    # ========================================================
    # ORÇAMENTO VS EXECUÇÃO
    # ========================================================

    categorias = {
        "Pessoal": ("orcamento_despesas_com_o_pessoal", "mensal_despesas_com_o_pessoal"),
        "Bens e Serviços": ("orcamento_aquisicao_de_bens_e_servicos", "mensal_aquisicao_de_bens_e_servicos"),
        "Transferências": ("orcamento_transferencias_correntes", "mensal_transferencias_correntes"),
        "Investimento": ("orcamento_investimentos", "mensal_investimentos"),
        "Outras Correntes": ("orcamento_outras_despesas_correntes", "mensal_outras_despesas_correntes"),
    }

    nomes = list(categorias.keys())
    orc_vals = [last[v[0]] for v in categorias.values()]
    exe_vals = [dff[v[1]].sum() for v in categorias.values()]

    fig_oc = go.Figure()

    fig_oc.add_trace(go.Bar(
        name="Orçamento",
        x=nomes,
        y=orc_vals,
        marker_color="rgba(52,152,219,0.6)",
        marker_line=dict(color="rgba(52,152,219,1)", width=1.5),
        text=[f"{v:,.1f}" for v in orc_vals],
        textposition="outside",
        hovertemplate="%{x}<br>Orçamento: %{y:,.1f} M€<extra></extra>",
    ))

    fig_oc.add_trace(go.Bar(
        name="Execução no Período",
        x=nomes,
        y=exe_vals,
        marker_color="rgba(231,76,60,0.8)",
        text=[f"{v:,.1f}" for v in exe_vals],
        textposition="outside",
        hovertemplate="%{x}<br>Execução: %{y:,.1f} M€<extra></extra>",
    ))

    fig_oc.update_layout(
        title=dict(
            text="Orçamento Anual vs Execução no Período",
            x=0.5,
            xanchor="center",
        ),
        barmode="group",
        yaxis=dict(title="M€", automargin=True),
        legend=dict(orientation="h", y=1.12),
        margin=dict(l=20, r=20, t=90, b=20),
        height=360,
        plot_bgcolor="white",
    )

    # ========================================================
    # DESPESA MENSAL
    # ========================================================

    fig_mensal = go.Figure()

    if not categoria_clicada:
        fig_mensal.add_trace(go.Bar(
            x=dff["tempo"],
            y=dff["mensal_receita_efectiva"],
            name="Receita Mensal",
            marker_color="#27ae60",
            hovertemplate="Data: %{x|%Y-%m}<br>Receita: %{y:,.1f} M€<extra></extra>",
        ))

        fig_mensal.add_trace(go.Bar(
            x=dff["tempo"],
            y=dff["mensal_despesa_efectiva"],
            name="Despesa Mensal",
            marker_color="#e74c3c",
            hovertemplate="Data: %{x|%Y-%m}<br>Despesa: %{y:,.1f} M€<extra></extra>",
        ))

        titulo_mensal = "Receita e Despesa Mensal"

    else:
        coluna_mensal = categorias[categoria_clicada][1]

        fig_mensal.add_trace(go.Bar(
            x=dff["tempo"],
            y=dff[coluna_mensal],
            name=categoria_clicada,
            marker_color="#3498db",
            hovertemplate="Data: %{x|%Y-%m}<br>Valor: %{y:,.1f} M€<extra></extra>",
        ))

        titulo_mensal = f"Despesa Mensal — {categoria_clicada}"

    fig_mensal.update_layout(
        title=dict(
            text=titulo_mensal,
            x=0.5,
            xanchor="center",
        ),
        barmode="group",
        yaxis=dict(title="M€", automargin=True),
        legend=dict(orientation="h", y=1.12),
        margin=dict(l=20, r=20, t=80, b=20),
        height=360,
        plot_bgcolor="white",
    )

    # ========================================================
    # WATERFALL
    # ========================================================

    pessoal = dff["mensal_despesas_com_o_pessoal"].sum()
    bens_serv = dff["mensal_aquisicao_de_bens_e_servicos"].sum()
    transferenc = dff["mensal_transferencias_correntes"].sum()
    investimento = dff["mensal_investimentos"].sum()
    outras = max(total_despesa - pessoal - bens_serv - transferenc - investimento, 0)

    fig_waterfall = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "relative", "relative", "total"],
        x=["Receita", "Pessoal", "Bens & Serv.", "Transferências", "Investimento", "Outras", "Saldo Final"],
        textposition="outside",
        text=[
            f"{total_receita:,.0f}",
            f"-{pessoal:,.0f}",
            f"-{bens_serv:,.0f}",
            f"-{transferenc:,.0f}",
            f"-{investimento:,.0f}",
            f"-{outras:,.0f}",
            f"{saldo_global:,.0f}",
        ],
        y=[
            total_receita,
            -pessoal,
            -bens_serv,
            -transferenc,
            -investimento,
            -outras,
            saldo_global,
        ],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        decreasing={"marker": {"color": "#e74c3c"}},
        increasing={"marker": {"color": "#27ae60"}},
        totals={"marker": {"color": "#2c3e50" if saldo_global >= 0 else "#c0392b"}},
        hovertemplate="%{x}<br>%{y:,.1f} M€<extra></extra>",
    ))

    fig_waterfall.update_layout(
        title=dict(text="Cascata Financeira: Receita até Saldo", x=0.5),
        margin=dict(l=20, r=20, t=60, b=20),
        height=340,
        showlegend=False,
        plot_bgcolor="white",
    )

    # ========================================================
    # HEATMAP
    # ========================================================

    fig_heatmap = build_heatmap(dff)

    return (
        kpis,
        fig_timeline,
        fig_oc,
        fig_mensal,
        fig_waterfall,
        fig_heatmap,
        out_click,
        out_relayout,
    )