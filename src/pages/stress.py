# ============================================================
# stress.py
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
import plotly.express as px
from shapely.geometry import Point, Polygon
import re

# ============================================================
# DATA LOAD
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
# GEOLOCATION
# ============================================================

def parse_localizacao(value):
    if pd.isna(value):
        return pd.Series([None, None])

    nums = re.findall(r"-?\d+\.\d+|-?\d+", str(value))

    if len(nums) < 2:
        return pd.Series([None, None])

    return pd.Series([float(nums[0]), float(nums[1])])


if "localizacao_geografica" in df.columns:
    df[["lat", "lon"]] = df["localizacao_geografica"].apply(parse_localizacao)
else:
    df["lat"] = np.nan
    df["lon"] = np.nan

df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

# ============================================================
# STRESS INDEX
# ============================================================

df["total_staff"] = df["medicos_internos"] + df["enfermeiros"]

df["stress_index"] = (
    df["total_urgencias"]
    / df["total_staff"].replace(0, np.nan)
) * 10

df["stress_index"] = (
    df["stress_index"]
    .replace([np.inf, -np.inf], np.nan)
    .fillna(0)
)

df["total_cirurgias"] = (
    df.get("no_intervencoes_cirurgicas_programadas", 0)
    + df.get("no_intervencoes_cirurgicas_convencionais", 0)
    + df.get("no_intervencoes_cirurgicas_urgentes", 0)
)

# ============================================================
# MAP LOAD
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

gdf["geometry"] = gdf["geometry"].simplify(
    0.002,
    preserve_topology=True,
)

# ============================================================
# MAP ZONES
# ============================================================

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


def assign_zone(lat, lon, fallback=None):
    if pd.isna(lat) or pd.isna(lon):
        return fallback

    point = Point(lon, lat)

    for zone, polygon in ZONE_POLYGONS.items():
        if polygon.contains(point):
            return zone

    return fallback


df["zona_mapa"] = df.apply(
    lambda row: assign_zone(
        row["lat"],
        row["lon"],
        row["regiao"],
    ),
    axis=1,
)

gdf_points = gdf.copy()
gdf_points["point"] = gdf_points.geometry.representative_point()
gdf["lon"] = gdf_points["point"].x
gdf["lat"] = gdf_points["point"].y

gdf["zona_mapa"] = gdf.apply(
    lambda row: assign_zone(
        row["lat"],
        row["lon"],
        None,
    ),
    axis=1,
)

geojson_map = gdf.__geo_interface__

# ============================================================
# CONSTANTS
# ============================================================

REGIOES = [
    "Norte",
    "Centro",
    "Lisboa e Vale do Tejo",
    "Alentejo",
    "Algarve",
]

REGIAO_COORDS = {
    "Norte": {"lat": 41.35, "lon": -8.20},
    "Centro": {"lat": 40.20, "lon": -8.15},
    "Lisboa e Vale do Tejo": {"lat": 38.80, "lon": -9.05},
    "Alentejo": {"lat": 38.10, "lon": -7.85},
    "Algarve": {"lat": 37.10, "lon": -8.10},
}

REGION_BOUNDS = {
    "Norte": {"lon": [-8.95, -6.15], "lat": [40.70, 42.30]},
    "Centro": {"lon": [-9.25, -6.25], "lat": [39.15, 40.85]},
    "Lisboa e Vale do Tejo": {"lon": [-9.65, -7.35], "lat": [38.20, 39.75]},
    "Alentejo": {"lon": [-9.25, -6.55], "lat": [37.20, 39.25]},
    "Algarve": {"lon": [-9.10, -7.15], "lat": [36.90, 37.45]},
}

STRESS_COLORSCALE = [
    [0.0, "#2C7BB6"],
    [0.25, "#74ADD1"],
    [0.5, "#ABDDA4"],
    [0.75, "#FDAE61"],
    [1.0, "#D7191C"],
]

