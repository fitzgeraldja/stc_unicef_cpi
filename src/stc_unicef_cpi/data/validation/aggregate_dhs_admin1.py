import pandas as pd
from shapely.geometry import Point
import h3.api.numpy_int as h3

from stc_unicef_cpi.data.validation import get_admin1 as adm1

dimensions = [
    "sumpoor_sev",
    "dep_housing_sev",
    "dep_water_sev",
    "dep_nutrition_sev",
    "dep_health_sev",
    "dep_education_sev",
    "dep_sanitation_sev",
    "deprived_sev",
]


# Sometimes DHS admin1 is region 1, sometimes it's region2 -- THIS NEEDS TO BE SPECIFIED
# The reweighting process could be improved


def get_dic_state_geom(country):
    """Create dic with state and geom
    :param country: dataframe with admin1, geometry columns
    :type country: dataframe
    :return: dictionary with keys admin1 name and value its geometry
    :rtype: dictionary
    """
    dic_geom = dict(zip(country["admin1"], country["geometry"]))
    return dic_geom


def get_dict_state(country_dhs, dic_geom, col="region2"):
    """Create dic with state and dhs code for that state

    :param country_dhs: DHS data for a country
    :type country_dhs: pd Dataframe
    :param dic_geom: dictionary with keys admin1 name and values geometry
    :type dic_geom: dictionary
    :param col: colname with admin1 info (can be region or region2), defaults to "region2"
    :type col: str, optional
    :return: dictionary with keys the admin1 name and value the DHS code for that admin1 area
    :rtype: dictionary
    """
    dic = {}
    for i in country_dhs.index:
        if country_dhs.loc[i][col] in dic.keys():
            pass
        else:
            for key, item in dic_geom.items():
                if Point(
                    country_dhs.loc[i]["LONGNUM"], country_dhs.loc[i]["LATNUM"]
                ).within(item):
                    dic[country_dhs.loc[i][col]] = key

    return dic


# choose country
# merge state
def add_state_to_dhs(country_dhs, dic_dhs, col="region2"):
    """Add column with state (admin1) name to DHS data

    :param country_dhs: DHS data for a country
    :type country_dhs: pd Dataframe
    :param dic_dhs: dictionary with keys the admin1 name and value the DHS code for that admin1 area
    :type dic_dhs: dictionary
    :param col: colname with admin1 info (can be region or region2), defaults to "region2"
    :type col: str, optional
    :return: DHS dataframe with col with admin1 name
    :rtype: pd Dataframe
    """
    country_dhs["admin1"] = country_dhs[col].apply(lambda x: dic_dhs[x])
    return country_dhs


def get_child_pop(data, scale_factor=25 * 20.6):
    """sum columns of children population

    :param data: Data with population information
    :type data: dataframe
    :param scale_factor: scale factor for population, defaults to 515
    :type scale_factor: float, optional
    :return: series with child population
    :rtype: pd Series
    """
    young_cols = [
        "F_0",
        "F_1",
        "F_5",
        "F_10",
        "F_15",
        "M_0",
        "M_1",
        "M_5",
        "M_10",
        "M_15",
    ]
    child_pop = data[young_cols].sum(axis=1) * scale_factor
    return child_pop


def compute_weights(country_dhs, path_train_csv, scale_factor=25 * 20.6, res=7):
    """ Compute weights as a weighted mean for the proportion of children and the DHS household weights

    :param country_dhs: DHS data for a country
    :type country_dhs: pd Dataframe
    :param path_train_csv: path to dataframe with population information
    :type path_train_csv: pd DataFrame
    :param scale_factor: scale factor for population, defaults to 515
    :type scale_factor: float, optional
    :param res: H3 resolution, defaults to 7
    :type res: int, optional
    :return: series with new weights
    :rtype: pd Series
    """
    train_data = pd.read_csv(path_train_csv, dtype={"hex_code": "Int64"})

    # get resolution from train_data
    # res = h3.h3_get_resolution(train_data.iloc[0]["hex_code"])
    country_dhs["hex_code"] = country_dhs.apply(
        lambda x: h3.geo_to_h3(lat=x["LATNUM"], lng=x["LONGNUM"], resolution=res),
        axis=1,
    )
    print("hex_code assigned")

    # get child measure
    train_data["child_pop"] = get_child_pop(train_data, scale_factor=25 * 20.6)

    train_data["population_abs"] = train_data["population"] * scale_factor
    train_data["prop_child"] = train_data["child_pop"] / train_data["population_abs"]

    # merge dataframe
    country_dhs = pd.merge(
        country_dhs,
        train_data[["hex_code", "child_pop", "population_abs", "prop_child"]],
        how="left",
        on="hex_code",
    )

    # get weights
    country_dhs["weight_prop"] = country_dhs["hhweight"] * country_dhs["prop_child"]
    return country_dhs["weight_prop"]


