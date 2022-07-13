"""Get delivery estimates using Facebook Marketing API"""

import time
import pandas as pd
import h3.api.numpy_int as h3

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.api import FacebookAdsApi

from src.utils.general import get_facebook_credentials


def fb_api_init(token, id):
    """Init Facebook API

    :param token: Access token
    :type access_token: str
    :param id: Account id
    :type ad_account_id: str
    :return: api and account connection
    :rtype: conn
    """
    api = FacebookAdsApi.init(access_token=token)
    account = AdAccount(id)
    try:
        account.get_ads()
        print("Initialized successfully!")
    except Exception as e:
        if e._api_error_code == 190:
            raise ValueError("Invalid or expired access token!")
        elif e._api_error_code == 100:
            raise ValueError("Invalid ad account id!")
        else:
            raise RuntimeError("Please check you credentials!")

    return api, account


def define_params(lat, lon, radius, opt):
    """Define search parameters

    :param lat: latitude
    :type lat: str
    :param long: longitude
    :type long: str
    :param radius: radius
    :type radius: float
    :param opt: optimization criteria
    :type opt: string
    """
    geo = {
        "latitude": lat,
        "longitude": lon,
        "radius": radius,
        "distance_unit": "kilometer",
    }
    targeting = {
        "geo_locations": {
            "custom_locations": [
                geo,
            ],
        },
    }
    params = {
        "optimization_goal": opt,
        "targeting_spec": targeting,
    }

    return params


def get_long_lat(data, hex_code):
    """Get centroid of hexagon
    :param data: dataset
    :type data: dataframe
    :param hex_code: name of column containing the hexagon code
    :type hex_code: string
    :return: coords
    :rtype: list of tuples
    """
    data["hex_centroid"] = data[[hex_code]].apply(
        lambda row: h3.h3_to_geo(row[hex]), axis=1
    )
    data["lat"], data["long"] = data["hex_centroid"].str
    coords = list(zip(data["lat"], data["long"]))
    return coords


def point_delivery_estimate(account, lat, lon, radius, opt):
    """Point delivery estimate
    :return: _description_
    :rtype: _type_
    """
    params = define_params(lat, lon, radius, opt)
    d_e = account.get_delivery_estimate(params=params)
    delivery_estimate = pd.DataFrame(d_e)
    return delivery_estimate


def get_delivery_estimate(coords):
    """Get delivery estimates from a lists of coordinates

    :return:
    :rtype:
    """
    token, account_id, _, radius, opt = get_facebook_credentials(
        "../../conf/credentials.yaml"
    )
    data = pd.DataFrame()
    _, account = fb_api_init(token, account_id)
    for i, (lat, long) in enumerate(coords[979:]):
        try:
            row = point_delivery_estimate(account, lat, long, radius, opt)
            row["lat"], row["long"] = lat, long
            data = data.append(row, ignore_index=True)
        except Exception as e:
            if e._api_error_code == 80004:
                print("Too many calls!")
                data.to_parquet(f"connectivity_nigeria_{i}.parquet")
                time.sleep(3600)
            else:
                print(f"Point {i}, ({lat, long}) not found.")
                pass


df = pd.read_csv("nga_clean_v1.csv")
coords = get_long_lat(df, "hex_code")
get_delivery_estimate(coords)