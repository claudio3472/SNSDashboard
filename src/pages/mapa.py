from dash import html, dcc, callback, Input, Output, no_update, ctx
from pages.pages_helper import load_data, process_data, create_sparkline, kpi_card

import pandas as pd
import numpy as np
import geopandas as gpd
import plotly.graph_objects as go
import re
from shapely.geometry import Point, Polygon


# ============================================================
# DATA
# ============================================================

df = process_data(load_data())

df["ano"] = df["ano"].astype(int)
df["mes"] = df["mes"].astype(int)
df["tempo"] = pd.to_datetime(dict(year=df["ano"], month=df["mes"], day=1))

MIN_DATE = df["tempo"].min().date()
MAX_DATE = df["tempo"].max().date()

REGIOES = ["Norte", "Centro", "Lisboa e Vale do Tejo", "Alentejo", "Algarve"]

COLORBLIND = [
    "#0072B2",
    "#E69F00",
    "#009E73",
    "#CC79A7",
    "#D55E00",
    "#56B4E9",
]

ACTIVITY_SCALE = [
    [0.0, "#F7F7F7"],
    [0.2, COLORBLIND[5]],
    [0.4, COLORBLIND[0]],
    [0.6, COLORBLIND[2]],
    [0.8, COLORBLIND[1]],
    [1.0, COLORBLIND[4]],
]

for col in [
    "no_de_consultas_medicas_total",
    "total_urgencias",
    "medicos_internos",
    "enfermeiros",
]:
    if col not in df.columns:
        df[col] = 0
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

if "tipo_instituicao" not in df.columns:
    df["tipo_instituicao"] = "Instituição"

df["tipo_instituicao"] = (
    df["tipo_instituicao"]
    .astype(str)
    .str.strip()
)

df = df[
    ~df["tipo_instituicao"]
    .str.lower()
    .str.contains("csp|outro|sns|hospital", na=False)
].copy()

CUMULATIVE_COLS = [
    "no_de_consultas_medicas_total",
    "total_urgencias",
]

df = df.sort_values(["instituicao", "ano", "mes"]).copy()

for col in CUMULATIVE_COLS:
    original = df[col].copy()

    df[col] = (
        df.groupby(["instituicao", "ano"])[col]
        .diff()
        .fillna(original)
    )

    df[col] = df[col].clip(lower=0)


# ============================================================
# GEO
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


ZONE_POLYGONS = {
    "Norte": Polygon([(-9.00, 40.75), (-6.00, 40.75), (-6.00, 42.35), (-9.00, 42.35)]),
    "Centro": Polygon([(-9.25, 39.20), (-6.00, 39.20), (-6.00, 40.75), (-9.25, 40.75)]),
    "Lisboa e Vale do Tejo": Polygon([(-9.65, 38.25), (-7.45, 38.25), (-7.45, 39.75), (-9.65, 39.75)]),
    "Alentejo": Polygon([(-9.25, 37.20), (-6.60, 37.20), (-6.60, 39.20), (-9.25, 39.20)]),
    "Algarve": Polygon([(-9.10, 36.80), (-7.20, 36.80), (-7.20, 37.45), (-9.10, 37.45)]),
}

REGIAO_COORDS = {
    "Norte": {"lat": 41.35, "lon": -8.20, "color": "#0072B2"},
    "Centro": {"lat": 40.20, "lon": -8.15, "color": "#E69F00"},
    "Lisboa e Vale do Tejo": {"lat": 38.80, "lon": -9.05, "color": "#009E73"},
    "Alentejo": {"lat": 38.10, "lon": -7.85, "color": "#CC79A7"},
    "Algarve": {"lat": 37.10, "lon": -8.10, "color": "#D55E00"},
}