def weighted_mean(data, column_name, col_weights="hhweight"):
    """ Compute weighted means of the column 'column_name' with the weights specified by the col_weights

    :param data: dataframe with column_name and col_weights
    :type data: pd DataFrame
    :param column_name: colname of the 
    :type column_name: str
    :param col_weights: colname of the weights for the weighted mean, defaults to "hhweight"
    :type col_weights: str, optional
    :return: series of the new weights
    :rtype: pd Series
    """
    data[column_name + "_weighted"] = data.apply(
        lambda x: x[column_name] * x[col_weights], axis=1
    )
    return data.groupby("admin1", as_index=False)[column_name + "_weighted"].agg(
        lambda x: x.mean(skipna=True)
    )


def save_df(data, country_code, path_save):
    """Save Dataframe at the given path "

    :param data: dataframe to save
    :type data: pd Dataframe
    :param country_code: country code
    :type country_code: str
    :param path_save: path where to save the file
    :type path_save: str
    """
    data.to_csv(path_save + "/" + country_code + "_admin1_agg.csv", index=False)


def aggregate_dhs_admin1(
    path_admin1,
    path_dhs,
    path_train_csv,
    country_name,
    country_code,
    col="region2",
    save=False,
    path_save=False,
    scale_factor=25 * 20.6,
    res=7,
    weights_on_pop=False,
):
    """ Aggregate DHS data at the admin level 1 using DHS household weights or reweighting them on population

    :param path_admin1: path with admin1 
    :type path_admin1: str
    :param path_dhs: path to DHS data
    :type path_dhs: str
    :param path_train_csv: path to dataframe with population information
    :type path_train_csv: pd DataFrame
    :param country_name: name of the country
    :type country_name: str
    :param country_code: code of the country
    :type country_code: str
    :param col: colname with admin1 info (can be region or region2), defaults to "region2"
    :type col: str, optional
    :param save: boolean to save dataframe, defaults to False
    :type save: bool, optional
    :param path_save: path where to save the file, defaults to False
    :type path_save: str, optional
    :param scale_factor: scale factor for population, defaults to 515
    :type scale_factor: float, optional
    :param res: H3 resolutions, defaults to 7
    :type res: int, optional
    :param weights_on_pop: if true consider weights based on population, otherwise the DHS weights, defaults to False
    :type weights_on_pop: bool, optional
    :return: dataframe with admin1 data for country and DHS data aggregated
    :rtype: pd Dataframe
    """
    # get world
    world = adm1.get_world_admin1(path_admin1)
    country = adm1.get_country_admin1(world, country_name)
    dic_geom = get_dic_state_geom(country)

    # download dhs
    # select country of dhs
    dhs = pd.read_csv(
        path_dhs + "/childpoverty_microdata_gps_21jun22.csv", low_memory=False
    )
    # FROM COUNTRY NAME DERIVE CODE
    country_dhs = dhs[dhs.countrycode == country_code].copy()
    dic_dhs = get_dict_state(country_dhs, dic_geom, col)
    country_dhs = add_state_to_dhs(country_dhs, dic_dhs, col)

    # If weights_on_pop is True, computes the weights considering population
    # otherwise just considering hhweight
    if weights_on_pop:
        # compute weights
        print("Compute Weights")
        country_dhs["weight_prop"] = list(
            compute_weights(country_dhs, path_train_csv, scale_factor, res)
        )
        col_weights = "weight_prop"
        print("compute weights done")
    else:
        col_weights = "hhweight"

    for col in dimensions:
        country = pd.merge(
            country,
            weighted_mean(country_dhs, col, col_weights),
            how="left",
            on="admin1",
        )

    print("save")
    if save:
        # Here I should check that path_save makes sense
        # print(country.columns)
        country_save = country[
            [
                "country",
                "admin1",
                # "geometry",
                "sumpoor_sev_weighted",
                "dep_housing_sev_weighted",
                "dep_water_sev_weighted",
                "dep_nutrition_sev_weighted",
                "dep_health_sev_weighted",
                "dep_education_sev_weighted",
                "dep_sanitation_sev_weighted",
                "deprived_sev_weighted",
            ]
        ].copy()
        save_df(country_save, country_code, path_save)
        print("File saved")
        # except:
        #     print(f"Unable to save file, check path: {path_save}")
    print("saving done")
    return country


print("Try2")
path_admin1 = (
    "C:/Users/vicin/Desktop/DSSG/Data/Validation Data/ne_10m_admin_1_states_provinces"
)
path_dhs = "C:/Users/vicin/Desktop/DSSG/Data/DHS"
path_train_csv = (
    r"C:\Users\vicin\Desktop\DSSG\Data\Training Data\nga_pop.csv"  # I only need the pop data
    # "C:/Users/vicin/Desktop/DSSG/Data/Training Data/hexes_nigeria_res7_thres30.csv"
)
path_save = "C:/Users/vicin/Desktop/DSSG/Data/Validation Data/Agg_admin1"


# path_save = "C:/Users/vicin/Desktop/DSSG/Data/Validation Data/Agg_admin1"

# results = aggregate_dhs_admin1(
#     path_admin1,
#     path_dhs,
#     path_train_csv,
#     country_name="Togo",
#     country_code="TGO",
#     col="region",
#     save=True,
#     path_save=path_save,
#     res=7,
# )
# print(results.shape)
