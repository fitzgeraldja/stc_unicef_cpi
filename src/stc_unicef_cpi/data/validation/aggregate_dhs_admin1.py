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


def get_dic_state_geom(country):
    """Create dic with state and geom"""
    dic_geom = dict(zip(country["admin1"], country["geometry"]))
    return dic_geom


def x(country_dhs, dic_geom):
    """Create dic with state and dhs code for that state"""
    dic = {}
    for i in country_dhs.index:
        if country_dhs.loc[i]["region2"] in dic.keys():
            pass
        else:
            for key, item in dic_geom.items():
                if Point(
                    country_dhs.loc[i]["LONGNUM"], country_dhs.loc[i]["LATNUM"]
                ).within(item):
                    dic[country_dhs.loc[i]["region2"]] = key

    return dic


# choose country

# merge state
def add_state_to_dhs(country_dhs, dic_dhs):
    country_dhs["admin1"] = country_dhs["region2"].apply(lambda x: dic_dhs[x])
    return country_dhs


def weighted_mean(data, column_name):
    data[column_name] = data.apply(lambda x: x[column_name] * x["hhweight"], axis=1)
    return data.groupby("admin1", as_index=False)[column_name].agg(
        lambda x: x.mean(skipna=True)
    )


def aggregate_dhs_admin1(path_admin1, path_dhs, country_name, country_code):
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
    dic_dhs = x(country_dhs, dic_geom)
    country_dhs = add_state_to_dhs(country_dhs, dic_dhs)

    for col in dimensions:
        country = pd.merge(
            country, weighted_mean(country_dhs, col), how="left", on="admin1"
        )

    return country


path_admin1 = (
    "C:/Users/vicin/Desktop/DSSG/Validation Data/ne_10m_admin_1_states_provinces"
)
path_dhs = r"C:\Users\vicin\Desktop\DSSG\Validation Data"
results = aggregate_dhs_admin1(
    path_admin1, path_dhs, country_name="Nigeria", country_code="NGA"
)
print(results.shape)
