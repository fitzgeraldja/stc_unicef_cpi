import argparse
import glob as glob
import logging
import sys
import os
import time
from functools import partial, reduce
from pathlib import Path

import cartopy.io.shapereader as shpreader
import geopandas as gpd
import h3.api.numpy_int as h3
import numpy as np
import pandas as pd
import pycountry
import rasterio
import rioxarray as rxr
import shapely.wkt
from art import *
from rich import pretty, print

import stc_unicef_cpi.data.process_geotiff as pg
import stc_unicef_cpi.data.process_netcdf as net
import stc_unicef_cpi.utils.constants as c
import stc_unicef_cpi.utils.general as g
import stc_unicef_cpi.utils.geospatial as geo
from stc_unicef_cpi.data.stream_data import RunStreamer
from stc_unicef_cpi.features import get_autoencoder_features as gaf


def read_input_unicef(path_read):
    """read_input_unicef _summary_
    :param path_read: _description_
    :type path_read: _type_
    :return: _description_
    :rtype: _type_
    """
    df = pd.read_csv(path_read, low_memory=False)
    return df


def select_country(df, country_code, lat, long):
    """Select country of interest
    :param df: _description_
    :type df: _type_
    :param country_code: _description_
    :type country_code: _type_
    :param lat: _description_
    :type lat: _type_
    :param long: _description_
    :type long: _type_
    :return: _description_
    :rtype: _type_
    """
    df.columns = df.columns.str.lower()
    subset = df[df["countrycode"].str.strip() == country_code].copy()
    subset.dropna(subset=[lat, long], inplace=True)
    return subset


def aggregate_dataset(df):
    """aggregate_dataset _summary_
    :param df: _description_
    :type df: _type_
    :return: _description_
    :rtype: _type_
    """
    df_mean = df.groupby(by=["hex_code"], as_index=False).mean()
    df_count = df.groupby(by=["hex_code"], as_index=False).count()[
        ["hex_code", "survey"]
    ]
    return df_mean, df_count


def create_target_variable(
    country_code, res, lat, long, threshold, read_dir, copy_to_nbrs=False
):
    try:
        source = Path(read_dir) / "childpoverty_microdata_gps_21jun22.csv"
    except FileNotFoundError:
        raise ValueError(f"Must have raw survey data available in {read_dir}")
    df = read_input_unicef(source)
    sub = select_country(df, country_code, lat, long)
    # Create variables for two or more deprivations
    for k in range(2, 5):
        sub[f"dep_{k}_or_more_sev"] = sub["sumpoor_sev"] >= k
    sub = geo.get_hex_code(sub, lat, long, res)
    sub = sub.reset_index(drop=True)
    if copy_to_nbrs:
        sub["hex_incl_nbrs"] = sub[["location", "hex_code"]].apply(
            lambda row: h3.k_ring(row["hex_code"], 1)
            if row["location"] == 1
            else h3.k_ring(row["hex_code"], 2),
            axis=1,
        )
        sev_cols = [col for col in sub.columns if "_sev" in col]
        other_cols = [
            col
            for col in sub.columns
            if ("int" in str(sub[col].dtype) or "float" in str(sub[col].dtype))
        ]
        agg_dict = {col: "mean" for col in other_cols}
        agg_dict.update({idx: ["mean", "count"] for idx in sev_cols})
        # agg_dict.update({"hhid": "count"})
        sub = sub.explode("hex_incl_nbrs").groupby(by=["hex_incl_nbrs"]).agg(agg_dict)
        sub.columns = ["_".join(col) for col in sub.columns.values]
        sub.rename(
            columns={
                f"{sev}_mean": f"{sev.replace('dep_','').replace('_sev','')}_prev"
                for sev in sev_cols
                if sev != "deprived_sev"
            },
            inplace=True,
        )
        sub.rename(
            columns={
                f"{sev}_count": f"{sev.replace('dep_','').replace('_sev','')}_count"
                for sev in sev_cols
                if sev != "deprived_sev"
            },
            inplace=True,
        )
        sub.drop(columns=["hex_code_mean"], inplace=True)
        survey_threshold = sub[sub.sumpoor_count >= threshold].reset_index().copy()
        survey_threshold.rename(columns={"hex_incl_nbrs": "hex_code"}, inplace=True)
        survey_threshold = geo.get_hex_centroid(survey_threshold, "hex_code")
    else:
        sub_mean, sub_count = aggregate_dataset(sub)
        sub_count = sub_count[sub_count.survey >= threshold]
        survey = geo.get_hex_centroid(sub_mean, "hex_code")
        survey_threshold = sub_count.merge(survey, how="left", on="hex_code")
    return survey_threshold