REGION_BOUNDS = {
    "Norte": {"lon": [-8.95, -6.15], "lat": [40.70, 42.30]},
    "Centro": {"lon": [-9.25, -6.25], "lat": [39.15, 40.85]},
    "Lisboa e Vale do Tejo": {"lon": [-9.65, -7.35], "lat": [38.20, 39.75]},
    "Alentejo": {"lon": [-9.25, -6.55], "lat": [37.20, 39.25]},
    "Algarve": {"lon": [-9.10, -7.15], "lat": [36.90, 37.45]},
}


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


gdf = gpd.read_file("src/map/geoBoundaries-PRT-ADM3.shp").to_crs(epsg=4326)


def make_unique_columns(cols):
    seen = {}
    output = []

    for col in cols:
        if col not in seen:
            seen[col] = 0
            output.append(col)
        else:
            seen[col] += 1
            output.append(f"{col}_{seen[col]}")

    return output


gdf.columns = make_unique_columns(gdf.columns)
gdf["map_id"] = gdf.index.astype(str)
gdf["geometry"] = gdf["geometry"].simplify(0.01, preserve_topology=True)

gdf_points = gdf.copy()
gdf_points["point"] = gdf_points.geometry.representative_point()

gdf["lon"] = gdf_points["point"].x
gdf["lat"] = gdf_points["point"].y

gdf["zona_mapa"] = gdf.apply(
    lambda row: assign_zone(row["lat"], row["lon"], None),
    axis=1,
)

geojson_map = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": row["map_id"],
            "properties": {
                "map_id": row["map_id"],
                "zona_mapa": row["zona_mapa"],
            },
            "geometry": row["geometry"].__geo_interface__,
        }
        for _, row in gdf.iterrows()
    ],
}


# ============================================================
# HELPERS
# ============================================================

def empty_fig(title):
    fig = go.Figure()

    fig.update_layout(
        title=dict(text=title, x=0.03),
        height=400,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text="Sem dados para os filtros selecionados",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
            )
        ],
        margin=dict(l=30, r=30, t=80, b=40),
    )

    return fig


def base_layout(fig, title, height=400):
    fig.update_layout(
        title=dict(text=title, x=0.03),
        height=height,
        margin=dict(l=30, r=30, t=80, b=40),
        plot_bgcolor="white",
        separators=", ",
    )
    return fig


def filter_period(start_date, end_date):
    dff = df.copy()

    if not end_date:
        end_date = dff["tempo"].max()

    end_date = pd.to_datetime(end_date)

    if start_date:
        dff = dff[dff["tempo"] >= pd.to_datetime(start_date)]

    return dff[dff["tempo"] <= end_date]


def spark(x, y, color):
    return dcc.Graph(
        figure=create_sparkline(x, y, color),
        config={"displayModeBar": False, "staticPlot": True},
    )


# ============================================================
# LAYOUT
# ============================================================

layout = html.Div(
    className="content",
    children=[
        dcc.Store(id="mapa-region"),

        html.Div(
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "flex-start",
                "gap": "20px",
                "flexWrap": "wrap",
                "marginBottom": "18px",
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
                        "alignItems": "flex-end",
                        "justifyContent": "flex-end",
                        "flexWrap": "wrap",
                        "paddingTop": "4px",
                    },
                    children=[
                        html.Button(
                            "Voltar às regiões",
                            id="btn-reset-region",
                            n_clicks=0,
                            className="reset-btn",
                        ),

                        html.Div([
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
                        ]),

                        html.Div([
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
                        ]),
                    ],
                ),
            ],
        ),

        html.Div(id="mapa-kpis", className="kpi-row"),

        html.Div(
            className="card",
            style={"marginBottom": "20px"},
            children=[
                dcc.Graph(
                    id="mapa-portugal",
                    config={"displayModeBar": False},
                )
            ],
        ),

        html.Div(
            className="grid-2x2",
            children=[
                html.Div(className="card", children=[dcc.Graph(id="mapa-atividade", config={"displayModeBar": False})]),
                html.Div(className="card", children=[dcc.Graph(id="mapa-tipo", config={"displayModeBar": False})]),
                html.Div(className="card", children=[dcc.Graph(id="mapa-capacidade", config={"displayModeBar": False})]),
                html.Div(className="card", children=[dcc.Graph(id="mapa-detail", config={"displayModeBar": False})]),
            ],
        ),
    ],
)


