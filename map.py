from dash import Dash, dash_table, Input, Output, callback, dcc, html
import dash_daq as daq

import pandas as pd
import geopandas as gpd
from shapely.geometry.point import Point
import base64
from io import BytesIO
import sys
import os


import matplotlib  # pip install matplotlib

matplotlib.use("agg")
import matplotlib.pyplot as plt
import matplotlib_scalebar
from matplotlib_scalebar.scalebar import ScaleBar


if getattr(sys, "frozen", False):
    map_path = os.path.join(sys._MEIPASS, "mapa_mexico3")
else:
    map_path = "mapa_mexico3"

mexico = gpd.read_file(map_path)
# lat = 19.332829
# lon = -99.185905


def build_image(gp_map, lat, lon):
    ax = gp_map.plot(
        column="asistentes",
        missing_kwds={
            "color": "white",
            "edgecolor": "lightgray",
        },
        legend=True,
        cmap="OrRd",
    )
    ax.add_artist(ScaleBar(1))
    ax.set_axis_off()
    center = to_meter_system(lat, lon)
    ax.scatter([center.x], [center.y], color="red")
    ax = (
        gp_map.loc[gp_map["CVE_EDO"] == "09"]
        .dissolve("CVE_EDO")
        .plot(ax=ax, facecolor="none", edgecolor="darkgray", linewidth=2)
    )
    # plt.axis([-2.86e6, -2.72e6, 2.37e6, 2.5e6])

    ## formating image
    fig = ax.figure
    buf = BytesIO()
    fig.savefig(buf, format="png")
    fig_data = base64.b64encode(buf.getbuffer()).decode("ascii")
    fig_base64 = f"data:image/png;base64,{fig_data}"

    return fig_base64


def to_meter_system(lat, lon):
    geometry = [Point((lon, lat))]
    geo_df = gpd.GeoDataFrame(geometry=geometry).set_crs("EPSG:4326")
    geo_df = geo_df.to_crs(epsg=32619)
    p = geo_df["geometry"].iloc[0]
    return p


def format_table(EDO=True, CDMX=True):
    if EDO and CDMX:
        query = 'CVE_EDO=="15" or CVE_EDO=="09"'
    elif CDMX:
        query = 'CVE_EDO=="09"'
    else:
        query = 'CVE_EDO=="15"'
    mapa = mexico.query(query).set_index("CLAVE").sort_index()
    mapa = mapa.to_crs(32619)
    mapa["clave"] = mapa.index
    mapa["asistentes"] = float("nan")
    return mapa


cdmx = format_table()
cdmx_records = list(
    map(
        lambda x: {
            "NOM_MUN": x["NOM_MUN"],
            "asistentes": x["asistentes"],
            "clave": x["clave"],
        },
        cdmx.to_dict("records"),
    )
)


app = Dash(__name__)
server = app.server

app.layout = html.Div(
    [
        html.Img(id="map-fig"),
        dcc.Input(
            id="input_lat",
            type="number",
            placeholder="Latitud",
            debounce=1,
            value=19.332829,
        ),
        dcc.Input(
            id="input_lon",
            type="number",
            placeholder="Longitud",
            debounce=1,
            value=-99.185905,
        ),
        daq.ToggleSwitch(
            id="EDO_switch",
            value=True,
            label="EDO",
        ),
        daq.ToggleSwitch(
            id="CDMX_switch",
            value=True,
            label="CDMX",
        ),
        dash_table.DataTable(
            id="asistentes-editable",
            columns=[
                {"name": "Municipio", "id": "NOM_MUN"},
                {"name": "asistentes", "id": "asistentes"},
            ],
            data=cdmx_records,
            editable=True,
        ),
    ]
)


@callback(
    Output(component_id="map-fig", component_property="src"),
    Input("asistentes-editable", "data"),
    Input(component_id="input_lat", component_property="value"),
    Input(component_id="input_lon", component_property="value"),
)
def display_output(rows, lat, lon):
    for r in rows:
        if r["asistentes"] != None:
            cdmx.at[r["clave"], "asistentes"] = float(r["asistentes"])
    return build_image(cdmx, lat, lon)


@callback(
    Output(component_id="asistentes-editable", component_property="data"),
    Input(component_id="EDO_switch", component_property="value"),
    Input(component_id="CDMX_switch", component_property="value"),
)
def include_EDO(EDO, CDMX):
    global cdmx
    cdmx = format_table(EDO, CDMX)
    cdmx_records = list(
        map(
            lambda x: {
                "NOM_MUN": x["NOM_MUN"],
                "asistentes": x["asistentes"],
                "clave": x["clave"],
            },
            cdmx.to_dict("records"),
        )
    )
    return cdmx_records


if __name__ == "__main__":
    app.run_server()
    # app.run(debug=True)