def change_name_reproject_tiff(
    tiff, attribute, country, read_dir=c.ext_data, out_dir=c.int_data
):
    """Rename attributes and reproject Tiff file
    :param tiff: _description_
    :type tiff: _type_
    :param attributes: _description_
    :type attributes: _type_
    :param country: _description_
    :type country: _type_
    :param read_dir: _description_, defaults to c.ext_data
    :type read_dir: _type_, optional
    """
    with rxr.open_rasterio(tiff) as data:
        fname = Path(tiff).name
        data.attrs["long_name"] = attribute
        data.rio.to_raster(tiff)
        try:
            gee_dir = Path(read_dir) / "gee"
            assert gee_dir.exists()
        except AssertionError:
            raise FileNotFoundError(
                f"Must have GEE data available in {gee_dir} - currently must manually download there from Google Drive."
            )
        p_r = Path(read_dir) / "gee" / f"cpi_poptotal_{country.lower()}_500.tif"
        pg.rxr_reproject_tiff_to_target(tiff, p_r, Path(out_dir) / fname, verbose=True)


@g.timing
def preprocessed_tiff_files(country, read_dir=c.ext_data, out_dir=c.int_data):
    """Preprocess tiff files
    :param country: _description_
    :type country: _type_
    :param read_dir: _description_, defaults to c.ext_data
    :type read_dir: _type_, optional
    :param out_dir: _description_, defaults to c.int_data
    :type out_dir: _type_, optional
    """
    g.create_folder(out_dir)
    # clip gdp ppp 30 arc sec
    print(" -- Clipping gdp pp 30 arc sec")
    if not (Path(read_dir) / (country.lower() + "_gdp_ppp_30.tif")).exists():
        net.netcdf_to_clipped_array(
            Path(read_dir) / "gdp_ppp_30.nc", ctry_name=country, save_dir=read_dir
        )

    # clip ec and gdp
    print(" -- Clipping ec and gdp")
    tifs = glob.glob(str(Path(read_dir) / "*" / "*" / "2019" / "*.tif"))
    if not all(
        [
            (Path(read_dir) / (country.lower() + "_" + str(Path(tif).name))).exists()
            for tif in tifs
        ]
    ):
        partial_func = partial(
            pg.clip_tif_to_ctry, ctry_name=country, save_dir=read_dir
        )
        list(map(partial_func, tifs))

    # reproject resolution + crs
    print(" -- Reprojecting resolution & determining crs")
    econ_tiffs = sorted(glob.glob(str(Path(read_dir) / f"{country.lower()}_*.tif")))
    econ_tiffs = [ele for ele in econ_tiffs if "africa" not in ele]
    if not all([(Path(out_dir) / Path(fname).name).exists() for fname in econ_tiffs]):
        attributes = [
            ["gdp_2019"],
            ["ec_2019"],
            ["gdp_ppp_1990", "gdp_ppp_2000", "gdp_ppp_2015"],
        ]
        mapfunc = partial(change_name_reproject_tiff, country=country)
        list(map(mapfunc, econ_tiffs, attributes))

    # critical infrastructure data
    print(" -- Reprojecting critical infrastructure data")
    cisi_ctry = Path(read_dir) / f"{country.lower()}_africa.tif"
    fname = Path(cisi_ctry).name
    if not (Path(out_dir) / fname).exists():
        cisi = glob.glob(str(Path(read_dir) / "*" / "*" / "010_degree" / "africa.tif"))[
            0
        ]
        pg.clip_tif_to_ctry(cisi, ctry_name=country, save_dir=read_dir)
        p_r = Path(read_dir) / "gee" / f"cpi_poptotal_{country.lower()}_500.tif"
        pg.rxr_reproject_tiff_to_target(
            cisi_ctry, p_r, Path(out_dir) / fname, verbose=True
        )


