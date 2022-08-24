# from pathlib import Path
from shapely.geometry import Polygon, Point
import pandas as pd
import geopandas as gpd

# import swifter
import numpy as np
import h3.api.numpy_int as h3
from pyquadkey2 import quadkey as qk
from stc_unicef_cpi.utils import geospatial as geo


def qk_to_poly(qkey):
    '''
    Return polygon given quadkey string
    :param qkey: quadkey value
    :type qkey: str
    :return: Polygon of quadkey
    :rtype: Polygon
    '''
    # save string as quadkey
    qkey = qk.QuadKey(str(qkey))
    # get coordinates
    n, w = qkey.to_geo(0)
    s, e = qkey.to_geo(3)

    poly_quadkey = Polygon(
        [Point([w, n]), Point([e, n]), Point([e, s]), Point([w, s])]
    )
    return poly_quadkey

def get_rwi(path_rwi, country_name="Nigeria", country_code="NGA", res=7, save=False):
    """
    Aggregate Relative Wealth Index for hexcodes of country, 
    weighting it for the percentage of area shared.
    :param path_rwi: path to file containing relative wealth index data
    :type path_rwi: str, optional
    :param country_name: _description_, defaults to "Nigeria"
    :type country_name: str, optional
    :param country_code: _description_, defaults to "NGA"
    :type country_code: str, optional
    :param res: h3 resolution, defaults to 7
    :type res: int, optional
    :param save: boolean to save the output, defaults to False
    :type save: bool, optional
    :return: dataframe with hexcodes of a country and rwi value per hexcode
    :rtype: pandas dataframe
    """
    rwi_path = path_rwi + "/" + country_code + "_relative_wealth_index.csv"
    rwi_df = pd.read_csv(rwi_path)

    hexes = geo.get_hexes_for_ctry(country_name, res)
    country_hexes = pd.DataFrame(hexes, columns=["hex_code"])

    country_hexes["hex_poly"] = country_hexes.hex_code.apply(
        lambda hhex: Polygon(h3.h3_to_geo_boundary(hhex, geo_json=True))
    )

    rwi_df["qk_poly"] = rwi_df.quadkey.apply(qk_to_poly)

    rwi_gdf = gpd.GeoDataFrame(rwi_df, geometry="qk_poly")
    hex_gdf = gpd.GeoDataFrame(country_hexes, geometry="hex_poly")

    # Join two dataframe with spatial join
    joined = gpd.sjoin(hex_gdf, rwi_gdf)
    joined["qk_poly"] = joined.quadkey.apply(qk_to_poly)

    joined["pc_area"] = (
        joined["hex_poly"].intersection(gpd.GeoSeries(joined["qk_poly"])).area
        / joined["hex_poly"].area
    )
    joined["weighted_rwi"] = joined["pc_area"] * joined["rwi"]
    new_rwi_df = joined.groupby("hex_code", as_index=False).agg(
        {"rwi": "mean", "error": "mean", "weighted_rwi": "sum"}
    )

    new_rwi_df["hex_code_str"] = new_rwi_df["hex_code"].apply(
        lambda x: h3.h3_to_string(x)
    )

    if save:
        new_rwi_df.to_csv(
            "../data/validation/" + country_code + "_rwi_hex.csv", index=False
        )

    return new_rwi_df


# path_rwi = r"C:\Users\vicin\Desktop\DSSG\Data\Validation Data\RWI\relative-wealth-index-april-2021"

# res = get_rwi(path_rwi, country_name="Nigeria", country_code="NGA", res=7, save=True)
# print(res.shape)
# print(res.head(5))
