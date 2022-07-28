import geojson
from shapely.geometry import Polygon
import numpy as np
import pandas as pd
import h3.api.numpy_int as h3

import matplotlib.pyplot as plt
from geojson_rewind import rewind

# TO DO : add correct dimensions in the features


def prep_data_mapbox(data, country_name, resolution):
    """
    data: data with hex_code columns and dimensions to plot
    """
    # include geometry
    data["geometry_latlon"] = [
        Polygon(h3.h3_to_geo_boundary(x, geo_json=False)) for x in data["hex_code"]
    ]

    features = [
        Feature(
            geometry=data.loc[i]["geometry_latlon"],
            properties={
                "dep_sanitation": data.loc[i]["fake_san"],
                "dep_water": data.loc[i]["fake_water"],
                "hex_code": int(data.loc[i]["hex_code"]),
                "population": int(data.loc[i]["fake_pop"]),
            },
        )
        for i in range(data.shape[0])
    ]

    feature_collection = FeatureCollection(features)
    # type(feature_collection)

    feature_collection_rewind = rewind(feature_collection)
    # type(feature_collection_rewind)

    return feature_collection_rewind