@g.timing
def preprocessed_speed_test(speed, res, country):
    # speed["geometry"] = speed.geometry.swifter.apply(shapely.wkt.loads)
    # speed = gpd.GeoDataFrame(speed, crs="epsg:4326")
    logging.info("Clipping speed data to country - can take a couple of mins...")
    shpfilename = shpreader.natural_earth(
        resolution="10m", category="cultural", name="admin_0_countries"
    )
    reader = shpreader.Reader(shpfilename)
    world = reader.records()
    country = pycountry.countries.search_fuzzy(args.country)[0]
    ctry_name = country.name
    ctry_geom = next(
        filter(lambda x: x.attributes["NAME"] == ctry_name, world)
    ).geometry
    # now use low res to roughly clip
    world = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
    ctry = world[world.name == country]
    bd_series = speed.geometry.str.replace(r"POLYGON\s\(+|\)", "").str.split(r"\s|,\s")
    speed["min_x"] = bd_series.str[0].astype("float")
    speed["max_y"] = bd_series.str[-1].astype("float")
    minx, miny, maxx, maxy = ctry.bounds.values.T.squeeze()
    # use rough bounds to restrict more or less to country
    speed = speed[
        speed.min_x.between(minx - 1e-1, maxx + 1e-1)
        & speed.max_y.between(miny - 1e-1, maxy + 1e-1)
    ].copy()
    speed["geometry"] = speed.geometry.swifter.apply(shapely.wkt.loads)
    speed = gpd.GeoDataFrame(speed, crs="epsg:4326")
    # only now look for intersection, as expensive
    ctry_geom = gpd.GeoSeries(ctry_geom)
    ctry_geom.crs = "EPSG:4326"
    speed = gpd.sjoin(speed, ctry_geom, how="inner", op="intersects").reset_index(
        drop=True
    )
    tmp = speed.geometry.swifter.apply(
        lambda x: pd.Series(np.array(x.centroid.coords.xy).flatten())
    )
    speed[["long", "lat"]] = tmp
    speed = geo.get_hex_code(speed, "lat", "long", res)
    speed = (
        speed[["hex_code", "avg_d_kbps", "avg_u_kbps"]]
        .groupby("hex_code")
        .mean()
        .reset_index()
    )
    return speed


@g.timing
def preprocessed_commuting_zones(country, res, read_dir=c.ext_data):
    """Preprocess commuting zones"""
    commuting = pd.read_csv(Path(read_dir) / "commuting_zones.csv", low_memory=False)
    commuting = commuting[commuting["country"] == country]
    comm = list(commuting["geometry"])
    comm_zones = pd.concat(list(map(partial(geo.hexes_poly, res=res), comm)))
    comm_zones = comm_zones.merge(commuting, on="geometry", how="left")
    comm_zones = comm_zones.add_suffix("_commuting")
    comm_zones.rename(columns={"hex_code_commuting": "hex_code"}, inplace=True)

    return comm_zones


