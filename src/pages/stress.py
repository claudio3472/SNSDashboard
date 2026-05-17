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

STRESS_COLORSCALE = [
    [0.0, "#F7F7F7"],
    [0.2, COLORBLIND[5]],
    [0.4, COLORBLIND[0]],
    [0.6, COLORBLIND[2]],
    [0.8, COLORBLIND[1]],
    [1.0, COLORBLIND[4]],
]

for col in [
    "total_urgencias",
    "medicos_internos",
    "enfermeiros",
    "no_de_consultas_medicas_total",
    "no_intervencoes_cirurgicas_programadas",
    "no_intervencoes_cirurgicas_convencionais",
    "no_intervencoes_cirurgicas_urgentes",
]:
    if col not in df.columns:
        df[col] = 0
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

CUMULATIVE_COLS = [
    "total_urgencias",
    "no_de_consultas_medicas_total",
    "no_intervencoes_cirurgicas_programadas",
    "no_intervencoes_cirurgicas_convencionais",
    "no_intervencoes_cirurgicas_urgentes",
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
    df["no_intervencoes_cirurgicas_programadas"]
    + df["no_intervencoes_cirurgicas_convencionais"]
    + df["no_intervencoes_cirurgicas_urgentes"]
)


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
gdf["geometry"] = gdf["geometry"].simplify(0.002, preserve_topology=True)

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

def empty_fig(title):
    fig = go.Figure()

    fig.update_layout(
        title=dict(text=title, x=0.03),
        height=380,
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


def base_layout(fig, title, height=380):
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
                                id="stress-start-date",
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
                                id="stress-end-date",
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

        html.Div(id="stress-kpis", className="kpi-row"),

        html.Div(
            className="card",
            style={"marginBottom": "20px"},
            children=[
                dcc.Graph(
                    id="stress-map",
                    config={"displayModeBar": False},
                )
            ],
        ),

        html.Div(
            className="grid-2x2",
            children=[
                html.Div(
                    className="card",
                    children=[
                        dcc.Graph(
                            id="stress-ts",
                            config={"displayModeBar": False},
                        )
                    ],
                ),

                html.Div(
                    className="card",
                    children=[
                        dcc.Graph(
                            id="stress-bubble",
                            config={"displayModeBar": False},
                        )
                    ],
                ),

                html.Div(
                    className="card",
                    children=[
                        dcc.Graph(
                            id="stress-heatmap",
                            config={"displayModeBar": False},
                        )
                    ],
                ),

                html.Div(
                    className="card",
                    children=[
                        dcc.Graph(
                            id="stress-parcoords",
                            config={"displayModeBar": False},
                        )
                    ],
                ),
            ],
        ),
    ],
)


# ============================================================
# CALLBACK — SELECTION
# ============================================================

@callback(
    Output("stress-region", "data"),
    Output("stress-inst", "data"),
    Input("stress-map", "clickData"),
    Input("stress-reset-region", "n_clicks"),
    Input("stress-reset-inst", "n_clicks"),
    prevent_initial_call=True,
)
def update_selection(map_click, reset_region, reset_inst):
    trigger = ctx.triggered_id

    if trigger == "stress-reset-region":
        return None, None

    if trigger == "stress-reset-inst":
        return no_update, None

    if trigger == "stress-map" and map_click:
        point = map_click["points"][0]
        custom = point.get("customdata")

        if isinstance(custom, list):
            if len(custom) >= 2 and custom[0] == "region":
                return custom[1], None

            if len(custom) >= 1 and custom[0] in REGIOES:
                return custom[0], None

            if len(custom) >= 1:
                return no_update, custom[0]

    return no_update, no_update


# ============================================================
# CALLBACK — DASHBOARD
# ============================================================

