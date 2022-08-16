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
    """Create dic with state and geom"""
    dic_geom = dict(zip(country["admin1"], country["geometry"]))
    return dic_geom


def get_dict_state(country_dhs, dic_geom, col="region2"):
    """Create dic with state and dhs code for that state"""
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
    country_dhs["admin1"] = country_dhs[col].apply(lambda x: dic_dhs[x])
    return country_dhs


def get_child_pop(data, scale_factor=25 * 20.6):
    """sum columns of children population"""
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


def compute_weights(country_dhs, path_train, scale_factor=25 * 20.6):

    train_data = pd.read_csv(path_train)
    # get resolution from train_data
    res = h3.h3_get_resolution(train_data.loc[0]["hex_code"])
    country_dhs["hex_code"] = country_dhs.apply(
        lambda x: h3.geo_to_h3(lat=x["LATNUM"], lng=x["LONGNUM"], resolution=res),
        axis=1,
    )

    # get child measure
    scale_factor = 25 * 20.6
    train_data["child_pop"] = get_child_pop(train_data, scale_factor=25 * 20.6)
    train_data["population_abs"] = train_data["population"] * scale_factor
    train_data["prop_child"] = train_data.apply(
        lambda x: x["child_pop"] / x["population_abs"], axis=1
    )

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
    data[column_name + "_weighted"] = data.apply(
        lambda x: x[column_name] * x[col_weights], axis=1
    )
    return data.groupby("admin1", as_index=False)[column_name + "_weighted"].agg(
        lambda x: x.mean(skipna=True)
    )


def save_df(data, country_code, path_save):
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
):
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

    # compute weights
    print("Compute Weights")
    country_dhs["weight_prop"] = list(
        compute_weights(country_dhs, path_train_csv, scale_factor)
    )

    for col in dimensions:
        country = pd.merge(
            country,
            weighted_mean(country_dhs, col, "weight_prop"),
            how="left",
            on="admin1",
        )

    if save:
        # Here I should check that path_save makes sense
        if save:
            # print(country.columns)
            country_save = country[
                [
                    "country",
                    "admin1",
                    "geometry",
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

    return country


print("Try1")
path_admin1 = (
    "C:/Users/vicin/Desktop/DSSG/Data/Validation Data/ne_10m_admin_1_states_provinces"
)
path_dhs = "C:/Users/vicin\Desktop/DSSG/Data/DHS"
path_train_csv = (
    "C:/Users/vicin/Desktop/DSSG/Data/Training Data/hexes_nigeria_res7_thres30.csv"
)
path_save = "C:/Users/vicin/Desktop/DSSG/Data/Validation Data/Agg_admin1"

results = aggregate_dhs_admin1(
    path_admin1,
    path_dhs,
    path_train_csv,
    country_name="Togo",
    country_code="TGO",
    col="region",
    save=True,
    path_save=path_save,
)
print(results.shape)