@g.timing
def append_features_to_hexes(
    country, res, encoders, force=False, audience=False, model_dir=c.base_dir_model, read_dir=c.ext_data, save_dir=c.int_data, tiff_dir=c.tiff_data,
    hyper_tunning=False
):
    """Append features to hexagons withing a country
    :param country_code: _description_, defaults to "NGA"
    :type country_code: str, optional
    :param country: _description_, defaults to "Nigeria"
    :type country: str, optional
    :param lat: _description_, defaults to "latnum"
    :type lat: str, optional
    :param long: _description_, defaults to "longnum"
    :type long: str, optional
    :param res: _description_, defaults to 6
    :type res: int, optional
    """
    # Setting up logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s:%(name)s:%(message)s")
    file_handler = logging.FileHandler(c.dataset_log)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info("Starting process...")

    # Retrieve external data
    print(
        f"Initiating data retrieval. Audience: {audience}. Forced data gathering: {force}"
    )
    RunStreamer(
        country,
        res,
        force,
        audience,
        read_path=str(c.ext_data),
        name_logger=c.str_log,
    )
    logger.info("Finished data retrieval.")
    logger.info(
        f"Please check your 'gee' folder in google drive and download all content to {read_dir}/gee. May take some time to appear."
    )

    # Country hexes
    logger.info(f"Retrieving hexagons for {country} at resolution {res}.")
    hexes_ctry = geo.get_hexes_for_ctry(country, res)
    # expand by 2 hexes to ensure covers all data
    outer_hexes = geo.get_new_nbrs_at_k(hexes_ctry, 2)
    hexes_ctry = np.concatenate((hexes_ctry, outer_hexes))
    ctry = pd.DataFrame(hexes_ctry, columns=["hex_code"])

    # Facebook connectivity metrics
    if audience:
        logger.info(
            f"Collecting audience estimates for {country} at resolution {res}..."
        )
        fb = pd.read_parquet(
            Path(read_dir) / f"fb_aud_{country.lower()}_res{res}.parquet"
        )
        fb = geo.get_hex_centroid(fb)

    # Preprocessed tiff files
    logger.info(f"Preprocessing tiff files from {read_dir} and saving to {save_dir}..")
    preprocessed_tiff_files(country, read_dir, save_dir)

    # Conflict Zones
    logger.info("Reading and computing conflict zone estimates...")
    cz = pd.read_csv(Path(read_dir) / "conflict/GEDEvent_v22_1.csv", low_memory=False)
    cz = cz[cz.country == country]
    cz = geo.get_hex_code(cz, "latitude", "longitude", res)
    cz = geo.create_geometry(cz, "latitude", "longitude")
    cz = geo.aggregate_hexagon(cz, "geometry", "n_conflicts", "count")

    # Commuting zones
    logger.info("Reading and computing commuting zone estimates...")
    commuting = preprocessed_commuting_zones(country, res, read_dir)[c.cols_commuting]

    ## Economic data
    logger.info("Retrieving features from economic tif files...")
    econ_files = glob.glob(str(Path(save_dir) / f"{country.lower()}*.tif"))
    # econ_files = [ele for ele in econ_files if "ppp" not in ele]

    econ = pg.agg_tif_to_df(
        ctry,
        econ_files,
        resolution=res,
        rm_prefix=rf"cpi|_|{country.lower()}|500",
        verbose=True,
    )
    # print(econ.head()) # looks OK
    # econ = list(map(pg.geotiff_to_df, econ_files))
    # NB never want to join on lat long if only need
    # aggregated values - first aggregate then join
    # on hex codes
    # econ = reduce(
    #     lambda left, right: pd.merge(
    #         left, right, on=["latitude", "longitude"], how="outer"
    #     ),
    #     econ,
    # )
    # ppp = glob.glob(str(Path(save_dir) / f"{country.lower()}*ppp*.tif"))[0]
    # ppp = pg.geotiff_to_df(ppp, ["gdp_ppp_1990", "gdp_ppp_2000", "gdp_ppp_2015"])
    # econ = econ.merge(ppp, on=["latitude", "longitude"], how="outer")
    # del ppp  # Clean up memory
    # Google Earth Engine
    logger.info("Retrieving features from google earth engine tif files...")
    gee_files = glob.glob(str(Path(read_dir) / "gee" / f"*_{country.lower()}*.tif"))
    # don't want to do this as loads every tiff as df and
    # loads all into memory at once
    # gee = list(map(pg.geotiff_to_df, gee_files))

    max_bands = 3
    gee_nbands = np.zeros(len(gee_files))
    for idx, file in enumerate(gee_files):
        with rasterio.open(file) as tif:
            gee_nbands[idx] = tif.count
    small_gee = np.array(gee_files)[gee_nbands < max_bands]
    large_gee = np.array(gee_files)[gee_nbands >= max_bands]
    gee = pg.agg_tif_to_df(
        ctry,
        list(small_gee),
        resolution=res,
        rm_prefix=rf"cpi|_|{country.lower()}|500",
        verbose=True,
    )
    for large_file in large_gee:
        gee = gee.join(
            pg.rast_to_agg_df(
                large_file, resolution=res, max_bands=max_bands, verbose=True
            ),
            on="hex_code",
            how="left",
        )
    # gee = reduce(
    #     lambda left, right: pd.merge(
    #         left, right, on=["latitude", "longitude"], how="outer"
    #     ),
    #     gee,
    # )

    # Join GEE with Econ
    logger.info("Merging aggregated features from tiff files to hexagons...")
    # econ.to_csv(Path(save_dir) / f"tmp_{country.lower()}_econ.csv")
    # gee.to_csv(Path(save_dir) / f"tmp_{country.lower()}_gee.csv")
    images = gee.merge(econ, on=["hex_code"], how="outer")
    del econ

    # Road density
    logger.info("Reading road density estimates...")
    road = pd.read_csv(Path(read_dir) / f"road_density_{country.lower()}_res{res}.csv")

    # Speed Test
    logger.info("Reading speed test estimates...")
    speed = pd.read_csv(
        Path(read_dir) / "connectivity" / "2021-10-01_performance_mobile_tiles.csv"
    )
    speed = preprocessed_speed_test(speed, res, country)

    # Open Cell Data
    logger.info("Reading open cell data...")
    cell = g.read_csv_gzip(
        glob.glob(str(Path(read_dir) / f"{country.lower()}_*gz.tmp"))[0]
    )
    cell = geo.get_hex_code(cell, "lat", "long", res)
    cell = cell[["hex_code", "radio", "avg_signal"]]
    cell = (
        cell.groupby(by=["hex_code", "radio"])
        .size()
        .unstack(level=1)
        .fillna(0)
        .join(cell.groupby("hex_code").avg_signal.mean())
    ).reset_index()

    # Collected Data
    logger.info("Merging all features")
    dfs = [ctry, commuting, cz, road, speed, cell, images]
    hexes = reduce(
        lambda left, right: pd.merge(left, right, on="hex_code", how="left"), dfs
    )

    # Get autoencoders
    if encoders:
        tiffs = Path(tiff_dir / country.lower())
        tiffs.mkdir(exist_ok=True)
        print('--- Copying tiff files to tiff directory')
        gaf.copy_files(c.ext_data / "gee", tiffs, country.lower())
        gaf.copy_files(c.ext_data, tiffs, country.lower())
        df = pd.read_csv('/Users/danielapintoveizaga/GitHub/stc_unicef_cpi/data/interim/hexes_nigeria_res7_thres30.csv')
        # check if model is trained, else train model
        modelname = f"autoencoder_{country.lower()}_res{res}.h5"
        if os.path.exists(Path(model_dir) / modelname):
            print('--- Model already saved.')
        else:
            print('--- Training auto encoder...')
            gaf.train_auto_encoder(list(df.hex_code), tiffs, hyper_tunning, model_dir, country, res)
        # check if autoencoder features have been saved
        filename = f"encodings_{country.lower()}_res{res}.csv"
        if os.path.exists(Path(save_dir) / filename):
            print("--- Autoencoding features have already been saved.")
            auto_features = pd.read_csv(Path(save_dir) / filename)
        else:
            print("--- Retrieving autoencoding features...")
            auto_features = gaf.retrieve_autoencoder_features(list(df.hex_code), model_dir, country, res, tiff_dir / country.lower())
            auto_features = pd.DataFrame(
                data=auto_features,
                columns=['f_'+str(i) for i in range(auto_features.shape[1])],
                index=list(df.hex_code)
            ).reset_index().rename({'index': 'hex_code'}, axis=1)
            print(f"--- Saving autoencoding features to {save_dir}...")
            auto_features.to_csv(
                Path(save_dir) / filename,
                index=False,
            )
        hexes = hexes.merge(auto_features, on='hex_code', how='left')

    zero_fill_cols = [
        "n_conflicts",
        "GSM",
        "LTE",
        "NR",
        "UMTS",
    ]
    # where nans mean zero, fill as such
    hexes.fillna(value={col: 0 for col in zero_fill_cols}, inplace=True)
    logger.info("Finishing process...")

    return hexes


