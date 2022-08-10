import pandas as pd
import numpy as np
import geopandas as gpd
import h3.api.numpy_int as h3

from stc_unicef_cpi.utils import geospatial as geo


def get_world_admin1(path):
    """
    Extract data from shapefile with admin1 labels of the world
    :param path: directory containing shp 'ne_10m_admin_1_states_provinces'
    :type path: str
    """
    # https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-1-states-provinces/
    world = gpd.read_file(path + "/ne_10m_admin_1_states_provinces.shp")
    world.rename(columns={"name": "admin1", "admin": "country"}, inplace=True)

    return world


def get_hex_region(region_name, country, res=7):
    """
    Get dataframe with all hexcodes belonging to a region of a country
    :param region_name: name of the region 
    :type region_name: str
    :param country: dataframe
    :type country: pandas DataFrame
    :param res: h3 resolution, defaults to 7
    :type res: int, optional
    """
    ## TO DO : check if region belongs to country

    # Select shape of region in country (polygon or multipolygon)
    region_shp = country[country.admin1 == region_name].geometry

    # check that there name of the country and of the region univocaly one area
    assert region_shp.shape[0] == 1

    # return dataframe with hexcode and geometry
    # df = geospatial.hexes_poly(region_shp, res)
    df = geo.hexes_poly(str(region_shp.iloc[0]), res)

    # add information about region and about country
    country_name = country.iloc[0]["country"]
    df["country"] = country_name
    df["admin1"] = region_name

    return df


def get_admin1(path, country_name, res=7):
    """
    Get hexcodes & admin1 label of a country
    :param path: directory containing shp 'ne_10m_admin_1_states_provinces'
    :type path: str
    :param country_name: name of a country
    :type country_name: str
    :param res: h3 resolution, defaults to 7
    :type res: int, optional
    """
    world = get_world_admin1(path)

    country = world[world.country == country_name]

    # Get hexcode and admin1 label of the country
    df = pd.DataFrame()
    for i in country.index:
        df = pd.concat([df, get_hex_region(country.loc[i]["admin1"], country, res)])

    return df


path = "C:/Users/vicin/Desktop/DSSG/Validation Data/ne_10m_admin_1_states_provinces"
get_admin1(path, "Senegal", res=7)