@callback(
    Output("stress-subtitle", "children"),
    Output("stress-kpis", "children"),
    Output("stress-map", "figure"),
    Output("stress-ts", "figure"),
    Output("stress-bubble", "figure"),
    Output("stress-heatmap", "figure"),
    Output("stress-parcoords", "figure"),
    Input("stress-start-date", "date"),
    Input("stress-end-date", "date"),
    Input("stress-region", "data"),
    Input("stress-inst", "data"),
)
def update_dashboard(start_date, end_date, selected_region, selected_inst):
    dff = filter_period(start_date, end_date)

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

    if dff_inst.empty:
        return (
            subtitle,
            [
                kpi_card("Stress Médio", "0.00"),
                kpi_card("Urgências", "0"),
                kpi_card("Instituições", "0"),
            ],
            empty_fig("Mapa de Stress"),
            empty_fig("Evolução do Índice de Stress"),
            empty_fig("Profissionais vs Urgências"),
            empty_fig("Heatmap Mensal de Stress"),
            empty_fig("Padrões Assistenciais"),
        )

    # ========================================================
    # KPIS
    # ========================================================

    total_urgencias = int(dff_inst["total_urgencias"].sum())
    total_staff = int(dff_inst["total_staff"].sum())
    stress_medio = total_urgencias / total_staff * 10 if total_staff > 0 else 0

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
           f"{stress_medio:.2f}".replace(".", ","),
            spark(spark_df["tempo"], spark_df["stress"], COLORBLIND[4]),
        ),

        kpi_card(
            "Urgências",
            f"{total_urgencias:,}".replace(",", " "),
            spark(spark_df["tempo"], spark_df["urgencias"], COLORBLIND[0]),
        ),


        kpi_card(
            "Instituições",
            f"{dff_inst['instituicao'].nunique()}",
            html.Div(
                f"{dff_inst['tempo'].nunique()} períodos analisados",
                className="kpi-subtitle",
                style={"marginTop": "10px"},
            ),
        ),
    ]

    # ========================================================
    # MAP
    # ========================================================

    stress_region = (
        dff.groupby("zona_mapa")
        .agg(
            urgencias=("total_urgencias", "sum"),
            staff=("total_staff", "sum"),
            instituicoes=("instituicao", "nunique"),
        )
        .reindex(REGIOES)
        .reset_index()
    )

    stress_region["stress"] = (
        stress_region["urgencias"]
        / stress_region["staff"].replace(0, np.nan)
        * 10
    ).replace([np.inf, -np.inf], np.nan).fillna(0)

    q95 = stress_region["stress"].quantile(0.95)

    if q95 > 0:
        stress_region["stress"] = stress_region["stress"].clip(upper=q95)

    map_df = (
        gdf[["map_id", "zona_mapa"]]
        .drop_duplicates()
        .merge(
            stress_region[["zona_mapa", "stress", "instituicoes"]],
            on="zona_mapa",
            how="left",
        )
    )

    map_df[["stress", "instituicoes"]] = map_df[["stress", "instituicoes"]].fillna(0)

    if selected_region:
        map_df.loc[map_df["zona_mapa"] != selected_region, "stress"] = 0

    fig_map = go.Figure()

    fig_map.add_trace(
        go.Choropleth(
            geojson=geojson_map,
            locations=map_df["map_id"],
            z=map_df["stress"],
            featureidkey="properties.map_id",
            colorscale=STRESS_COLORSCALE,
            showscale=True,
            marker_line_color="white",
            marker_line_width=0.35,
            customdata=map_df[["zona_mapa", "stress", "instituicoes"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Stress: %{customdata[1]:.2f}<br>"
                "Instituições: %{customdata[2]:.0f}"
                "<extra></extra>"
            ),
            colorbar=dict(title="Stress", thickness=12),
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
                        size=38,
                        color="rgba(255,255,255,0.65)",
                        opacity=0.95,
                        line=dict(color="#111827", width=1.4),
                    ),
                    textposition="middle center",
                    textfont=dict(color="#111827", size=11),
                    hovertemplate="<b>%{customdata[1]}</b><extra></extra>",
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

        points["stress"] = points["stress"].replace([np.inf, -np.inf], np.nan).fillna(0)

        if not points.empty:
            fig_map.add_trace(
                go.Scattergeo(
                    lon=points["lon"],
                    lat=points["lat"],
                    mode="markers",
                    text=points["instituicao"],
                    customdata=points[["instituicao", "zona_mapa", "stress", "urgencias", "staff"]],
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
            text=f"Mapa de Stress — {selected_region}" if selected_region else "Mapa de Stress por Região",
            x=0.03,
        ),
        height=560,
        margin=dict(l=0, r=0, t=60, b=0),
        showlegend=False,
        dragmode=False,
        separators=", ",
    )

    # ========================================================
    # TIME SERIES
    # ========================================================

    ts = (
        dff_inst.groupby("tempo")
        .agg(
            stress=("stress_index", "mean"),
            urgencias=("total_urgencias", "sum"),
            staff=("total_staff", "sum"),
        )
        .reset_index()
        .sort_values("tempo")
    )

    ts["rolling_3m"] = ts["stress"].rolling(3).mean()
    benchmark = ts["stress"].mean()

    fig_ts = go.Figure()

    fig_ts.add_trace(
        go.Scatter(
            x=ts["tempo"],
            y=ts["stress"],
            name="Stress",
            mode="lines+markers",
            line=dict(color=COLORBLIND[0], width=2.5),
            hovertemplate="Data: %{x|%Y-%m}<br>Stress: %{y:.2f}<extra></extra>",
        )
    )

    fig_ts.add_trace(
        go.Scatter(
            x=ts["tempo"],
            y=ts["rolling_3m"],
            name="Tendência 3m",
            mode="lines",
            line=dict(color=COLORBLIND[4], width=3, dash="dot"),
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

    fig_ts = base_layout(fig_ts, "Evolução do Índice de Stress")
    fig_ts.update_layout(
        yaxis=dict(title="Stress"),
        legend=dict(orientation="h", y=1.12),
    )

    # ========================================================
    # BUBBLE
    # ========================================================

    bubble = (
        dff_region.groupby(["instituicao", "zona_mapa"])
        .agg(
            total_staff=("total_staff", "sum"),
            total_urgencias=("total_urgencias", "sum"),
            stress=("stress_index", "mean"),
        )
        .reset_index()
    )

    bubble["stress"] = bubble["stress"].replace([np.inf, -np.inf], np.nan).fillna(0)

    max_stress = bubble["stress"].max()

    if max_stress > 0:
        bubble["size"] = (bubble["stress"] / max_stress * 42) + 8
    else:
        bubble["size"] = 12

    fig_bubble = go.Figure()

    for i, regiao in enumerate(REGIOES):
        dfr = bubble[bubble["zona_mapa"] == regiao]

        if dfr.empty:
            continue

        fig_bubble.add_trace(
            go.Scatter(
                x=dfr["total_staff"],
                y=dfr["total_urgencias"],
                mode="markers",
                name=regiao,
                marker=dict(
                    size=dfr["size"],
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

    if not bubble.empty:
        fig_bubble.add_vline(
            x=bubble["total_staff"].mean(),
            line_dash="dash",
            line_color="#6B7280",
        )
        fig_bubble.add_hline(
            y=bubble["total_urgencias"].mean(),
            line_dash="dash",
            line_color="#6B7280",
        )

    fig_bubble = base_layout(
        fig_bubble,
        f"Instituições: Profissionais vs Urgências — {selected_region}"
        if selected_region
        else "Instituições: Profissionais vs Urgências",
    )

    fig_bubble.update_layout(
        xaxis=dict(title="Profissionais"),
        yaxis=dict(title="Urgências"),
        legend=dict(orientation="h", y=1.12),
    )

    # ========================================================
    # HEATMAP
    # ========================================================

    heat = (
        dff_region.groupby(["zona_mapa", "tempo"])
        .agg(
            urgencias=("total_urgencias", "sum"),
            staff=("total_staff", "sum"),
        )
        .reset_index()
    )

    heat["stress"] = (
        heat["urgencias"]
        / heat["staff"].replace(0, np.nan)
        * 10
    ).replace([np.inf, -np.inf], np.nan).fillna(0)

    heat["periodo"] = heat["tempo"].dt.strftime("%Y-%m")

    pivot = heat.pivot_table(
        index="zona_mapa",
        columns="periodo",
        values="stress",
        aggfunc="mean",
    ).reindex(REGIOES)

    fig_heat = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
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

    fig_heat = base_layout(fig_heat, "Heatmap Mensal de Stress")
    fig_heat.update_layout(
        xaxis=dict(title="Mês"),
        yaxis=dict(title="Região"),
    )

    # ========================================================
    # PARALLEL COORDINATES
    # ========================================================

    pc = (
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

    pc = pc.replace([np.inf, -np.inf], np.nan).fillna(0)

    regioes_unicas = pc["zona_mapa"].dropna().unique().tolist()

    if regioes_unicas:
        pc["regiao_id"] = pc["zona_mapa"].apply(
            lambda x: regioes_unicas.index(x) if x in regioes_unicas else 0
        )
        cmax = max(0, len(regioes_unicas) - 1)
    else:
        pc["regiao_id"] = 0
        cmax = 1

    fig_pc = go.Figure(
        data=go.Parcoords(
            line=dict(
                color=pc["regiao_id"],
                colorscale=[
                    [0.0, COLORBLIND[0]],
                    [0.25, COLORBLIND[1]],
                    [0.5, COLORBLIND[2]],
                    [0.75, COLORBLIND[3]],
                    [1.0, COLORBLIND[4]],
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
                dict(label="Urgências", values=pc["urgencias"]),
                dict(label="Consultas", values=pc["consultas"]),
                dict(label="Cirurgias", values=pc["cirurgias"]),
                dict(label="Staff", values=pc["staff"]),
                dict(label="Stress", values=pc["stress"]),
            ],
        )
    )

    fig_pc.update_layout(
        title=dict(text="Padrões Assistenciais por Instituição", x=0.5),
        height=420,
        margin=dict(l=60, r=40, t=90, b=40),
    )

    return (
        subtitle,
        kpis,
        fig_map,
        fig_ts,
        fig_bubble,
        fig_heat,
        fig_pc,
    )