@g.timing
def append_target_variable_to_hexes(
    country_code,
    country,
    res,
    encoders=True,
    force=False,
    audience=False,
    hyper_tunning=True,
    lat="latnum",
    long="longnum",
    interim_dir=c.int_data,
    save_dir=c.proc_data,
    model_dir=c.base_dir_model,
    threshold=c.cutoff,
    read_dir_target=c.raw_data,
    read_dir=c.ext_data,
    tiff_dir=c.tiff_data,
):
    tprint("Child Poverty Index", font="cybermedum")
    print(f"Building dataset for {country} at resolution {res}")
    print(
        f"Creating target variable...only available for certain hexagons in {country}"
    )
    train = create_target_variable(
        country_code, res, lat, long, threshold, read_dir_target
    )
    train_expanded = create_target_variable(
        country_code, res, lat, long, threshold, read_dir_target, copy_to_nbrs=True
    )
    print(
        f"Appending  features to all hexagons in {country}. This step might take a while...~20 minutes"
    )
    complete = append_features_to_hexes(
        country, res, encoders, force, audience, model_dir, read_dir, interim_dir, tiff_dir, hyper_tunning
    )
    print(f"Merging target variable to hexagons in {country}")
    complete = complete.merge(train, on="hex_code", how="left")
    print(f"Saving dataset to {save_dir}")
    complete.to_csv(
        Path(save_dir) / f"hexes_{country.lower()}_res{res}_thres{threshold}.csv",
        index=False,
    )
    train_expanded.to_csv(
        Path(save_dir) / f"expanded_{country.lower()}_res{res}_thres{threshold}.csv",
        index=False,
    )
    print("Done!")
    return complete


