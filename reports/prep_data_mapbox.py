import geojson
from shapely.geometry import Polygon, Point
import numpy as np
import pandas as pd
import h3.api.numpy_int as h3

from geojson_rewind import rewind


# DATA COLUMNS needed:
# hex code (integer)
# dep_sanitation_sev, ....
# confidence_sanitation, ...
# population
# deprived, confidence_deprived
# sumpoor, confidence_sumpoor

# TO DO
# Crop results at second decimal number
# The confidence is a PI, so make it as you would like to see it in the map


def prep_data_mapbox(data):
    """
    data: data with hex_code columns and dimensions to plot
    """

    # remove hex_code where pop is less than 50
    # TODO: check that population is not scaled
    # data = data[data["population"] > 50].copy()

    # Add geometry of the polygon
    data["geometry_latlon"] = [
        Polygon(h3.h3_to_geo_boundary(x, geo_json=False)) for x in data["hex_code"]
    ]
    # Compute Coordinates of Centroid (long, lat)
    data["centroid"] = data["hex_code"].apply(
        lambda x: Point(h3.h3_to_geo(x)[1], h3.h3_to_geo(x)[0])
    )

    # Create a list of features
    features = [
        geojson.Feature(
            geometry=data.loc[i]["geometry_latlon"],
            properties={
                # sanitation
                "sanitation": data.loc[i]["dep_sanitation_sev"],
                "confidence_sanitation": data.loc[i]["confidence_sanitation"],
                # health
                # "health": data.loc[i]["dep_health_sev"],
                # "confidence_health": data.loc[i]["confidence_health"],
                # housing
                "housing": data.loc[i]["dep_housing_sev"],
                "confidence_housing": data.loc[i]["confidence_housing"],
                # education
                "education": data.loc[i]["dep_education_sev"],
                "confidence_education": data.loc[i]["confidence_education"],
                # nutrition
                # "nutrition": data.loc[i]["dep_nutrition_sev"],
                # "confidence_nutrition": data.loc[i]["confidence_nutrition"],
                # water
                "water": data.loc[i]["dep_water_sev"],
                "confidence_water": data.loc[i]["confidence_water"],
                # population
                # "hex_code": int(data.loc[i]["hex_code"]),
                "population": int(data.loc[i]["population"]),
                # prevalence and severity
                "deprived": data.loc[i]["deprived_sev"],
                "confidence_deprived": data.loc[i]["confidence_deprived"],
                "sumpoor": data.loc[i]["sumpoor_sev"],
                "confidence_sumpoor": data.loc[i]["confidence_sumpoor"],
                # "centroid": data.loc[i]["centroid"],
            },
        )
        for i in range(data.shape[0])
    ]

    # Create feature collection
    feature_collection = geojson.FeatureCollection(features)

    # Enforce polygon ring winding order in the geojson
    feature_collection_rewind = rewind(feature_collection)

    return feature_collection_rewind


def aggregate_results(data, res):
    '''
    aggregate result in the new resolution taking the means of the hexagons
    whose centroid belong to the hexagon in that resolution
    and summing the population
    '''

    # Compute Coordinates of Centroid (long, lat)
    data["centroid"] = data["hex_code"].apply(
        lambda x: Point(h3.h3_to_geo(x)[1], h3.h3_to_geo(x)[0])
    )
    # Assign hexcode in new resolution to each centroid
    data['new_hexcode'] = data['centroid'].apply(lambda x: h3.geo_to_h3(x.coords[0][1], x.coords[0][0], res))

    data = data.groupby('new_hexcode').mean().reset_index()
    data.drop(columns = ['hex_code'], inplace=True)

    # take the sum of the population
    data['population'] = list(data.groupby('new_hexcode')['population'].sum())

    return data.rename(columns={'new_hexcode':'hex_code'})
  

