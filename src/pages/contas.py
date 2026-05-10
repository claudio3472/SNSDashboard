from dash import html, dcc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# DATA LOAD
# ============================================================
df = pd.read_csv("data/processed/contas_sns.csv")

df["tempo"] = pd.to_datetime(df["tempo"])
df["ano"] = df["ano"].astype(int)

# ============================================================
# KPIs (EXECUÇÃO ACUMULADA)
# ============================================================
total_receita = df["execucao_acumulada_receita_efectiva"].max() / 1e3
total_despesa = df["execucao_acumulada_despesa_efectiva"].max() / 1e3
saldo_global = df["execucao_acumulada_saldo_global"].iloc[-1] / 1e3
num_periodos = df["tempo"].nunique()

# ============================================================
# 1️⃣ RECEITA vs DESPESA (EXECUÇÃO ACUMULADA)
# ============================================================
ts = df.sort_values("tempo").copy()

fig_receita_despesa = go.Figure()

fig_receita_despesa.add_trace(go.Scatter(
    x=ts["tempo"],
    y=ts["execucao_acumulada_receita_efectiva"] / 1e3,
    name="Receita",
    line=dict(color="#16a34a"),
))

fig_receita_despesa.add_trace(go.Scatter(
    x=ts["tempo"],
    y=ts["execucao_acumulada_despesa_efectiva"] / 1e3,
    name="Despesa",
    line=dict(color="#dc2626"),
    fill="tonexty",
))

fig_receita_despesa.update_layout(
    title="Receita vs Despesa (Execução Acumulada, M€)",
    height=360,
)

# ============================================================
# 2️⃣ EVOLUÇÃO DO SALDO
# ============================================================
fig_saldo = px.bar(
    ts,
    x="tempo",
    y=ts["execucao_acumulada_saldo_global"] / 1e3,
    title="Evolução do Saldo (M€)",
)
fig_saldo.update_layout(height=360)

# ============================================================
# 3️⃣ ORÇAMENTO vs EXECUÇÃO (DESPESA)
# ============================================================
orc_exec = (
    df.groupby("ano")[[
        "orcamento_despesa_efectiva",
        "execucao_acumulada_despesa_efectiva",
    ]]
    .max()
    .reset_index()
)

orc_exec[[
    "orcamento_despesa_efectiva",
    "execucao_acumulada_despesa_efectiva",
]] /= 1e3

fig_orc_exec = go.Figure()

fig_orc_exec.add_trace(go.Bar(
    x=orc_exec["ano"],
    y=orc_exec["orcamento_despesa_efectiva"],
    name="Orçamento da Despesa",
    marker_color="#2563eb",
))

fig_orc_exec.add_trace(go.Bar(
    x=orc_exec["ano"],
    y=orc_exec["execucao_acumulada_despesa_efectiva"],
    name="Execução da Despesa",
    marker_color="#22c55e",
))

fig_orc_exec.update_layout(
    title="Orçamento vs Execução da Despesa (M€)",
    barmode="group",
    height=360,
)

# ============================================================
# 4️⃣ CATEGORIAS DE DESPESA (MÉDIA DE EXECUÇÃO)
# ============================================================
cats = pd.DataFrame({
    "Categoria": ["Pessoal", "Bens e Serviços"],
    "Valor": [
        df["execucao_acumulada_despesas_com_o_pessoal"].mean(),
        df["execucao_acumulada_aquisicao_de_bens_e_servicos"].mean(),
    ],
})

cats["Valor"] /= 1e3

fig_categorias = px.pie(
    cats,
    names="Categoria",
    values="Valor",
    title="Composição Média da Despesa (Execução)",
)

# ============================================================
# 5️⃣ MÉDIA ANUAL: RECEITA vs DESPESA
# ============================================================
media_anual = (
    df.groupby("ano")[[
        "execucao_acumulada_receita_efectiva",
        "execucao_acumulada_despesa_efectiva",
    ]]
    .mean()
    .reset_index()
)

media_anual[[
    "execucao_acumulada_receita_efectiva",
    "execucao_acumulada_despesa_efectiva",
]] /= 1e3

fig_media = px.bar(
    media_anual,
    x="ano",
    y=[
        "execucao_acumulada_receita_efectiva",
        "execucao_acumulada_despesa_efectiva",
    ],
    title="Média Anual: Receita vs Despesa (M€)",
    barmode="group",
)
fig_media.update_layout(height=360)

# ============================================================
# 6️⃣ TAXA DE EXECUÇÃO 
# ============================================================
df_taxa = df.copy()

df_taxa["taxa_execucao"] = (
    df_taxa["execucao_acumulada_despesa_efectiva"]
    / df_taxa["orcamento_despesa_efectiva"]
) * 100

taxa_ts = (
    df_taxa.groupby("tempo")["taxa_execucao"]
    .mean()
    .reset_index()
)

taxa_ts["rolling_6m"] = taxa_ts["taxa_execucao"].rolling(6).mean()

fig_taxa = go.Figure()

fig_taxa.add_trace(go.Scatter(
    x=taxa_ts["tempo"],
    y=taxa_ts["taxa_execucao"],
    name="Taxa de Execução",
))

fig_taxa.add_trace(go.Scatter(
    x=taxa_ts["tempo"],
    y=taxa_ts["rolling_6m"],
    name="Tendência (6 meses)",
    line=dict(width=3, dash="dot"),
))

fig_taxa.add_hline(
    y=100,
    line_dash="dash",
    line_color="red",
    annotation_text="100% Execução",
)

fig_taxa.update_layout(
    title="Taxa de Execução Orçamental (%)",
    height=360,
)

# ============================================================
# KPI CARD
# ============================================================
def kpi_card(title, value):
    return html.Div(
        className="kpi-card",
        children=[
            html.Div(title, className="kpi-title"),
            html.Div(value, className="kpi-value"),
        ],
    )

# ============================================================
# ✅ FINAL LAYOUT
# ============================================================
layout = html.Div(
    className="content",
    children=[
        html.H2("Contas SNS"),
        html.P("Orçamento e execução do Serviço Nacional de Saúde"),

        html.Div(
            className="kpi-row",
            children=[
                kpi_card("Receita Efetiva", f"{total_receita:,.0f} M€"),
                kpi_card("Despesa Efetiva", f"{total_despesa:,.0f} M€"),
                kpi_card("Saldo Global", f"{saldo_global:,.0f} M€"),
                kpi_card("Períodos", f"{num_periodos}"),
            ],
        ),

        html.Div(
            className="grid-2x2",
            children=[
                dcc.Graph(figure=fig_receita_despesa),
                dcc.Graph(figure=fig_saldo),
                dcc.Graph(figure=fig_orc_exec),
                dcc.Graph(figure=fig_categorias),
                dcc.Graph(figure=fig_media),
                dcc.Graph(figure=fig_taxa),
            ],
        ),
    ],
)
