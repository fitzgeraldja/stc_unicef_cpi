import pandas as pd
import numpy as np

COLUMNS_OPHI = [
    "ISO country numeric code",
    "ISO country code",
    "Country",
    "World Region",
    "Survey",
    "Year",
    "Subnational region",
    "MPI of the country",  # range 0 to 1
    "MPI of the region",  # Range 0 to 1
    "Nutrition",  # health # % Population
    "Child mortality",  # health # % Population
    "Years of schooling",  # education # % Population
    "School attendance",  # education # % Population
    "Cooking fuel",  # Living Standards # % Population
    "Sanitation",  # Living Standards # % Population
    "Drinking water",  # Living Standards # % Population
    "Electricity",  # Living Standards # % Population
    "Housing",  # Living Standards # % Population
    "Assets",  # Living Standards # % Population
    "Year of the survey",  # Total Population by Country [Thousands]
    "Population 2018",  # Total Population by Country [Thousands]
    "Population 2019",  # Total Population by Country [Thousands]
    "Population share by region",  # Population 2019 [% Population]
    "Population size by region",  # Population 2019 [% Population]
    "Total number of indicators included (out of ten)",  # included in MPI
    "Indicator (s) missing",
]


def clean_df(path):
    # Read dataframe
    df = pd.read_table(
        path + "/Table-5-Subnational-Results-MPI-2021-uncensored.csv",
        sep=";",
        names=COLUMNS_OPHI,
    )

    # remove the first and last rows that have no information
    df = df.loc[9:1299].copy()
    return df


def get_validation_data(path, country_name="Nigeria"):
    """
    country_name
    subnational_raw: Table 5 uncensored from https://ophi.org.uk/multidimensional-poverty-index/data-tables-do-files/
    """
    # select dataframe
    subnational_df = clean_df(path)

    # select data of a country
    country = subnational_df[subnational_df.Country == country_name].copy()

    # select dimensions
    country = country[
        [
            "Country",
            "Subnational region",
            "Nutrition",
            "School attendance",
            "Sanitation",
            "Drinking water",
            "Housing",
            "Population 2019",
        ]
    ].copy()

    # check that the name of the states are different
    assert country["Subnational region"].nunique() == country.shape[0]

    # Nutrition -> Any person under 70 years of age for whom there is nutritional information is undernourished.
    # School attendance -> Any school-aged child is not attending school up to the age at which he/she would complete class 8.
    # Sanitation -> The household has unimproved or no sanitation facility or it is improved but shared with other households.
    # Drinking water -> The household's source of drinking water is not safe or safe drinking water is a 30-minute or longer walk from home, roundtrip.
    # Housing -> The household has inadequate housing materials in any of the three components: floor, roof, or walls.

    # Replace comma with dot in the different dimensions and convert it to float
    for col in [
        "Nutrition",
        "School attendance",
        "Sanitation",
        "Drinking water",
        "Housing",
    ]:
        country[col] = country[col].apply(lambda x: float(x.replace(",", ".")))

    return country.reset_index(drop=True)


path = "C:/Users/vicin/Desktop/DSSG/Validation Data"  # /Table-5-Subnational-Results-MPI-2021-uncensored.csv
get_validation_data(path, country_name="Nigeria")
