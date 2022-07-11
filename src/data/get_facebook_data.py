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
    for i, (lat, long) in enumerate(coords[979:]):
        # coords[147] prob!!
        # 12.925100390654583 4.114276850465597
        # 12.937335470049032 13.658856220094602
        # 12.458455660302773 13.226811407217733
        # 12.590859285972973 12.676161554371511
        # 12.72501865899576 12.819890365987854
        # 6.333381924196154 6.892878272763654
        # 9.710345808273702 5.383430879183822
        # 10.6605036482887 5.898300880348415
        # 8.607634966320314 10.306819321447255
        # 8.17510218571346 10.141325772840773
        # TODO: try & except for points not found through the API
        # TODO: try & except for calls limit per hour
        print(i, lat, long)
        try:
            row = point_delivery_estimate(account, lat, long, radius, opt)
            row["lat"], row["long"] = lat, long
            data = data.append(row, ignore_index=True)
        except Exception:
            print("There have been too many calls!")
            data.to_parquet(f"connectivity_nigeria_{i}.parquet")
            time.sleep(3600)


get_delivery_estimate()
