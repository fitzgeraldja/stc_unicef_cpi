import requests
import pandas as pd
import logging


def request_dhs_surveys():
    """API call to DHS

    :return: survey
    :rtype: _type_
    """
    countries_url = r"https://api.dhsprogram.com/rest/dhs/surveys"
    response = requests.get(countries_url)
    surveys = pd.DataFrame(response.json()["Data"])

    return surveys


def valid_surveys(region_filter, year_lower_bound, type_survey):
    """valid_surveys _summary_

    _extended_summary_

    :param region_filter: _description_
    :type region_filter: _type_
    :param year_lower_bound: _description_
    :type year_lower_bound: _type_
    :param type_survey: _description_
    :type type_survey: _type_
    """
    surveys = request_dhs_surveys()
    surveys = surveys[surveys["RegionName"] == region_filter]
    surveys["SurveyYear"] = surveys["SurveyYear"].astype(int)
    surveys = surveys[surveys["SurveyYear"] >= year_lower_bound]
    surveys = surveys[surveys.SurveyType == type_survey]

    return surveys


def get_stats_survey(region_filter, year_lower_bound, type_survey):
    """stats_survey _summary_

    _extended_summary_

    :param df: _description_
    :type df: _type_
    """
    df = valid_surveys(region_filter, year_lower_bound, type_survey)
    logging.basicConfig(
        filename="descriptives_dhs.log", filemode="w", level=logging.DEBUG
    )
    logging.info("Nº OF SURVEYS PER YEAR")
    logging.info("**********************")
    logging.info(df.groupby("CountryName")["SurveyId"].count().nlargest(60))
    df = df.sort_values(by="SurveyYear", ascending=False)
    unique = df.drop_duplicates("CountryName", keep="first").reset_index(drop=True)
    logging.info(unique)
    vars = ["CountryName", "NumberofHouseholds", "NumberOfWomen", "SurveyYear"]
    logging.info("Nº HOUSEHOLDS SURVEYED IN MOST RECENT SURVEY")
    logging.info("**********************")
    logging.info(unique.sort_values(by="NumberofHouseholds")[vars])
    logging.info("Nº OF WOMEN SURVEYED IN MOST RECENT SURVEY")
    logging.info("**********************")
    logging.info(unique.sort_values(by="NumberOfWomen")[vars])


get_stats_survey("Sub-Saharan Africa", 2010, "DHS")
