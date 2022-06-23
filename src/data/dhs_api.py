import requests
import pandas as pd
import logging


def request_dhs_surveys():
    """API CALL TO DHS PROGRAM

    :return: response
    :type: dataframe
    """
    countries_url = r"https://api.dhsprogram.com/rest/dhs/surveys"
    response = requests.get(countries_url)
    response = pd.DataFrame(response.json()["Data"])

    return response


def valid_surveys(region_filter, year_lower_bound, type_survey):
    """SELECT ONLY INFORMATION OF INTEREST

    :param region_filter: Region of interest
    :type region_filter: str
    :param year_lower_bound: Lowest possible year
    :type year_lower_bound: int
    :param type_survey: Survey type (MICS, DHS)
    :type type_survey: str
    """
    surveys = request_dhs_surveys()
    surveys = surveys[surveys["RegionName"] == region_filter]
    surveys["SurveyYear"] = surveys["SurveyYear"].astype(int)
    surveys = surveys[surveys["SurveyYear"] >= year_lower_bound]
    surveys = surveys[surveys.SurveyType == type_survey]

    return surveys


def get_stats_survey(region_filter, year_lower_bound, type_survey):
    """COMPUTE STATS FROM SURVEY

    :param region_filter: Region of interest
    :type region_filter: str
    :param year_lower_bound: Lowest possible year
    :type year_lower_bound: int
    :param type_survey: Survey type (MICS, DHS)
    :type type_survey: str
    """
    df = valid_surveys(region_filter, year_lower_bound, type_survey)
    print(df.columns)
    logging.basicConfig(
        filename="descriptives_dhs.log", filemode="w", level=logging.DEBUG
    )
    logging.info("Nº OF DHS SURVEYS SINCE 2010")
    logging.info("**********************")
    logging.info(df.groupby("CountryName")["SurveyId"].count().nlargest(60))
    df = df.sort_values(by="SurveyYear", ascending=False)
    df_g = df.groupby("CountryName").sum().reset_index()

    vars = ["CountryName", "NumberofHouseholds", "NumberOfWomen"]
    logging.info("Nº HOUSEHOLDS SURVEYED SINCE 2010")
    logging.info("**********************")
    logging.info(df_g.sort_values(by="NumberofHouseholds")[vars])
    logging.info("Nº OF WOMEN SURVEYED SINCE 2010")
    logging.info("**********************")
    logging.info(df_g.sort_values(by="NumberOfWomen")[vars])


get_stats_survey("Sub-Saharan Africa", 2010, "DHS")
