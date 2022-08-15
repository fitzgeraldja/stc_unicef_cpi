import pandas as pd
from shapely.geometry import Point
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


# NA
# MEarning of output
# Sometimes DHS admin1 is region 1, sometimes it's region2 -- THIS NEEDS TO BE SPECIFIED


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


def weighted_mean(data, column_name):
    data[column_name + "_weighted"] = data.apply(
        lambda x: x[column_name] * x["hhweight"], axis=1
    )
    return data.groupby("admin1", as_index=False)[column_name + "_weighted"].agg(
        lambda x: x.mean(skipna=True)
    )


def save_df(data, country_code, path_save):
    data.to_csv(path_save + "/" + country_code + "_admin1_agg.csv", index=False)


def aggregate_dhs_admin1(
    path_admin1,
    path_dhs,
    country_name,
    country_code,
    col="region2",
    save=False,
    path_save=False,
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

    for col in dimensions:
        country = pd.merge(
            country, weighted_mean(country_dhs, col), how="left", on="admin1"
        )

    if save:
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


path_admin1 = (
    "C:/Users/vicin/Desktop/DSSG/Data/Validation Data/ne_10m_admin_1_states_provinces"
)
path_dhs = r"C:\Users\vicin\Desktop\DSSG\Data\Validation Data"
path_save = r"C:\Users\vicin\Desktop\DSSG\Data\Validation Data\Agg_admin1"

results = aggregate_dhs_admin1(
    path_admin1,
    path_dhs,
    country_name="Togo",
    country_code="TGO",
    col="region",
    save=True,
    path_save=path_save,
)
print(results.shape)
