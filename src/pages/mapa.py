# ============================================================
# mapa.py
# ============================================================

from dash import (
    html,
    dcc,
    callback,
    Input,
    Output,
    State,
    dash_table,
    no_update,
    ctx,
)

import pandas as pd
import numpy as np
import geopandas as gpd
import plotly.graph_objects as go
import re

from shapely.geometry import Point, Polygon

# ============================================================
# DATA
# ============================================================

df = pd.read_csv("data/processed/master_dataset.csv")

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

# ============================================================
# SAFE COLUMNS
# ============================================================

needed_cols = [
    "no_de_consultas_medicas_total",
    "total_urgencias",
    "medicos_internos",
    "enfermeiros",
]

for col in needed_cols:
    if col not in df.columns:
        df[col] = 0

for col in needed_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

if "tipo_instituicao" not in df.columns:
    df["tipo_instituicao"] = "Instituição"

# ============================================================
# GEOLOCATION
# ============================================================

def parse_localizacao(value):
    if pd.isna(value):
        return pd.Series([np.nan, np.nan])

    nums = re.findall(r"-?\d+\.\d+|-?\d+", str(value))

    if len(nums) < 2:
        return pd.Series([np.nan, np.nan])

    return pd.Series([float(nums[0]), float(nums[1])])


if "localizacao_geografica" in df.columns:
    df[["lat", "lon"]] = df["localizacao_geografica"].apply(parse_localizacao)
else:
    df["lat"] = np.nan
    df["lon"] = np.nan

df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

# ============================================================
# MAP FILE
# ============================================================

MAP_PATH = "src/map/geoBoundaries-PRT-ADM3.shp"
gdf = gpd.read_file(MAP_PATH).to_crs(epsg=4326)


def make_unique_columns(columns):
    seen = {}
    new_cols = []

    for col in columns:
        if col not in seen:
            seen[col] = 0
            new_cols.append(col)
        else:
            seen[col] += 1
            new_cols.append(f"{col}_{seen[col]}")

    return new_cols


gdf.columns = make_unique_columns(gdf.columns)
gdf["map_id"] = gdf.index.astype(str)
gdf["geometry"] = gdf["geometry"].simplify(0.002, preserve_topology=True)

# ============================================================
# REGIONS
# ============================================================

REGIOES = [
    "Norte",
    "Centro",
    "Lisboa e Vale do Tejo",
    "Alentejo",
    "Algarve",
]

ZONE_POLYGONS = {
    "Norte": Polygon([
        (-9.00, 40.75),
        (-6.00, 40.75),
        (-6.00, 42.35),
        (-9.00, 42.35),
    ]),
    "Centro": Polygon([
        (-9.25, 39.20),
        (-6.00, 39.20),
        (-6.00, 40.75),
        (-9.25, 40.75),
    ]),
    "Lisboa e Vale do Tejo": Polygon([
        (-9.65, 38.25),
        (-7.45, 38.25),
        (-7.45, 39.75),
        (-9.65, 39.75),
    ]),
    "Alentejo": Polygon([
        (-9.25, 37.20),
        (-6.60, 37.20),
        (-6.60, 39.20),
        (-9.25, 39.20),
    ]),
    "Algarve": Polygon([
        (-9.10, 36.80),
        (-7.20, 36.80),
        (-7.20, 37.45),
        (-9.10, 37.45),
    ]),
}

REGIAO_COORDS = {
    "Norte": {"lat": 41.35, "lon": -8.20, "color": "#0072B2"},
    "Centro": {"lat": 40.20, "lon": -8.15, "color": "#E69F00"},
    "Lisboa e Vale do Tejo": {"lat": 38.80, "lon": -9.05, "color": "#009E73"},
    "Alentejo": {"lat": 38.10, "lon": -7.85, "color": "#D55E00"},
    "Algarve": {"lat": 37.10, "lon": -8.10, "color": "#CC79A7"},
}

