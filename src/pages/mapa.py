
from dash import html, dcc, callback, Input, Output, State, dash_table, no_update, ctx
import pandas as pd
import geopandas as gpd
import plotly.graph_objects as go
import plotly.express as px
import re
from shapely.geometry import Point, Polygon

# ============================================================
# DATA LOAD
# ============================================================

df = pd.read_csv("data/processed/master_dataset.csv")
df["ano"] = df["ano"].astype(int)

MAP_PATH = "src/map/geoBoundaries-PRT-ADM3.shp"
gdf = gpd.read_file(MAP_PATH).to_crs(epsg=4326)

# ============================================================
# GEOLOCATION
# ============================================================

def parse_localizacao(value):
    if pd.isna(value):
        return pd.Series([None, None])

    nums = re.findall(r"-?\d+\.\d+|-?\d+", str(value))

    if len(nums) < 2:
        return pd.Series([None, None])

    lat = float(nums[0])
    lon = float(nums[1])

    return pd.Series([lat, lon])


if "localizacao_geografica" in df.columns:
    df[["lat", "lon"]] = df["localizacao_geografica"].apply(parse_localizacao)

df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

# ============================================================
# MAP LIMITS / ZONES
# Each institution belongs to ONE zone only.
# ============================================================

ZONE_POLYGONS = {
    "Lisboa e Vale do Tejo": Polygon([
        (-9.65, 38.25),
        (-7.45, 38.25),
        (-7.45, 39.75),
        (-9.65, 39.75),
    ]),

    "Algarve": Polygon([
        (-9.10, 36.80),
        (-7.20, 36.80),
        (-7.20, 37.45),
        (-9.10, 37.45),
    ]),

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

    "Alentejo": Polygon([
        (-9.25, 37.20),
        (-6.60, 37.20),
        (-6.60, 39.20),
        (-9.25, 39.20),
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
        row["regiao"] if "regiao" in df.columns else None,
    ),
    axis=1,
)

# ============================================================
# MAP PREP
# ============================================================

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

ANOS = sorted(df["ano"].astype(int).unique().tolist())

REGIAO_COORDS = {
    "Norte": {
        "lat": 41.35,
        "lon": -8.20,
        "color": "#5b7cfa",
    },
    "Centro": {
        "lat": 40.20,
        "lon": -8.15,
        "color": "#46b8b0",
    },
    "Lisboa e Vale do Tejo": {
        "lat": 38.80,
        "lon": -9.05,
        "color": "#f2b84b",
    },
    "Alentejo": {
        "lat": 38.10,
        "lon": -7.85,
        "color": "#a978d6",
    },
    "Algarve": {
        "lat": 37.10,
        "lon": -8.10,
        "color": "#e84f5f",
    },
}

# ============================================================
# HELPERS
# ============================================================

def filter_year(data, ano):
    if ano == "all":
        return data.copy()

    return data[data["ano"] == int(ano)].copy()


def make_kpi(title, value):
    return html.Div(
        className="kpi-card",
        children=[
            html.Div(title, className="kpi-title"),
            html.Div(value, className="kpi-value"),
        ],
    )


def empty_figure(title):
    fig = go.Figure()

    fig.update_layout(
        title=title,
        height=360,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text="Selecione uma região no mapa ou uma instituição na tabela",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=14),
            )
        ],
    )

    return fig


