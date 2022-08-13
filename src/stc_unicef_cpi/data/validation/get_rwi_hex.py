import pandas as pd
import numpy as np
from pyquadkey2.quadkey import QuadKey
from shapely.geometry import Polygon, Point
from shapely.geometry import mapping
import h3.api.numpy_int as h3
from stc_unicef_cpi.utils import geospatial as geo
from tqdm import tqdm

tqdm.pandas()


# https://docs.muetsch.io/pyquadkey2/methods/


def quadkey_to_polygon(quadkey):
    """Return polygon of quadkey
    :param quadkey: quadkey code
    :type quadkey: str
    """
    # Extract coordinates of quadkey
    quadkey = QuadKey(quadkey)
    # This returns a tuple (lat, long)
    n, w = quadkey.to_geo(0)
    # ne = quadkey.to_geo(1)
    # sw = quadkey.to_geo(2)
    s, e = quadkey.to_geo(3)
    # center = quadkey.to_geo(4)

    # build polygon
    poly_quadkey = Polygon([Point([w, n]), Point([e, n]), Point([e, s]), Point([w, s])])
    # poly_quadkey = Polygon([Point(nw), Point(ne), Point(se), Point(sw)])
    return poly_quadkey


# geo.get_new_nbrs_at_k(hexes, k) fa la stessa cosa
def get_hexcode_polygon_full(poly_qk, res=7, k=1):
    """Get hexcodes whose centroid belong to the polygon
    and the neighbors
    :param poly_qk: polygon
    :type poly_qk: Polygon
    :param res: h3 resolution, defaults to 7
    :type res: int, optional
    :param k: number of k-ring neighbors to cover quadkey [SHOULD BE AUTOMATED]
    :type k: int, optional
    """
    hexcodes = h3.polyfill(mapping(poly_qk), res)

    # p1 = Polygon(h3.h3_to_geo_boundary(609543640011767807, False))
    list_hex = []
    for hex in hexcodes:
        for elem in list(h3.k_ring(hex, k)):
            list_hex.append(elem)

    set_hex = set(list_hex)
    return set_hex


def get_hexcode_in_qk(qk, res=7, k=1):
    """
    Return hexcodes in qk
    :param qk: quadkey code
    :type qk: str
    :param res: h3 resolution, defaults to 7
    :type res: int, optional
    :param k: number of k-ring neighbors to cover quadkey [SHOULD BE AUTOMATED]
    :type k: int, optional
    """
    poly_quadkey = quadkey_to_polygon(str(qk))
    set_hex = get_hexcode_polygon_full(poly_quadkey, res, k)
    return list(set_hex)


def get_rwi_country(path, code):
    """
    Get the RWI csv of a particular country
    :param path: directory containing csv of relative-wealth-index-april-2021
    :type path: str
    :param code: code of the country [SHOULD BE AUTOMATED]
    :type code: str
    """
    # import quadkey as a string
    rwi_country = pd.read_csv(
        path + "/" + code + "_relative_wealth_index.csv", dtype={"quadkey": "string"}
    )
    rwi_country.head()
    return rwi_country


def invert_qk_hex(df):
    """
    From a dic (dataframe) where each key is a qk and the value is the possible hex that intersect the qk
    to a dic where each key is a hex and the value is the possible qk that intersect the hex
    df is a dataframe with col quadkey and hexcodes
    :param df: dataframe with one column quadkey and another list of with hexcode whose centroid belong to square and their neighbors
    :type df: pd DataFrame
    """
    dic = {}
    for i in tqdm(list(df.index)):
        for hex in df.loc[i]["hexcodes"]:
            if hex in dic.keys():
                dic[hex].append(df.loc[i]["quadkey"])
            else:
                dic[hex] = [df.loc[i]["quadkey"]]
    return dic


def get_perc_areas(hex, dic, data):
    """
    Compute area shared between hexagons and quadkey polygons
    :param hex: hex code
    :type hex: int
    :param dic: dictionary with key hex code and all possible quadkeys that intersect hexagon
    :type dic: dict
    :param data: dataframe with one column quadkey and another with geometry of respective quadkey
    :type data: pd DataFrame
    """
    weights = {}
    if hex in dic.keys():
        poly_hex = Polygon(h3.h3_to_geo_boundary(hex, False))
        area_hex = abs(geo.get_area_polygon(poly_hex, crs="WGS84"))
        # print(len(dic[hex]))

        for qk in set(dic[hex]):
            # print(qk)
            inters = poly_hex.intersection(
                data[data["quadkey"] == qk]["geometry"].iloc[0]
            )

            try:
                area_inters = abs(geo.get_area_polygon(inters, crs="WGS84"))
                perc = area_inters / area_hex
                weights[qk] = perc
            except:
                pass
                # print(f'No intersection')
        return weights
    else:
        return {}


def weighted_rwi(qk_weights, dic_rwi):
    """ 
    Compute weighted RWI for a hexagon
    :param qk_weights: dictionary with keys quadkeys and values the proportion of area shared with hexagon
    :type qk_weights: dict
    :param dic_rwi: dictionary with key quadkey and value the RWI of that quadkey
    :type dic_rwi: dict
    """
    if len(qk_weights.keys()):
        return sum([qk_weights[qk] * dic_rwi[qk] for qk in qk_weights.keys()])
    else:
        return np.nan


def get_rwi_hex(path, country_name, code, res=7, k=1):
    """
    Aggregate RWI predictions at hexagonal level
    :param path: directory containing csv of relative-wealth-index-april-2021
    :type path: str
    :param country_name: name of a country
    :type country_name: str
    :param code: code of the country [SHOULD BE AUTOMATED]
    :type code: str
    :param res: h3 resolution, defaults to 7
    :type res: int, optional
    :param k: number of k-ring neighbors to cover quadkey [SHOULD BE AUTOMATED]
    :type k: int, optional
    """

    rwi_country = get_rwi_country(path, code)

    rwi_country["hexcodes"] = rwi_country["quadkey"].apply(
        lambda x: get_hexcode_in_qk(x, res, k)
    )
    # get geometry of quadkeys
    rwi_country["geometry"] = rwi_country["quadkey"].apply(
        lambda x: quadkey_to_polygon(str(x))
    )

    dic = invert_qk_hex(rwi_country)

    hex_country = geo.get_hexes_for_ctry(country_name, res)
    df = pd.DataFrame(hex_country, columns=["hex_code"])
    print("Compute Weights")
    df["qk_weights"] = df.progress_apply(
        lambda x: get_perc_areas(x["hex_code"], dic, rwi_country), axis=1
    )

    dic_rwi = dict(zip(rwi_country["quadkey"], rwi_country["rwi"]))
    df["rwi"] = df["qk_weights"].progress_apply(lambda x: weighted_rwi(x, dic_rwi))

    return df[["hex_code", "rwi"]]


# TO DO: select code from country and viceversa

# print("Nigeria")
# code = "NGA"
# country_name = "Nigeria"
# path = (
#     "C:/Users/vicin/Desktop/DSSG/Validation Data/RWI/relative-wealth-index-april-2021"
# )
# res = 7
# df = get_rwi_hex(path, country_name, code, res)
# print(df.shape)
# print(sum(df.rwi.isna()))