REGION_BOUNDS = {
    "Norte": {"lon": [-8.95, -6.15], "lat": [40.70, 42.30]},
    "Centro": {"lon": [-9.25, -6.25], "lat": [39.15, 40.85]},
    "Lisboa e Vale do Tejo": {"lon": [-9.65, -7.35], "lat": [38.20, 39.75]},
    "Alentejo": {"lon": [-9.25, -6.55], "lat": [37.20, 39.25]},
    "Algarve": {"lon": [-9.10, -7.15], "lat": [36.90, 37.45]},
}

COLORBLIND = [
    "#0072B2",
    "#E69F00",
    "#009E73",
    "#D55E00",
    "#CC79A7",
    "#56B4E9",
]

ACTIVITY_SCALE = [
    [0.0, "#F7FBFF"],
    [0.25, "#C6DBEF"],
    [0.5, "#6BAED6"],
    [0.75, "#2171B5"],
    [1.0, "#08306B"],
]

# ============================================================
# ASSIGN ZONES
# ============================================================

def assign_zone(lat, lon, fallback=None):
    if pd.isna(lat) or pd.isna(lon):
        return fallback

    point = Point(lon, lat)

    for zone, polygon in ZONE_POLYGONS.items():
        if polygon.contains(point):
            return zone

    return fallback


df["zona_mapa"] = df.apply(
    lambda row: assign_zone(row["lat"], row["lon"], row["regiao"]),
    axis=1,
)

gdf_points = gdf.copy()
gdf_points["point"] = gdf_points.geometry.representative_point()
gdf["lon"] = gdf_points["point"].x
gdf["lat"] = gdf_points["point"].y

gdf["zona_mapa"] = gdf.apply(
    lambda row: assign_zone(row["lat"], row["lon"], None),
    axis=1,
)

geojson_map = gdf.__geo_interface__

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