# ============================================================
# CALLBACK — SELECTION
# ============================================================

@callback(
    Output("mapa-region", "data"),
    Input("mapa-portugal", "clickData"),
    Input("btn-reset-region", "n_clicks"),
    prevent_initial_call=True,
)
def update_selection(map_click, reset_region):
    trigger = ctx.triggered_id

    if trigger == "btn-reset-region":
        return None

    if trigger == "mapa-portugal" and map_click:
        point = map_click["points"][0]
        custom = point.get("customdata")

        if isinstance(custom, list):
            if len(custom) >= 2 and custom[0] == "region":
                return custom[1]

            if len(custom) >= 1 and custom[0] in REGIOES:
                return custom[0]

    return no_update


# ============================================================
# CALLBACK — DASHBOARD
# ============================================================

@callback(
    Output("mapa-subtitle", "children"),
    Output("mapa-kpis", "children"),
    Output("mapa-portugal", "figure"),
    Output("mapa-atividade", "figure"),
    Output("mapa-tipo", "figure"),
    Output("mapa-capacidade", "figure"),
    Output("mapa-detail", "figure"),
    Input("mapa-start-date", "date"),
    Input("mapa-end-date", "date"),
    Input("mapa-region", "data"),
)
def update_dashboard(start_date, end_date, selected_region):
    dff = filter_period(start_date, end_date)

    if selected_region:
        dff_region = dff[dff["zona_mapa"] == selected_region].copy()
    else:
        dff_region = dff.copy()

    real_end = end_date or str(MAX_DATE)
    subtitle = f"Período: {start_date} a {real_end} | Nível: {selected_region or 'Portugal'}"

    if dff_region.empty:
        return (
            subtitle,
            [
                kpi_card("Atividade Total", "0"),
                kpi_card("Consultas", "0"),
                kpi_card("Urgências", "0"),
                kpi_card("Instituições", "0"),
            ],
            empty_fig("Mapa de Atividade Assistencial"),
            empty_fig("Evolução da Atividade Assistencial"),
            empty_fig("Atividade por Tipo de Instituição"),
            empty_fig("Capacidade Assistencial"),
            empty_fig("Consultas vs Urgências por Região"),
        )

    # ========================================================
    # KPIS
    # ========================================================

    consultas = int(dff_region["no_de_consultas_medicas_total"].sum())
    urgencias = int(dff_region["total_urgencias"].sum())
    atividade = consultas + urgencias
    profissionais = int((dff_region["medicos_internos"] + dff_region["enfermeiros"]).sum())

    spark_df = (
        dff_region.groupby("tempo")
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

    kpis = [
        kpi_card(
            "Atividade Total",
            f"{atividade:,}".replace(",", " "),
            spark(spark_df["tempo"], spark_df["atividade"], COLORBLIND[0]),
        ),
        kpi_card(
            "Consultas",
            f"{consultas:,}".replace(",", " "),
            spark(spark_df["tempo"], spark_df["consultas"], COLORBLIND[2]),
        ),
        kpi_card(
            "Urgências",
            f"{urgencias:,}".replace(",", " "),
            spark(spark_df["tempo"], spark_df["urgencias"], COLORBLIND[4]),
        ),
        kpi_card(
            "Instituições",
            f"{dff_region['instituicao'].nunique()}",
            html.Div(
                f"{profissionais:,}".replace(",", " ")
                + f" profissionais | {dff_region['tempo'].nunique()} períodos",
                className="kpi-subtitle",
                style={"marginTop": "10px"},
            ),
        ),
    ]

    # ========================================================
    # MAP
    # ========================================================

    map_data = (
        dff.groupby("zona_mapa")
        .agg(
            consultas=("no_de_consultas_medicas_total", "sum"),
            urgencias=("total_urgencias", "sum"),
            instituicoes=("instituicao", "nunique"),
            meses=("tempo", "nunique"),
        )
        .reindex(REGIOES)
        .fillna(0)
        .reset_index()
    )

    map_data["atividade"] = map_data["consultas"] + map_data["urgencias"]

    map_data["atividade_media_mensal"] = np.where(
        (map_data["meses"] > 0) & (map_data["instituicoes"] > 0),
        map_data["atividade"] / map_data["meses"] / map_data["instituicoes"],
        0,
    )

    map_data["atividade_m"] = map_data["atividade_media_mensal"] / 1e6

    map_df = (
        gdf[["map_id", "zona_mapa"]]
        .drop_duplicates()
        .merge(
            map_data[["zona_mapa", "atividade_m"]],
            on="zona_mapa",
            how="left",
        )
    )

    map_df["atividade_m"] = map_df["atividade_m"].fillna(0)

    if selected_region:
        map_df.loc[map_df["zona_mapa"] != selected_region, "atividade_m"] = 0

    fig_map = go.Figure()

    fig_map.add_trace(
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
                "Média mensal por instituição: %{customdata[1]:.3f} M"
                "<extra></extra>"
            ),
            colorbar=dict(
                title="Média mensal<br>por instituição<br>(M)",
                thickness=12,
            ),
        )
    )

    if not selected_region:
        for regiao, info in REGIAO_COORDS.items():
            fig_map.add_trace(
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
                )
            )

    if selected_region:
        inst_points = (
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

        inst_points["atividade"] = inst_points["consultas"] + inst_points["urgencias"]
        max_atividade = inst_points["atividade"].max()

        if max_atividade > 0:
            inst_points["size"] = (inst_points["atividade"] / max_atividade * 38) + 8
        else:
            inst_points["size"] = 12

        if not inst_points.empty:
            fig_map.add_trace(
                go.Scattergeo(
                    lon=inst_points["lon"],
                    lat=inst_points["lat"],
                    mode="markers",
                    marker=dict(
                        size=inst_points["size"],
                        color="#111827",
                        opacity=0.78,
                        line=dict(color="white", width=1),
                    ),
                    customdata=inst_points[["instituicao", "consultas", "urgencias"]],
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Consultas: %{customdata[1]:,.0f}<br>"
                        "Urgências: %{customdata[2]:,.0f}"
                        "<extra></extra>"
                    ),
                )
            )

    if selected_region:
        lon_range = REGION_BOUNDS[selected_region]["lon"]
        lat_range = REGION_BOUNDS[selected_region]["lat"]
    else:
        lon_range = [-9.7, -6.0]
        lat_range = [36.8, 42.3]

    fig_map.update_geos(
        visible=False,
        projection_type="mercator",
        lonaxis=dict(range=lon_range),
        lataxis=dict(range=lat_range),
    )

    fig_map.update_layout(
        title=dict(
            text=f"Mapa de Atividade — {selected_region}" if selected_region else "Mapa de Atividade Assistencial",
            x=0.03,
        ),
        height=580,
        margin=dict(l=0, r=0, t=60, b=0),
        showlegend=False,
        dragmode=False,
        separators=", ",
    )

    # ========================================================
    # AREA
    # ========================================================

    area = (
        dff_region.groupby(["tempo", "zona_mapa"])
        .agg(
            consultas=("no_de_consultas_medicas_total", "sum"),
            urgencias=("total_urgencias", "sum"),
        )
        .reset_index()
        .sort_values("tempo")
    )

    area["atividade"] = area["consultas"] + area["urgencias"]

    fig_area = go.Figure()

    for i, regiao in enumerate(REGIOES):
        dfr = area[area["zona_mapa"] == regiao]

        if dfr.empty:
            continue

        fig_area.add_trace(
            go.Scatter(
                x=dfr["tempo"],
                y=dfr["atividade"],
                mode="lines",
                stackgroup="one",
                name=regiao,
                line=dict(color=COLORBLIND[i % len(COLORBLIND)], width=2),
                hovertemplate="Data: %{x|%Y-%m}<br>Atividade: %{y:,.0f}<extra></extra>",
            )
        )

    fig_area = base_layout(fig_area, "Evolução da Atividade Assistencial")
    fig_area.update_layout(
        yaxis=dict(title="Atividade"),
        xaxis=dict(title=None),
        legend=dict(orientation="h", y=1.12),
    )

    # ========================================================
    # TYPE BAR
    # ========================================================

    tipo = (
        dff_region.groupby(["zona_mapa", "tipo_instituicao"])
        .agg(
            consultas=("no_de_consultas_medicas_total", "sum"),
            urgencias=("total_urgencias", "sum"),
        )
        .reset_index()
    )

    tipo["atividade"] = tipo["consultas"] + tipo["urgencias"]

    fig_tipo = go.Figure()

    for i, regiao in enumerate(REGIOES):
        dfr = tipo[tipo["zona_mapa"] == regiao]

        if dfr.empty:
            continue

        fig_tipo.add_bar(
            x=dfr["tipo_instituicao"],
            y=dfr["atividade"],
            name=regiao,
            marker_color=COLORBLIND[i % len(COLORBLIND)],
            hovertemplate="<b>%{x}</b><br>Atividade: %{y:,.0f}<extra></extra>",
        )

    fig_tipo = base_layout(fig_tipo, "Atividade por Tipo de Instituição", height=420)
    fig_tipo.update_layout(
        barmode="group",
        yaxis=dict(title="Atividade"),
        xaxis=dict(title=None, tickangle=-25),
        legend=dict(orientation="h", y=1.12),
    )

    # ========================================================
    # CAPACITY
    # ========================================================

    cap = (
        dff_region.groupby(["instituicao", "zona_mapa"])
        .agg(
            consultas=("no_de_consultas_medicas_total", "sum"),
            urgencias=("total_urgencias", "sum"),
            medicos=("medicos_internos", "sum"),
            enfermeiros=("enfermeiros", "sum"),
        )
        .reset_index()
    )

    cap["atividade"] = cap["consultas"] + cap["urgencias"]
    cap["profissionais"] = cap["medicos"] + cap["enfermeiros"]

    max_urg = cap["urgencias"].max()

    if max_urg > 0:
        cap["size"] = (cap["urgencias"] / max_urg * 42) + 8
    else:
        cap["size"] = 12

    fig_cap = go.Figure()

    for i, regiao in enumerate(REGIOES):
        dfr = cap[cap["zona_mapa"] == regiao]

        if dfr.empty:
            continue

        fig_cap.add_trace(
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

    fig_cap = base_layout(fig_cap, "Capacidade Assistencial: Profissionais vs Atividade")
    fig_cap.update_layout(
        xaxis=dict(title="Profissionais"),
        yaxis=dict(title="Atividade assistencial"),
        legend=dict(orientation="h", y=1.12),
    )

    # ========================================================
    # DETAIL
    # ========================================================

    region_data = (
        dff_region.groupby("zona_mapa")
        .agg(
            consultas=("no_de_consultas_medicas_total", "sum"),
            urgencias=("total_urgencias", "sum"),
        )
        .reindex(REGIOES)
        .fillna(0)
        .reset_index()
    )

    fig_detail = go.Figure()

    fig_detail.add_bar(
        x=region_data["zona_mapa"],
        y=region_data["consultas"],
        name="Consultas",
        marker_color=COLORBLIND[2],
    )

    fig_detail.add_bar(
        x=region_data["zona_mapa"],
        y=region_data["urgencias"],
        name="Urgências",
        marker_color=COLORBLIND[4],
    )

    fig_detail = base_layout(fig_detail, "Consultas vs Urgências por Região")
    fig_detail.update_layout(
        barmode="group",
        yaxis=dict(title="Total"),
        legend=dict(orientation="h", y=1.12),
    )

    return (
        subtitle,
        kpis,
        fig_map,
        fig_area,
        fig_tipo,
        fig_cap,
        fig_detail,
    )