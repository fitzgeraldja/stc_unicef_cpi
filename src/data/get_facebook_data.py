"""Get data from Facebook Marketing API"""

import time
import pandas as pd
import numpy as np
import h3.api.numpy_int as h3

from math import ceil
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


def set_params(lat, lon, radius, opt):

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


def get_long_lat(df):
    # df[hex] = df[hex].astype(int)
    # print(df)
    # df[["hex_centroid"]] = df[[hex]].apply(lambda row: h3.h3_to_geo(row[hex]), axis=1)
    # print(df)
    df[["lat", "long"]] = (
        df["hex_centroid"].str[1:-1].str.split(",", expand=True).astype(float)
    )
    return df


def point_delivery_estimate(account, lat, lon, radius, opt):

    """_summary_

    _extended_summary_

    :return: _description_
    :rtype: _type_
    """
    params = set_params(lat, lon, radius, opt)
    delivery_estimate = account.get_delivery_estimate(params=params)

    return delivery_estimate


def get_delivery_estimate(df, token, id, limit, radius):

    """_summary_

    _extended_summary_

    :return: _description_
    :rtype: _type_
    """
    no_chunks = ceil(len(df) / limit)

    if no_chunks == 1:
        print("Calling Facebook Ads API; collection will take few minutes!")
    else:
        print(
            f"Calling Facebook Ads API; collection will approximately take {(no_chunks - 1)} hour(s)!"
        )

    estimate_dict = {
        "source_school_id": [],
        "estimate_dau": [],
        "estimate_mau": [],
        "estimate_ready": [],
    }

    for c_no, chunk in enumerate(np.array_split(df, no_chunks)):
        print("Getting facebook data for the chunk " + str(c_no) + "...")

        for row in chunk.iterrows():
            out = [row[1].source_school_id]
            try:
                api, account = fb_api_init(token, id)
                est = point_delivery_estimate(
                    account, row[1]["lat"], row[1]["long"], radius
                )
            except:
                pass

            [
                estimate_dict[j].append(i)
                for i, j in zip(out + list(est), estimate_dict.keys())
            ]

        print(
            "Done! Hold for one hour!\nTotal number of requests: "
            + str(api._num_requests_attempted)
            + "\nNumber of remaining chunks: "
            + str(no_chunks - c_no - 1)
        )

        if (no_chunks - c_no - 1) != 0:
            time.sleep(3600)

    return pd.DataFrame(estimate_dict)


def run_code():
    token, account_id, limit, radius, opt = get_facebook_credentials(
        "../../conf/credentials.yaml"
    )
    api, account = fb_api_init(token, account_id)

    # df = point_delivery_estimate(
    #     account, "13.077020922031977", "6.425812475913585", radius, opt
    # )
    # print(df)
    df = pd.read_csv("clean_nga_dhs.csv")
    df = get_long_lat(df)
    print(df)
    m = get_delivery_estimate(df[:10], api, account, limit, radius)
    print(m)
    # df = get_long_lat(df)
    # print(df)


run_code()