def create_sparkline(x_data, y_data, color):
    fig = go.Figure()

    fig.add_trace(
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


def kpi_card(title, value, extra_component=None, color=None, subtitle=None):
    children = [
        html.Div(title, className="kpi-title"),
        html.Div(
            value,
            className="kpi-value",
            style={"color": color} if color else {},
        ),
    ]

    if extra_component is not None:
        children.append(extra_component)

    if subtitle:
        children.append(
            html.Div(
                subtitle,
                className="kpi-subtitle",
                style={
                    "marginTop": "10px",
                    "fontSize": "0.85rem",
                    "color": "#7f8c8d",
                },
            )
        )

    return html.Div(className="kpi-card", children=children)


def empty_figure(title, text="Sem dados para os filtros selecionados"):
    fig = go.Figure()

    fig.update_layout(
        title=dict(text=title, x=0.03),
        height=400,
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


def safe_area_figure(df_area, title):
    if df_area.empty:
        return empty_figure(title)

    fig = go.Figure()

    for i, regiao in enumerate(REGIOES):
        dfr = df_area[df_area["zona_mapa"] == regiao]

        if dfr.empty:
            continue

        fig.add_trace(
            go.Scatter(
                x=dfr["tempo"],
                y=dfr["atividade"],
                mode="lines",
                stackgroup="one",
                name=regiao,
                line=dict(
                    color=COLORBLIND[i % len(COLORBLIND)],
                    width=2,
                ),
                hovertemplate=(
                    "Data: %{x|%Y-%m}<br>"
                    "Atividade: %{y:,.0f}"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(text=title, x=0.03),
        height=400,
        margin=dict(l=30, r=30, t=80, b=40),
        yaxis=dict(title="Atividade"),
        xaxis=dict(title=None),
        legend=dict(orientation="h", y=1.12),
        plot_bgcolor="white",
    )

    return fig


def make_map(selected_region=None, dff=None):
    if dff is None:
        dff = df.copy()

    atividade = (
        dff.groupby("zona_mapa")
        .agg(
            consultas=("no_de_consultas_medicas_total", "sum"),
            urgencias=("total_urgencias", "sum"),
        )
        .reindex(REGIOES)
        .fillna(0)
        .reset_index()
    )

    atividade["atividade"] = atividade["consultas"] + atividade["urgencias"]
    atividade["atividade_m"] = atividade["atividade"] / 1e6

    map_df = gdf[["map_id", "zona_mapa"]].drop_duplicates().copy()

    map_df = map_df.merge(
        atividade[["zona_mapa", "atividade_m"]],
        on="zona_mapa",
        how="left",
    )

    map_df["atividade_m"] = map_df["atividade_m"].fillna(0)

    if selected_region:
        map_df.loc[map_df["zona_mapa"] != selected_region, "atividade_m"] = 0

    fig = go.Figure()

    fig.add_trace(
        go.Choropleth(
            geojson=geojson_map,
            locations=map_df["map_id"],
            z=map_df["atividade_m"],
            featureidkey="properties.map_id",
            colorscale=ACTIVITY_SCALE,
            showscale=True,
            marker_line_color="white",
            marker_line_width=0.35,
            customdata=map_df[["zona_mapa", "atividade_m"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Atividade: %{customdata[1]:.2f} M"
                "<extra></extra>"
            ),
            colorbar=dict(title="Milhões", thickness=12),
            name="Atividade",
        )
    )

    if not selected_region:
        for regiao, info in REGIAO_COORDS.items():
            fig.add_trace(
                go.Scattergeo(
                    lon=[info["lon"]],
                    lat=[info["lat"]],
                    mode="markers+text",
                    text=[regiao],
                    customdata=[["region", regiao]],
                    marker=dict(
                        size=42,
                        color=info["color"],
                        opacity=0.92,
                        line=dict(color="#111827", width=1),
                    ),
                    textposition="middle center",
                    textfont=dict(color="#111827", size=11),
                    hovertemplate="<b>%{customdata[1]}</b><extra></extra>",
                    name=regiao,
                )
            )

    if selected_region:
        inst = (
            dff[
                (dff["zona_mapa"] == selected_region)
                & dff["lat"].notna()
                & dff["lon"].notna()
            ]
            .groupby(["instituicao", "lat", "lon"])
            .agg(
                consultas=("no_de_consultas_medicas_total", "sum"),
                urgencias=("total_urgencias", "sum"),
            )
            .reset_index()
        )

        inst["atividade"] = inst["consultas"] + inst["urgencias"]

        max_atividade = inst["atividade"].max()

        if pd.notna(max_atividade) and max_atividade > 0:
            inst["size"] = (inst["atividade"] / max_atividade * 38) + 8
        else:
            inst["size"] = 12

        if not inst.empty:
            fig.add_trace(
                go.Scattergeo(
                    lon=inst["lon"],
                    lat=inst["lat"],
                    mode="markers",
                    marker=dict(
                        size=inst["size"],
                        color="#111827",
                        opacity=0.78,
                        line=dict(color="white", width=1),
                    ),
                    customdata=inst[["instituicao", "consultas", "urgencias"]],
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Consultas: %{customdata[1]:,.0f}<br>"
                        "Urgências: %{customdata[2]:,.0f}"
                        "<extra></extra>"
                    ),
                    name="Instituições",
                )
            )

    if selected_region:
        lon_range = REGION_BOUNDS[selected_region]["lon"]
        lat_range = REGION_BOUNDS[selected_region]["lat"]
    else:
        lon_range = [-9.7, -6.0]
        lat_range = [36.8, 42.3]

    fig.update_geos(
        visible=False,
        projection_type="mercator",
        lonaxis=dict(range=lon_range),
        lataxis=dict(range=lat_range),
    )

    fig.update_layout(
        title=dict(
            text=(
                f"Mapa de Atividade — {selected_region}"
                if selected_region
                else "Mapa de Atividade Assistencial"
            ),
            x=0.03,
            font=dict(size=16),
        ),
        height=580,
        margin=dict(l=0, r=0, t=60, b=0),
        showlegend=False,
        dragmode=False,
    )

    return fig

# ============================================================
# LAYOUT
# ============================================================

layout = html.Div(
    className="content",
    children=[
        dcc.Store(id="mapa-region"),
        dcc.Store(id="mapa-inst"),

        html.Div(
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "gap": "12px",
                "flexWrap": "wrap",
            },
            children=[
                html.Div([
                    html.H2("Mapa Regional"),
                    html.P(id="mapa-subtitle"),
                ]),

                html.Div(
                    style={
                        "display": "flex",
                        "gap": "10px",
                        "alignItems": "center",
                        "flexWrap": "wrap",
                    },
                    children=[
                        html.Button(
                            "Voltar às regiões",
                            id="btn-reset-region",
                            n_clicks=0,
                            className="reset-btn",
                        ),

                        html.Button(
                            "Limpar instituição",
                            id="btn-reset-inst",
                            n_clicks=0,
                            className="reset-btn",
                        ),

                        html.Div(
                            children=[
                                html.Div(
                                    "Data Inicial",
                                    style={
                                        "fontSize": "12px",
                                        "marginBottom": "4px",
                                        "fontWeight": "600",
                                    },
                                ),

                                dcc.DatePickerSingle(
                                    id="mapa-start-date",
                                    min_date_allowed=MIN_DATE,
                                    max_date_allowed=MAX_DATE,
                                    date=MIN_DATE,
                                    display_format="YYYY-MM-DD",
                                ),
                            ]
                        ),

                        html.Div(
                            children=[
                                html.Div(
                                    "Data Final",
                                    style={
                                        "fontSize": "12px",
                                        "marginBottom": "4px",
                                        "fontWeight": "600",
                                    },
                                ),

                                dcc.DatePickerSingle(
                                    id="mapa-end-date",
                                    min_date_allowed=MIN_DATE,
                                    max_date_allowed=MAX_DATE,
                                    date=None,
                                    placeholder="Última disponível",
                                    display_format="YYYY-MM-DD",
                                ),
                            ]
                        ),
                    ],
                ),
            ],
        ),

        html.Div(id="mapa-kpis", className="kpi-row"),

        html.Div(
            className="card",
            style={"marginBottom": "20px"},
            children=[
                dcc.Graph(id="mapa-portugal", config={"displayModeBar": False}),
            ],
        ),

        html.Div(
            className="grid-2x2",
            children=[
                html.Div(
                    className="card",
                    children=[dcc.Graph(id="mapa-atividade", config={"displayModeBar": False})],
                ),
                html.Div(
                    className="card",
                    children=[dcc.Graph(id="mapa-tipo", config={"displayModeBar": False})],
                ),
                html.Div(
                    className="card",
                    children=[dcc.Graph(id="mapa-capacidade", config={"displayModeBar": False})],
                ),
                html.Div(
                    className="card",
                    children=[dcc.Graph(id="mapa-detail", config={"displayModeBar": False})],
                ),
            ],
        ),

        html.Div(
            className="card",
            children=[
                html.H4("Instituições"),

                dash_table.DataTable(
                    id="mapa-table",
                    page_size=10,
                    active_cell=None,
                    style_table={"overflowX": "auto"},
                    style_cell={
                        "textAlign": "left",
                        "padding": "8px",
                    },
                    style_header={
                        "fontWeight": "bold",
                        "backgroundColor": "#f3f4f6",
                    },
                    style_data_conditional=[
                        {
                            "if": {"state": "active"},
                            "backgroundColor": "#dbeafe",
                            "border": "1px solid #2563eb",
                        }
                    ],
                ),
            ],
        ),
    ],
)

# ============================================================
# SELECTION CALLBACK
# ============================================================

@callback(
    Output("mapa-region", "data"),
    Output("mapa-inst", "data"),

    Input("mapa-portugal", "clickData"),
    Input("mapa-table", "active_cell"),
    Input("btn-reset-region", "n_clicks"),
    Input("btn-reset-inst", "n_clicks"),

    State("mapa-table", "data"),
    State("mapa-region", "data"),

    prevent_initial_call=True,
)
def update_selection(
    map_click,
    active_cell,
    reset_region,
    reset_inst,
    table_data,
    current_region,
):
    trigger = ctx.triggered_id

    if trigger == "btn-reset-region":
        return None, None

    if trigger == "btn-reset-inst":
        return current_region, None

    if trigger == "mapa-table" and active_cell and table_data:
        row = active_cell["row"]
        inst = table_data[row]["instituicao"]

        return current_region, inst

    if trigger == "mapa-portugal" and map_click:
        point = map_click["points"][0]

        if "customdata" not in point:
            return no_update, no_update

        custom = point["customdata"]

        if isinstance(custom, list):
            if len(custom) >= 2 and custom[0] == "region":
                return custom[1], None

            if len(custom) >= 1 and custom[0] in REGIOES:
                return custom[0], None

    return no_update, no_update

# ============================================================
# UPDATE DASHBOARD
# ============================================================

@callback(
    Output("mapa-subtitle", "children"),
    Output("mapa-kpis", "children"),
    Output("mapa-portugal", "figure"),
    Output("mapa-atividade", "figure"),
    Output("mapa-tipo", "figure"),
    Output("mapa-capacidade", "figure"),
    Output("mapa-detail", "figure"),
    Output("mapa-table", "data"),
    Output("mapa-table", "columns"),

    Input("mapa-start-date", "date"),
    Input("mapa-end-date", "date"),
    Input("mapa-region", "data"),
    Input("mapa-inst", "data"),
)
def update_dashboard(
    start_date,
    end_date,
    selected_region,
    selected_inst,
):
    dff = filter_period(df, start_date, end_date)

    if selected_region:
        dff_region = dff[dff["zona_mapa"] == selected_region].copy()
    else:
        dff_region = dff.copy()

    if selected_inst:
        dff_inst = dff_region[dff_region["instituicao"] == selected_inst].copy()
    else:
        dff_inst = dff_region.copy()

    real_end = end_date or str(MAX_DATE)
    subtitle = f"Período: {start_date} a {real_end} | Nível: {selected_region or 'Portugal'}"

    if selected_inst:
        subtitle += f" → {selected_inst}"

    # ========================================================
    # KPIs
    # ========================================================

    consultas = int(dff_inst["no_de_consultas_medicas_total"].sum())
    urgencias = int(dff_inst["total_urgencias"].sum())
    atividade = consultas + urgencias
    profissionais = int((dff_inst["medicos_internos"] + dff_inst["enfermeiros"]).sum())
    instituicoes = dff_inst["instituicao"].nunique()
    periodos = dff_inst["tempo"].nunique()

    spark_df = (
        dff_inst.groupby("tempo")
        .agg(
            consultas=("no_de_consultas_medicas_total", "sum"),
            urgencias=("total_urgencias", "sum"),
            medicos=("medicos_internos", "sum"),
            enfermeiros=("enfermeiros", "sum"),
        )
        .reset_index()
        .sort_values("tempo")
    )

    spark_df["atividade"] = spark_df["consultas"] + spark_df["urgencias"]
    spark_df["profissionais"] = spark_df["medicos"] + spark_df["enfermeiros"]

    kpis = [
        kpi_card(
            "Atividade Total",
            f"{atividade:,}".replace(",", " "),
            dcc.Graph(
                figure=create_sparkline(spark_df["tempo"], spark_df["atividade"], "#0072B2"),
                config={"displayModeBar": False, "staticPlot": True},
            ),
        ),
        kpi_card(
            "Consultas",
            f"{consultas:,}".replace(",", " "),
            dcc.Graph(
                figure=create_sparkline(spark_df["tempo"], spark_df["consultas"], "#009E73"),
                config={"displayModeBar": False, "staticPlot": True},
            ),
        ),
        kpi_card(
            "Urgências",
            f"{urgencias:,}".replace(",", " "),
            dcc.Graph(
                figure=create_sparkline(spark_df["tempo"], spark_df["urgencias"], "#D55E00"),
                config={"displayModeBar": False, "staticPlot": True},
            ),
        ),
        kpi_card(
            "Instituições",
            f"{instituicoes}",
            subtitle=f"{profissionais:,}".replace(",", " ") + f" profissionais | {periodos} períodos",
        ),
    ]

    # ========================================================
    # MAP
    # ========================================================

    fig_map = make_map(selected_region=selected_region, dff=dff)

    # ========================================================
    # ACTIVITY AREA
    # ========================================================

    atividade_df = (
        dff_region.groupby(["tempo", "zona_mapa"])
        .agg(
            consultas=("no_de_consultas_medicas_total", "sum"),
            urgencias=("total_urgencias", "sum"),
        )
        .reset_index()
        .sort_values("tempo")
    )

    atividade_df["atividade"] = atividade_df["consultas"] + atividade_df["urgencias"]

    fig_atividade = safe_area_figure(
        atividade_df,
        "Evolução da Atividade Assistencial",
    )

    # ========================================================
    # ACTIVITY BY INSTITUTION TYPE
    # ========================================================

    tipo_df = (
        dff_region
        .groupby(["zona_mapa", "tipo_instituicao"])
        .agg(
            consultas=("no_de_consultas_medicas_total", "sum"),
            urgencias=("total_urgencias", "sum"),
        )
        .reset_index()
    )

    tipo_df["atividade"] = tipo_df["consultas"] + tipo_df["urgencias"]

    fig_tipo = go.Figure()

    for i, regiao in enumerate(REGIOES):
        dfr = tipo_df[tipo_df["zona_mapa"] == regiao]

        if dfr.empty:
            continue

        fig_tipo.add_trace(
            go.Bar(
                x=dfr["tipo_instituicao"],
                y=dfr["atividade"],
                name=regiao,
                marker_color=COLORBLIND[i % len(COLORBLIND)],
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Atividade: %{y:,.0f}"
                    "<extra></extra>"
                ),
            )
        )

    fig_tipo.update_layout(
        title=dict(text="Atividade por Tipo de Instituição", x=0.03),
        height=420,
        barmode="group",
        margin=dict(l=30, r=30, t=90, b=90),
        yaxis=dict(title="Atividade"),
        xaxis=dict(title=None, tickangle=-25),
        legend=dict(orientation="h", y=1.12),
        plot_bgcolor="white",
    )

    # ========================================================
    # CAPACITY SCATTER
    # ========================================================

    capacidade_df = (
        dff_region.groupby(["instituicao", "zona_mapa"])
        .agg(
            consultas=("no_de_consultas_medicas_total", "sum"),
            urgencias=("total_urgencias", "sum"),
            medicos=("medicos_internos", "sum"),
            enfermeiros=("enfermeiros", "sum"),
        )
        .reset_index()
    )

    capacidade_df["atividade"] = capacidade_df["consultas"] + capacidade_df["urgencias"]
    capacidade_df["profissionais"] = capacidade_df["medicos"] + capacidade_df["enfermeiros"]
    capacidade_df = capacidade_df.replace([np.inf, -np.inf], np.nan).fillna(0)

    max_urgencias = capacidade_df["urgencias"].max()

    if pd.notna(max_urgencias) and max_urgencias > 0:
        capacidade_df["size"] = (capacidade_df["urgencias"] / max_urgencias * 42) + 8
    else:
        capacidade_df["size"] = 12

    fig_capacidade = go.Figure()

    for i, regiao in enumerate(REGIOES):
        dfr = capacidade_df[capacidade_df["zona_mapa"] == regiao]

        if dfr.empty:
            continue

        fig_capacidade.add_trace(
            go.Scatter(
                x=dfr["profissionais"],
                y=dfr["atividade"],
                mode="markers",
                name=regiao,
                marker=dict(
                    size=dfr["size"],
                    color=COLORBLIND[i % len(COLORBLIND)],
                    opacity=0.75,
                    line=dict(color="white", width=1),
                ),
                customdata=dfr[["instituicao", "consultas", "urgencias"]],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Profissionais: %{x:,.0f}<br>"
                    "Atividade: %{y:,.0f}<br>"
                    "Consultas: %{customdata[1]:,.0f}<br>"
                    "Urgências: %{customdata[2]:,.0f}"
                    "<extra></extra>"
                ),
            )
        )

    fig_capacidade.update_layout(
        title=dict(text="Capacidade Assistencial: Profissionais vs Atividade", x=0.03),
        height=400,
        margin=dict(l=30, r=30, t=90, b=40),
        xaxis=dict(title="Profissionais"),
        yaxis=dict(title="Atividade assistencial"),
        legend=dict(orientation="h", y=1.12),
        plot_bgcolor="white",
    )

    # ========================================================
    # DETAIL
    # ========================================================

    if selected_inst:
        detalhe = (
            dff_inst
            .groupby("tempo")
            .agg(
                consultas=("no_de_consultas_medicas_total", "sum"),
                urgencias=("total_urgencias", "sum"),
                medicos=("medicos_internos", "sum"),
                enfermeiros=("enfermeiros", "sum"),
            )
            .reset_index()
            .sort_values("tempo")
        )

        detalhe["profissionais"] = detalhe["medicos"] + detalhe["enfermeiros"]

        fig_detail = go.Figure()

        fig_detail.add_trace(
            go.Scatter(
                x=detalhe["tempo"],
                y=detalhe["consultas"],
                mode="lines+markers",
                name="Consultas",
                line=dict(color="#009E73", width=2.5),
                hovertemplate="Data: %{x|%Y-%m}<br>Consultas: %{y:,.0f}<extra></extra>",
            )
        )

        fig_detail.add_trace(
            go.Scatter(
                x=detalhe["tempo"],
                y=detalhe["urgencias"],
                mode="lines+markers",
                name="Urgências",
                line=dict(color="#D55E00", width=2.5),
                hovertemplate="Data: %{x|%Y-%m}<br>Urgências: %{y:,.0f}<extra></extra>",
            )
        )

        fig_detail.add_trace(
            go.Bar(
                x=detalhe["tempo"],
                y=detalhe["profissionais"],
                name="Profissionais",
                marker_color="rgba(0,114,178,0.35)",
                hovertemplate="Data: %{x|%Y-%m}<br>Profissionais: %{y:,.0f}<extra></extra>",
            )
        )

        fig_detail.update_layout(
            title=dict(text=f"Perfil Assistencial — {selected_inst}", x=0.03),
            height=400,
            margin=dict(l=30, r=30, t=90, b=40),
            legend=dict(orientation="h", y=1.12),
            yaxis=dict(title="Total"),
            plot_bgcolor="white",
        )

    else:
        region_df = (
            dff_region
            .groupby("zona_mapa")
            .agg(
                consultas=("no_de_consultas_medicas_total", "sum"),
                urgencias=("total_urgencias", "sum"),
            )
            .reindex(REGIOES)
            .fillna(0)
            .reset_index()
        )

        fig_detail = go.Figure()

        fig_detail.add_trace(
            go.Bar(
                x=region_df["zona_mapa"],
                y=region_df["consultas"],
                name="Consultas",
                marker_color="#009E73",
                hovertemplate="<b>%{x}</b><br>Consultas: %{y:,.0f}<extra></extra>",
            )
        )

        fig_detail.add_trace(
            go.Bar(
                x=region_df["zona_mapa"],
                y=region_df["urgencias"],
                name="Urgências",
                marker_color="#D55E00",
                hovertemplate="<b>%{x}</b><br>Urgências: %{y:,.0f}<extra></extra>",
            )
        )

        fig_detail.update_layout(
            title=dict(text="Consultas vs Urgências por Região", x=0.03),
            height=400,
            barmode="group",
            margin=dict(l=30, r=30, t=90, b=40),
            yaxis=dict(title="Total"),
            legend=dict(orientation="h", y=1.12),
            plot_bgcolor="white",
        )

    # ========================================================
    # TABLE
    # ========================================================

    inst = (
        dff_region
        .groupby("instituicao")
        .agg(
            consultas=("no_de_consultas_medicas_total", "sum"),
            urgencias=("total_urgencias", "sum"),
            medicos=("medicos_internos", "sum"),
            enfermeiros=("enfermeiros", "sum"),
            regiao=("zona_mapa", "first"),
        )
        .reset_index()
    )

    inst["atividade"] = inst["consultas"] + inst["urgencias"]
    inst["profissionais"] = inst["medicos"] + inst["enfermeiros"]

    table = inst[
        [
            "instituicao",
            "regiao",
            "atividade",
            "consultas",
            "urgencias",
            "profissionais",
        ]
    ].copy()

    table = table.sort_values("atividade", ascending=False)

    columns = [{"name": col, "id": col} for col in table.columns]

    return (
        subtitle,
        kpis,
        fig_map,
        fig_atividade,
        fig_tipo,
        fig_capacidade,
        fig_detail,
        table.to_dict("records"),
        columns,
    )