if __name__ == "__main__":

    parser = argparse.ArgumentParser("High-res multi-dim CPI model training")
    # parser.add_argument(
    #     "-cc",
    #     "--country_code",
    #     type=str,
    #     help="Country code to make dataset for, default is NGA",
    #     default="NGA",
    # )

    parser.add_argument(
        "-c",
        "--country",
        type=str,
        help="Country to make dataset for, default is Nigeria",
        default="Nigeria",
    )

    parser.add_argument(
        "-r",
        "--resolution",
        type=int,
        help="H3 resolution level, default is 7",
        default=7,
    )

    try:
        args = parser.parse_args()
    except argparse.ArgumentError:
        parser.print_help()
        sys.exit(0)
    country = pycountry.countries.search_fuzzy(args.country)[0]
    country_name = country.name
    country_code = country.alpha_3

    append_target_variable_to_hexes(
        country_code=country_code, country=country_name, res=args.resolution
    )

## Health Sites
# hh = pd.read_csv("nga_health.csv")
# hh = hh[~hh.X.isna()]
# hh = create_geometry(hh, "X", "Y")
# hh = get_hex_code(hh, "X", "Y")
# hh = aggregate_hexagon(hh, "geometry", "n_health", "count")
#
#
## Education Facilities
# edu = gpd.read_file("nga_education")
# edu = get_lat_long(edu, "geometry")
# edu = get_hex_code(edu, "lat", "long")
# edu = aggregate_hexagon(edu, "geometry", "n_education", "count")
