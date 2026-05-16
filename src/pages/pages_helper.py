import pandas as pd
import plotly.graph_objects as go
from dash import html
import os


def load_data(data_path: str | None = None) -> pd.DataFrame:
    """Load raw CSV from data folder."""
    if data_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_path = os.path.join(base_dir, "..", "data", "processed", "master_dataset.csv")

    return pd.read_csv(data_path)


def process_data(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize column types and strip strings. Returns a processed DataFrame."""
    dfp = raw.copy()
    if "ano" in dfp.columns:
        dfp["ano"] = dfp["ano"].astype(int)
    if "regiao" in dfp.columns:
        dfp["regiao"] = dfp["regiao"].astype(str).str.strip()
    if "instituicao" in dfp.columns:
        dfp["instituicao"] = dfp["instituicao"].astype(str).str.strip()

    return dfp


def kpi_card(title, value, extra_component=None):
    children = [
        html.Div(title, className="kpi-title"),
        html.Div(value, className="kpi-value"),
    ]
    
    if extra_component is not None:
        children.append(extra_component)
        
    return html.Div(className="kpi-card", children=children)


def create_sparkline(x_data, y_data, color):
    fig = go.Figure(
        go.Scatter(
            x=x_data,
            y=y_data,
            mode="lines",
            line=dict(color=color, width=2.5),
            hoverinfo="skip",
        )
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=4, b=4),
        height=56,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig

def carregar_e_processar_dados(caminho: str) -> pd.DataFrame:
    """Carrega, valida e processa dados consoante o dataset especificado"""
    df = pd.read_csv(caminho)
    
    if caminho == "data/processed/contas_sns.csv":
        df = processar_contas_sns(df)
    else:
        raise ValueError(f"Dataset desconhecido: {caminho}")
    
    return df


def processar_contas_sns(df: pd.DataFrame) -> pd.DataFrame:
    
    df["ano"] = df["ano"].astype(int)
    df["tempo"] = pd.to_datetime(df["tempo"])
    df = df.sort_values("tempo").reset_index(drop=True)
    df["mes"] = df["tempo"].dt.month
    
    colunas = [
        "execucao_acumulada_receita_efectiva",
        "execucao_acumulada_despesa_efectiva",
        "execucao_acumulada_despesas_com_o_pessoal",
        "execucao_acumulada_aquisicao_de_bens_e_servicos",
        "execucao_acumulada_transferencias_correntes",
        "execucao_acumulada_investimentos",
        "execucao_acumulada_outras_despesas_correntes"
    ]
    
    for col in colunas:
        nova_col = col.replace("execucao_acumulada_", "mensal_")
        df[nova_col] = df.groupby(df["tempo"].dt.year)[col].diff().fillna(df[col])
    
    return df

def aplicar_config_padrao(fig: go.Figure, titulo: str, altura: int = 320) -> go.Figure:
    """Aplica configurações visuais padrão a um gráfico"""
    fig.update_layout(
        title=titulo,
        yaxis=dict(title="M€"),
        margin=dict(l=20, r=20, t=70, b=20),
        height=altura,
    )
    return fig