def make_map(selected_region=None, selected_inst=None, dff=None):
    fig = go.Figure()

    fig.add_trace(
        go.Choropleth(
            geojson=geojson_map,
            locations=gdf["map_id"],
            z=[1] * len(gdf),
            featureidkey="properties.map_id",
            colorscale=[
                [0, "#e5e7eb"],
                [1, "#e5e7eb"],
            ],
            showscale=False,
            marker_line_color="white",
            marker_line_width=0.35,
            hoverinfo="skip",
            name="Portugal",
        )
    )

    # Show region bubbles ONLY before selecting a region
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
                        size=44,
                        color=info["color"],
                        opacity=0.92,
                        line=dict(
                            color="#111827",
                            width=1,
                        ),
                    ),
                    textposition="middle center",
                    textfont=dict(
                        color="#111827",
                        size=11,
                    ),
                    hovertemplate="<b>%{customdata[1]}</b><extra></extra>",
                    name=regiao,
                )
            )

    # Show institutions ONLY after selecting a region
    if selected_region and dff is not None:
        points = (
            dff[
                (dff["zona_mapa"] == selected_region)
                & dff["lat"].notna()
                & dff["lon"].notna()
            ]
            .groupby(["instituicao", "zona_mapa", "lat", "lon"])
            .agg(
                gastos=("gastos_operacionais", "sum"),
                urgencias=("total_urgencias", "sum"),
            )
            .reset_index()
        )

        points["gastos_m"] = points["gastos"] / 1e6

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
                        "gastos_m",
                    ]
                ],
                marker=dict(
                    size=13,
                    color="#ef4444",
                    opacity=0.9,
                    line=dict(
                        color="#111827",
                        width=1,
                    ),
                ),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Zona: %{customdata[1]}<br>"
                    "Gastos: %{customdata[2]:.1f} M€"
                    "<extra></extra>"
                ),
                name="Instituições",
            )
        )

    # Zoom bounds by selected region
    region_bounds = {
        "Norte": {
            "lon": [-8.95, -6.15],
            "lat": [40.70, 42.30],
        },
        "Centro": {
            "lon": [-9.25, -6.25],
            "lat": [39.15, 40.85],
        },
        "Lisboa e Vale do Tejo": {
            "lon": [-9.65, -7.35],
            "lat": [38.20, 39.75],
        },
        "Alentejo": {
            "lon": [-9.25, -6.55],
            "lat": [37.20, 39.25],
        },
        "Algarve": {
            "lon": [-9.10, -7.15],
            "lat": [36.90, 37.45],
        },
    }

    if selected_region:
        lon_range = region_bounds[selected_region]["lon"]
        lat_range = region_bounds[selected_region]["lat"]
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
        title=(
            f"Mapa — {selected_region}"
            if selected_region
            else "Mapa Regional"
        ),
        height=560,
        margin=dict(
            l=0,
            r=0,
            t=45,
            b=0,
        ),
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
            },
            children=[
                html.Div([
                    html.H2("Mapa Regional"),
                    html.P(id="mapa-subtitle"),
                ]),

                html.Div(
                    style={
                        "display": "flex",
                        "gap": "8px",
                        "alignItems": "center",
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

                        dcc.Dropdown(
                            id="mapa-ano",
                            options=[
                                {
                                    "label": "Todos os anos",
                                    "value": "all",
                                }
                            ]
                            + [
                                {
                                    "label": str(a),
                                    "value": int(a),
                                }
                                for a in ANOS
                            ],
                            value="all",
                            clearable=False,
                            style={"width": "180px"},
                        ),
                    ],
                ),
            ],
        ),

        html.Div(
            id="mapa-kpis",
            className="kpi-row",
        ),

        html.Div(
            className="grid-2x2",
            children=[
                html.Div(
                    className="card",
                    children=[
                        dcc.Graph(
                            id="mapa-portugal",
                            config={
                                "displayModeBar": False,
                            },
                        ),
                    ],
                ),

                html.Div(
                    className="card",
                    children=[
                        dcc.Graph(
                            id="mapa-regiao",
                            config={
                                "displayModeBar": False,
                                "staticPlot": True,
                            },
                        ),
                    ],
                ),

                html.Div(
                    className="card",
                    children=[
                        dcc.Graph(
                            id="mapa-inst-graph",
                            config={
                                "displayModeBar": False,
                                "staticPlot": True,
                            },
                        ),
                    ],
                ),

                html.Div(
                    className="card",
                    children=[
                        dcc.Graph(
                            id="mapa-detail",
                            config={
                                "displayModeBar": False,
                                "staticPlot": True,
                            },
                        ),
                    ],
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
                    style_table={
                        "overflowX": "auto",
                    },
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
# ONE SELECTION CALLBACK — avoids circular dependencies
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
    State("mapa-inst", "data"),

    prevent_initial_call=True,
)
def update_selection(
    map_click,
    active_cell,
    reset_region,
    reset_inst,
    table_data,
    current_region,
    current_inst,
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
            if custom[0] == "region":
                return custom[1], None

            return current_region, custom[0]

    return no_update, no_update


# ============================================================
# UPDATE DASHBOARD
# ============================================================

@callback(
    Output("mapa-subtitle", "children"),
    Output("mapa-kpis", "children"),
    Output("mapa-portugal", "figure"),
    Output("mapa-regiao", "figure"),
    Output("mapa-inst-graph", "figure"),
    Output("mapa-detail", "figure"),
    Output("mapa-table", "data"),
    Output("mapa-table", "columns"),

    Input("mapa-ano", "value"),
    Input("mapa-region", "data"),
    Input("mapa-inst", "data"),
)
def update_dashboard(
    ano,
    selected_region,
    selected_inst,
):
    dff = filter_year(df, ano)

    if selected_region:
        dff_region = dff[
            dff["zona_mapa"] == selected_region
        ].copy()
    else:
        dff_region = dff.copy()

    if selected_inst:
        dff_inst = dff_region[
            dff_region["instituicao"] == selected_inst
        ].copy()
    else:
        dff_inst = dff_region.copy()

    subtitle = f"Nível: {selected_region or 'Portugal'}"

    if selected_inst:
        subtitle += f" → {selected_inst}"

    # ========================================================
    # KPIs
    # ========================================================

    gastos = dff_inst["gastos_operacionais"].sum() / 1e6

    urgencias = int(
        dff_inst["total_urgencias"].sum()
    )

    profissionais = int(
        dff_inst[
            [
                "medicos_internos",
                "enfermeiros",
            ]
        ]
        .sum()
        .sum()
    )

    instituicoes = dff_inst["instituicao"].nunique()

    kpis = [
        make_kpi(
            "Gastos Operacionais",
            f"{gastos:,.1f} M€",
        ),
        make_kpi(
            "Urgências",
            f"{urgencias:,}".replace(",", " "),
        ),
        make_kpi(
            "Profissionais",
            f"{profissionais:,}".replace(",", " "),
        ),
        make_kpi(
            "Instituições",
            f"{instituicoes}",
        ),
    ]

    # ========================================================
    # MAP
    # ========================================================

    fig_map = make_map(
        selected_region=selected_region,
        selected_inst=selected_inst,
        dff=dff,
    )

    # ========================================================
    # REGION GRAPH
    # ========================================================

    regiao_data = (
        dff.groupby("zona_mapa")["gastos_operacionais"]
        .sum()
        .reindex(REGIOES)
        .reset_index()
        .rename(columns={"zona_mapa": "regiao"})
    )

    regiao_data["gastos_m"] = (
        regiao_data["gastos_operacionais"] / 1e6
    )

    fig_regiao = px.bar(
        regiao_data,
        x="regiao",
        y="gastos_m",
        title="Gastos por Região (M€)",
    )

    fig_regiao.update_layout(
        height=360,
        clickmode="none",
        dragmode=False,
    )

    # ========================================================
    # INSTITUTIONS GRAPH
    # ========================================================

    inst = (
        dff_region
        .groupby("instituicao")
        .agg(
            gastos=("gastos_operacionais", "sum"),
            urgencias=("total_urgencias", "sum"),
            consultas=("no_de_consultas_medicas_total", "sum"),
            divida=("divida_total_fornecedores_externos", "sum"),
            regiao=("zona_mapa", "first"),
        )
        .reset_index()
        .sort_values("gastos", ascending=False)
    )

    inst["gastos_m"] = inst["gastos"] / 1e6
    inst["divida_m"] = inst["divida"] / 1e6

    fig_inst = px.bar(
        inst.head(15),
        x="instituicao",
        y="gastos_m",
        title=(
            f"Instituições — {selected_region}"
            if selected_region
            else "Instituições — Portugal"
        ),
    )

    fig_inst.update_layout(
        height=360,
        xaxis_tickangle=-35,
        clickmode="none",
        dragmode=False,
    )

    # ========================================================
    # DETAIL GRAPH
    # ========================================================

    if selected_inst:
        detalhe = (
            dff_inst
            .groupby("ano")[
                [
                    "gastos_operacionais",
                    "rendimentos_operacionais",
                    "divida_total_fornecedores_externos",
                ]
            ]
            .sum()
            / 1e6
        ).reset_index()

        fig_detail = go.Figure()

        fig_detail.add_trace(
            go.Scatter(
                x=detalhe["ano"],
                y=detalhe["gastos_operacionais"],
                mode="lines+markers",
                name="Gastos",
            )
        )

        fig_detail.add_trace(
            go.Scatter(
                x=detalhe["ano"],
                y=detalhe["rendimentos_operacionais"],
                mode="lines+markers",
                name="Rendimentos",
            )
        )

        fig_detail.add_trace(
            go.Scatter(
                x=detalhe["ano"],
                y=detalhe["divida_total_fornecedores_externos"],
                mode="lines+markers",
                name="Dívida",
            )
        )

        fig_detail.update_layout(
            title=f"Detalhe — {selected_inst}",
            height=360,
            clickmode="none",
            dragmode=False,
        )

    else:
        fig_detail = empty_figure(
            "Detalhe da Instituição"
        )

    # ========================================================
    # TABLE
    # ========================================================

    table = inst[
        [
            "instituicao",
            "regiao",
            "gastos_m",
            "urgencias",
            "consultas",
            "divida_m",
        ]
    ].copy()

    table["gastos_m"] = table["gastos_m"].round(1)
    table["divida_m"] = table["divida_m"].round(1)

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
        fig_regiao,
        fig_inst,
        fig_detail,
        table.to_dict("records"),
        columns,
    )