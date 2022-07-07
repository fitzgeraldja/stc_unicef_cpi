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


def get_long_lat(data, centroid):
    """Get longitude and latitude from centroid point
    :param data: dataset
    :type data: dataframe
    :param centroid: name of column containing centroid variable
    :type centroid: string
    :return: coords
    :rtype: list of tuples
    """
    # df[["hex_centroid"]] = df[[hex]].apply(lambda row: h3.h3_to_geo(row[hex]), axis=1)
    # print(df)
    data[["lat", "long"]] = data[centroid].str[1:-1].str.split(", ", expand=True)
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


def get_delivery_estimate():
    """Get delivery estimates

    :return:
    :rtype:
    """
    df = pd.read_csv("clean_nga_dhs.csv")
    coords = get_long_lat(df, "hex_centroid")
    token, account_id, _, radius, opt = get_facebook_credentials(
        "../../conf/credentials.yaml"
    )
    data = pd.DataFrame()
    _, account = fb_api_init(token, account_id)
    for lat, long in coords:
        while True:
            try:
                row = point_delivery_estimate(account, lat, long, radius, opt)
                row["lat"], row["long"] = lat, long
                data = data.append(row, ignore_index=True)
            except Exception:
                print("There have been too many calls!")
                time.sleep(36000)
                continue
            break

    print(data)
    data.to_parquet("connectivity_nigeria.parquet")


get_delivery_estimate()
