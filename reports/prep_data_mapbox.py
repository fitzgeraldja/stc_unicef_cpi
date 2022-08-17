import geojson
from shapely.geometry import Polygon, Point
import numpy as np
import pandas as pd
import h3.api.numpy_int as h3

from tqdm import tqdm

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


def get_data(path_csv):
    """Open Data

    :param path_csv: Path to csv
    :type path_csv: str
    :return: dataframe contained in the path
    :rtype: pd DataFrame
    """
    data = pd.read_csv(path_csv)
    return data


def save_geojson(geojson_file, name_save):
    """Save the geojson

    :param geojson_file: geojson to save
    :type geojson_file: str
    :param name_save: name to give to the saved geojson
    :type name_save: str
    # TO DO: Add String
    """
    with open(name_save + ".geojson", "w") as f:
        geojson.dump(geojson_file, f)


def prep_data_mapbox(path_csv, name_save, save=False):
    """Prepare geojson to pass to mapbox with columns:
    ...
    and it will rewind it in the correct format.
    
    :param path_csv: path to csv with data data with hex_code columns and dimensions to plot
    :type path_csv: str
    :param name_save: Name to give to the geojson that will be saved
    :type name_save: str
    :param save: select whether to save or not the geojson, defaults to False
    :type save: bool, optional
    :return: geojson
    :rtype: geojson
    """

    data = get_data(path_csv)

    # # Rescale
    # data["population"] = data["population"].apply(lambda x: x * 25 * 20.6)

    # If POPULATION IS MISSING : I REPLACE IT WITH -1,
    # SO THAT I CAN VISUALIZE THEM ON THE MAP
    data["population_abs"].fillna(-1, inplace=True)
    data["child_pop"].fillna(-1, inplace=True)

    # remove hex_code where pop is less than 50
    # TODO: check that population is not scaled
    # data = data[data["population"] > 50].copy()

    # Add geometry of the polygon
    """
    geo_json (bool, optional) 
    If True, return output in GeoJson format: lng/lat pairs (opposite order), 
    and have the last pair be the same as the first. 
    If False (default), return lat/lng pairs, with the last pair distinct from the first.
    """
    data["geometry_latlon"] = [
        Polygon(h3.h3_to_geo_boundary(x, geo_json=True)) for x in data["hex_code"]
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
                # "confidence_sanitation": data.loc[i]["confidence_sanitation"],
                # health
                # "health": data.loc[i]["dep_health_sev"],
                # "confidence_health": data.loc[i]["confidence_health"],
                # housing
                "housing": data.loc[i]["dep_housing_sev"],
                # "confidence_housing": data.loc[i]["confidence_housing"],
                # education
                "education": data.loc[i]["dep_education_sev"],
                # "confidence_education": data.loc[i]["confidence_education"],
                # nutrition
                # "nutrition": data.loc[i]["dep_nutrition_sev"],
                # "confidence_nutrition": data.loc[i]["confidence_nutrition"],
                # water
                "water": data.loc[i]["dep_water_sev"],
                # "confidence_water": data.loc[i]["confidence_water"],
                # population
                # "hex_code": int(data.loc[i]["hex_code"]),
                "population": int(data.loc[i]["population_abs"]),
                "child_pop": int(data.loc[i]["child_pop"]),
                # prevalence and severity
                "deprived": data.loc[i]["deprived_sev"],
                # "confidence_deprived": data.loc[i]["confidence_deprived"],
                "sumpoor": data.loc[i]["sumpoor_sev"],
                # "confidence_sumpoor": data.loc[i]["confidence_sumpoor"],
                # "centroid": data.loc[i]["centroid"],
                "dep_2_or_more_sev": data.loc[i]["dep_2_or_more_sev"],
            },
        )
        for i in tqdm(range(data.shape[0]))
    ]

    # Create feature collection
    feature_collection = geojson.FeatureCollection(features)

    # Enforce polygon ring winding order in the geojson
    feature_collection_rewind = rewind(feature_collection)

    if save:
        save_geojson(feature_collection_rewind, name_save)

    return feature_collection_rewind


def aggregate_results(path_csv, res):
    """Aggregate result in the new resolution taking the means of the hexagons
    whose centroid belong to the hexagon in that resolution
    and summing the population.

    :param path_csv: _description_
    :type path_csv: str
    :param res: H3 resolution to which aggregate the data 
    :type res: int
    :rtype: pd DataFrame

    # TO DO: Check if new resolution is lower than previous one
    """
    data = get_data(path_csv)

    # Compute Coordinates of Centroid (long, lat)
    data["centroid"] = data["hex_code"].apply(
        lambda x: Point(h3.h3_to_geo(x)[1], h3.h3_to_geo(x)[0])
    )
    # Assign hexcode in new resolution to each centroid
    data["new_hexcode"] = data["centroid"].apply(
        lambda x: h3.geo_to_h3(x.coords[0][1], x.coords[0][0], res)
    )

    data = data.groupby("new_hexcode").mean().reset_index()
    data.drop(columns=["hex_code"], inplace=True)

    # take the sum of the population
    # HERE SINCE IM TAKING THE SUM ITS LIKE FILLING NAs WITH 0
    data["population"] = list(data.groupby("new_hexcode")["population"].sum())
    data["child_pop"] = list(data.groupby("new_hexcode")["child_pop"].sum())

    return data.rename(columns={"new_hexcode": "hex_code"})


print("Try6")
path_csv = r"C:\Users\vicin\Desktop\DSSG\Data\Predictions\20220812_preds_nigeria_res7_child_pop.csv"

prep_data_mapbox(path_csv, "20220812_preds_nigeria_res7_child_pop", save=True)

aggregate_results(path_csv, 5, save=True)