COLORBLIND = [
    "#0072B2",
    "#E69F00",
    "#009E73",
    "#D55E00",
    "#CC79A7",
    "#56B4E9",
]

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


def make_empty_figure(title, text="Sem dados para os filtros selecionados"):
    fig = go.Figure()

    fig.update_layout(
        title=dict(text=title, x=0.03),
        height=380,
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


def make_stress_map(selected_region=None, dff=None):
    if dff is None:
        dff = df.copy()

    stress_region = (
        dff.groupby("zona_mapa")
        .agg(
            total_urgencias=("total_urgencias", "sum"),
            total_staff=("total_staff", "sum"),
            instituicoes=("instituicao", "nunique"),
        )
        .reindex(REGIOES)
        .reset_index()
    )

    stress_region["stress_index"] = (
        stress_region["total_urgencias"]
        / stress_region["total_staff"].replace(0, np.nan)
    ) * 10

    stress_region["stress_index"] = (
        stress_region["stress_index"]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )

    q95 = stress_region["stress_index"].quantile(0.95)

    if q95 > 0:
        stress_region["stress_index"] = stress_region["stress_index"].clip(
            upper=q95
        )

    map_df = gdf[["map_id", "zona_mapa"]].drop_duplicates().copy()

    map_df = map_df.merge(
        stress_region[
            [
                "zona_mapa",
                "stress_index",
                "instituicoes",
            ]
        ],
        on="zona_mapa",
        how="left",
    )

    map_df["stress_index"] = (
        map_df["stress_index"]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )

    map_df["instituicoes"] = map_df["instituicoes"].fillna(0)

    if selected_region:
        map_df.loc[
            map_df["zona_mapa"] != selected_region,
            "stress_index"
        ] = 0

    fig = go.Figure()

    fig.add_trace(
        go.Choropleth(
            geojson=geojson_map,
            locations=map_df["map_id"],
            z=map_df["stress_index"],
            featureidkey="properties.map_id",
            colorscale=STRESS_COLORSCALE,
            showscale=True,
            marker_line_color="white",
            marker_line_width=0.35,
            customdata=map_df[
                [
                    "zona_mapa",
                    "stress_index",
                    "instituicoes",
                ]
            ],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Stress: %{customdata[1]:.2f}<br>"
                "Instituições: %{customdata[2]:.0f}"
                "<extra></extra>"
            ),
            colorbar=dict(title="Stress", thickness=12),
            name="Stress",
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
                        size=38,
                        color="rgba(255,255,255,0.65)",
                        opacity=0.95,
                        line=dict(color="#111827", width=1.4),
                    ),
                    textposition="middle center",
                    textfont=dict(color="#111827", size=11),
                    hovertemplate="<b>%{customdata[1]}</b><extra></extra>",
                    name=regiao,
                )
            )

    if selected_region:
        points = (
            dff[
                (dff["zona_mapa"] == selected_region)
                & dff["lat"].notna()
                & dff["lon"].notna()
            ]
            .groupby(["instituicao", "zona_mapa", "lat", "lon"])
            .agg(
                stress=("stress_index", "mean"),
                urgencias=("total_urgencias", "sum"),
                staff=("total_staff", "sum"),
            )
            .reset_index()
        )

        points["stress"] = (
            points["stress"]
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0)
        )

        if not points.empty:
            fig.add_trace(
                go.Scattergeo(
                    lon=points["lon"],
                    lat=points["lat"],
                    mode="markers",
                    text=points["instituicao"],
                    customdata=points[
                        [
                            "instituicao",
                            "zona_mapa",
                            "stress",
                            "urgencias",
                            "staff",
                        ]
                    ],
                    marker=dict(
                        size=13,
                        color="#111827",
                        opacity=0.85,
                        line=dict(color="white", width=1.2),
                    ),
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Zona: %{customdata[1]}<br>"
                        "Stress: %{customdata[2]:.2f}<br>"
                        "Urgências: %{customdata[3]:,.0f}<br>"
                        "Staff: %{customdata[4]:,.0f}"
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
                f"Mapa de Stress — {selected_region}"
                if selected_region
                else "Mapa de Stress por Região"
            ),
            x=0.03,
            font=dict(size=16),
        ),
        height=560,
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
        dcc.Store(id="stress-region"),
        dcc.Store(id="stress-inst"),

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
                    html.H2("Stress Hospitalar"),
                    html.P(id="stress-subtitle"),
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
                            id="stress-reset-region",
                            n_clicks=0,
                            className="reset-btn",
                        ),

                        html.Button(
                            "Limpar instituição",
                            id="stress-reset-inst",
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
                                    id="stress-start-date",
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
                                    id="stress-end-date",
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

        html.Div(
            id="stress-kpis",
            className="kpi-row",
        ),

        html.Div(
            className="card",
            style={"marginBottom": "20px"},
            children=[
                dcc.Graph(
                    id="stress-map",
                    config={"displayModeBar": False},
                ),
            ],
        ),

        html.Div(
            className="grid-2x2",
            children=[
                html.Div(
                    className="card",
                    children=dcc.Graph(
                        id="stress-ts",
                        config={"displayModeBar": False},
                    ),
                ),

                html.Div(
                    className="card",
                    children=dcc.Graph(
                        id="stress-bubble",
                        config={"displayModeBar": False},
                    ),
                ),

                html.Div(
                    className="card",
                    children=dcc.Graph(
                        id="stress-heatmap",
                        config={"displayModeBar": False},
                    ),
                ),

                html.Div(
                    className="card",
                    children=dcc.Graph(
                        id="stress-parcoords",
                        config={"displayModeBar": False},
                    ),
                ),
            ],
        ),

        html.Div(
            className="card",
            children=[
                html.H4("Instituições"),

                dash_table.DataTable(
                    id="stress-table",
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
    Output("stress-region", "data"),
    Output("stress-inst", "data"),

    Input("stress-map", "clickData"),
    Input("stress-table", "active_cell"),
    Input("stress-reset-region", "n_clicks"),
    Input("stress-reset-inst", "n_clicks"),

    State("stress-table", "data"),
    State("stress-region", "data"),

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

    if trigger == "stress-reset-region":
        return None, None

    if trigger == "stress-reset-inst":
        return current_region, None

    if trigger == "stress-table" and active_cell and table_data:
        row = active_cell["row"]
        inst = table_data[row]["instituicao"]

        return current_region, inst

    if trigger == "stress-map" and map_click:
        point = map_click["points"][0]

        if "customdata" not in point:
            return no_update, no_update

        custom = point["customdata"]

        if isinstance(custom, list):
            if len(custom) >= 2 and custom[0] == "region":
                return custom[1], None

            if len(custom) >= 1 and custom[0] in REGIOES:
                return custom[0], None

            if len(custom) >= 1:
                return current_region, custom[0]

    return no_update, no_update

# ============================================================
# UPDATE DASHBOARD
# ============================================================

@callback(
    Output("stress-subtitle", "children"),
    Output("stress-kpis", "children"),
    Output("stress-map", "figure"),
    Output("stress-ts", "figure"),
    Output("stress-bubble", "figure"),
    Output("stress-heatmap", "figure"),
    Output("stress-parcoords", "figure"),
    Output("stress-table", "data"),
    Output("stress-table", "columns"),

    Input("stress-start-date", "date"),
    Input("stress-end-date", "date"),
    Input("stress-region", "data"),
    Input("stress-inst", "data"),
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
        dff_inst = dff_region[
            dff_region["instituicao"] == selected_inst
        ].copy()
    else:
        dff_inst = dff_region.copy()

    real_end = end_date or str(MAX_DATE)

    subtitle = f"Período: {start_date} a {real_end} | Nível: {selected_region or 'Portugal'}"

    if selected_inst:
        subtitle += f" → {selected_inst}"

    if dff_inst.empty:
        kpis = [
            kpi_card("Stress Médio", "0.00"),
            kpi_card("Urgências", "0"),
            kpi_card("Profissionais", "0"),
            kpi_card("Instituições", "0"),
        ]

        return (
            subtitle,
            kpis,
            make_stress_map(selected_region=selected_region, dff=dff),
            make_empty_figure("Evolução do Índice de Stress"),
            make_empty_figure("Profissionais vs Urgências"),
            make_empty_figure("Heatmap Mensal de Stress"),
            make_empty_figure("Padrões Assistenciais"),
            [],
            [],
        )

    # ========================================================
    # KPIs WITH SPARKLINES
    # ========================================================

    total_urgencias = int(dff_inst["total_urgencias"].sum())
    total_staff = int(dff_inst["total_staff"].sum())

    stress_medio = (
        total_urgencias / total_staff * 10
        if total_staff > 0
        else 0
    )

    instituicoes = dff_inst["instituicao"].nunique()
    periodos = dff_inst["tempo"].nunique()

    spark_df = (
        dff_inst.groupby("tempo")
        .agg(
            urgencias=("total_urgencias", "sum"),
            staff=("total_staff", "sum"),
            stress=("stress_index", "mean"),
        )
        .reset_index()
        .sort_values("tempo")
    )

    kpis = [
        kpi_card(
            "Stress Médio",
            f"{stress_medio:,.2f}",
            dcc.Graph(
                figure=create_sparkline(
                    spark_df["tempo"],
                    spark_df["stress"],
                    "#D55E00",
                ),
                config={"displayModeBar": False, "staticPlot": True},
            ),
            color="#D55E00",
        ),

        kpi_card(
            "Urgências",
            f"{total_urgencias:,}".replace(",", " "),
            dcc.Graph(
                figure=create_sparkline(
                    spark_df["tempo"],
                    spark_df["urgencias"],
                    "#0072B2",
                ),
                config={"displayModeBar": False, "staticPlot": True},
            ),
        ),

        kpi_card(
            "Profissionais",
            f"{total_staff:,}".replace(",", " "),
            dcc.Graph(
                figure=create_sparkline(
                    spark_df["tempo"],
                    spark_df["staff"],
                    "#009E73",
                ),
                config={"displayModeBar": False, "staticPlot": True},
            ),
        ),

        kpi_card(
            "Instituições",
            f"{instituicoes}",
            subtitle=f"{periodos} períodos analisados",
        ),
    ]

    # ========================================================
    # MAP
    # ========================================================

    fig_map = make_stress_map(
        selected_region=selected_region,
        dff=dff,
    )

    # ========================================================
    # TEMPORAL STRESS
    # ========================================================

    stress_ts = (
        dff_inst.groupby("tempo")
        .agg(
            stress=("stress_index", "mean"),
            urgencias=("total_urgencias", "sum"),
            staff=("total_staff", "sum"),
        )
        .reset_index()
        .sort_values("tempo")
    )

    stress_ts["rolling_3m"] = stress_ts["stress"].rolling(3).mean()
    benchmark = stress_ts["stress"].mean()

    fig_ts = go.Figure()

    fig_ts.add_trace(
        go.Scatter(
            x=stress_ts["tempo"],
            y=stress_ts["stress"],
            name="Stress",
            mode="lines+markers",
            line=dict(color="#0072B2", width=2.5),
            hovertemplate="Data: %{x|%Y-%m}<br>Stress: %{y:.2f}<extra></extra>",
        )
    )

    fig_ts.add_trace(
        go.Scatter(
            x=stress_ts["tempo"],
            y=stress_ts["rolling_3m"],
            name="Tendência 3m",
            mode="lines",
            line=dict(color="#D55E00", width=3, dash="dot"),
            hovertemplate="Data: %{x|%Y-%m}<br>Tendência: %{y:.2f}<extra></extra>",
        )
    )

    if not np.isnan(benchmark):
        fig_ts.add_hline(
            y=benchmark,
            line_dash="dash",
            line_color="#6B7280",
            annotation_text="Média do período",
        )

    fig_ts.update_layout(
        title=dict(
            text="Evolução do Índice de Stress",
            x=0.03,
            font=dict(size=16),
        ),
        height=380,
        margin=dict(l=30, r=30, t=90, b=40),
        legend=dict(orientation="h", y=1.12),
        yaxis=dict(title="Stress"),
        plot_bgcolor="white",
    )

    # ========================================================
    # BUBBLE CHART
    # ========================================================

    bubble_df = (
        dff_region.groupby(["instituicao", "zona_mapa"])
        .agg(
            total_staff=("total_staff", "sum"),
            total_urgencias=("total_urgencias", "sum"),
            stress=("stress_index", "mean"),
        )
        .reset_index()
    )

    bubble_df["stress"] = (
        bubble_df["stress"]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )

    bubble_df["bubble_size"] = bubble_df["stress"].clip(lower=0)

    if bubble_df["bubble_size"].max() > 0:
        bubble_df["bubble_size"] = (
            bubble_df["bubble_size"]
            / bubble_df["bubble_size"].max()
            * 42
        ) + 8
    else:
        bubble_df["bubble_size"] = 12

    fig_bubble = go.Figure()

    for i, regiao in enumerate(REGIOES):
        dfr = bubble_df[bubble_df["zona_mapa"] == regiao]

        if dfr.empty:
            continue

        fig_bubble.add_trace(
            go.Scatter(
                x=dfr["total_staff"],
                y=dfr["total_urgencias"],
                mode="markers",
                name=regiao,
                marker=dict(
                    size=dfr["bubble_size"],
                    color=COLORBLIND[i % len(COLORBLIND)],
                    opacity=0.75,
                    line=dict(color="white", width=1),
                ),
                customdata=dfr[["instituicao", "stress"]],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Profissionais: %{x:,.0f}<br>"
                    "Urgências: %{y:,.0f}<br>"
                    "Stress: %{customdata[1]:.2f}"
                    "<extra></extra>"
                ),
            )
        )

    if not bubble_df.empty:
        fig_bubble.add_vline(
            x=bubble_df["total_staff"].mean(),
            line_dash="dash",
            line_color="#6B7280",
            annotation_text="Média staff",
        )
        fig_bubble.add_hline(
            y=bubble_df["total_urgencias"].mean(),
            line_dash="dash",
            line_color="#6B7280",
            annotation_text="Média urgências",
        )

    fig_bubble.update_layout(
        title=dict(
            text=(
                f"Instituições: Profissionais vs Urgências — {selected_region}"
                if selected_region
                else "Instituições: Profissionais vs Urgências"
            ),
            x=0.03,
            font=dict(size=16),
        ),
        height=380,
        margin=dict(l=30, r=30, t=90, b=40),
        xaxis=dict(title="Profissionais"),
        yaxis=dict(title="Urgências"),
        legend=dict(orientation="h", y=1.12),
        plot_bgcolor="white",
    )

    # ========================================================
    # MONTHLY HEATMAP
    # ========================================================

    heatmap_df = (
        dff_region.groupby(["zona_mapa", "tempo"])
        .agg(
            total_urgencias=("total_urgencias", "sum"),
            total_staff=("total_staff", "sum"),
        )
        .reset_index()
    )

    heatmap_df["stress"] = (
        heatmap_df["total_urgencias"]
        / heatmap_df["total_staff"].replace(0, np.nan)
    ) * 10

    heatmap_df["stress"] = (
        heatmap_df["stress"]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )

    heatmap_df["periodo"] = heatmap_df["tempo"].dt.strftime("%Y-%m")

    pivot_heatmap = heatmap_df.pivot_table(
        index="zona_mapa",
        columns="periodo",
        values="stress",
        aggfunc="mean",
    ).reindex(REGIOES)

    fig_heatmap = go.Figure(
        data=go.Heatmap(
            z=pivot_heatmap.values,
            x=pivot_heatmap.columns,
            y=pivot_heatmap.index,
            colorscale=STRESS_COLORSCALE,
            hovertemplate=(
                "Região: %{y}<br>"
                "Período: %{x}<br>"
                "Stress: %{z:.2f}"
                "<extra></extra>"
            ),
            colorbar=dict(title="Stress"),
        )
    )

    fig_heatmap.update_layout(
        title=dict(
            text="Heatmap Mensal de Stress",
            x=0.03,
            font=dict(size=16),
        ),
        height=380,
        margin=dict(l=30, r=30, t=90, b=40),
        xaxis=dict(title="Mês"),
        yaxis=dict(title="Região"),
    )

    # ========================================================
    # PARALLEL COORDINATES
    # ========================================================

    pc_df = (
        dff_region.groupby(["instituicao", "zona_mapa"])
        .agg(
            urgencias=("total_urgencias", "sum"),
            consultas=("no_de_consultas_medicas_total", "sum"),
            cirurgias=("total_cirurgias", "sum"),
            staff=("total_staff", "sum"),
            stress=("stress_index", "mean"),
        )
        .reset_index()
    )

    pc_df = pc_df.replace([np.inf, -np.inf], np.nan).fillna(0)

    regioes_unicas = pc_df["zona_mapa"].dropna().unique().tolist()

    if regioes_unicas:
        pc_df["regiao_id"] = pc_df["zona_mapa"].apply(
            lambda x: regioes_unicas.index(x) if x in regioes_unicas else 0
        )
        cmax = max(0, len(regioes_unicas) - 1)
    else:
        pc_df["regiao_id"] = 0
        cmax = 1

    fig_parcoords = go.Figure(
        data=go.Parcoords(
            line=dict(
                color=pc_df["regiao_id"],
                colorscale=[
                    [0.0, "#0072B2"],
                    [0.25, "#E69F00"],
                    [0.5, "#009E73"],
                    [0.75, "#D55E00"],
                    [1.0, "#CC79A7"],
                ],
                showscale=True,
                cmin=0,
                cmax=cmax,
                colorbar=dict(
                    title="Região",
                    tickmode="array",
                    tickvals=list(range(len(regioes_unicas))),
                    ticktext=regioes_unicas,
                ),
            ),
            dimensions=[
                dict(label="Urgências", values=pc_df["urgencias"]),
                dict(label="Consultas", values=pc_df["consultas"]),
                dict(label="Cirurgias", values=pc_df["cirurgias"]),
                dict(label="Staff", values=pc_df["staff"]),
                dict(label="Stress", values=pc_df["stress"]),
            ],
        )
    )

    fig_parcoords.update_layout(
        title=dict(
            text="Padrões Assistenciais por Instituição",
            x=0.5,
            xanchor="center",
            y=0.96,
            yanchor="top",
            font=dict(size=16),
        ),
        height=420,
        margin=dict(l=60, r=40, t=90, b=40),
    )

    # ========================================================
    # TABLE
    # ========================================================

    table = (
        dff_region.groupby(["instituicao", "zona_mapa"])
        .agg(
            stress=("stress_index", "mean"),
            urgencias=("total_urgencias", "sum"),
            consultas=("no_de_consultas_medicas_total", "sum"),
            cirurgias=("total_cirurgias", "sum"),
            medicos=("medicos_internos", "sum"),
            enfermeiros=("enfermeiros", "sum"),
            staff=("total_staff", "sum"),
        )
        .reset_index()
        .sort_values("stress", ascending=False)
    )

    table = table.rename(columns={"zona_mapa": "regiao"})

    table["stress"] = (
        table["stress"]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
        .round(2)
    )

    columns = [
        {
            "name": col,
            "id": col,
        }
        for col in table.columns
    ]

    return (
        subtitle,
        kpis,
        fig_map,
        fig_ts,
        fig_bubble,
        fig_heatmap,
        fig_parcoords,
        table.to_dict("records"),
        columns,
    )