import pandas as pd


def get_data(path_df):
    """get training data"""
    df = pd.read_csv(path_df)
    print(df.shape)
    return df


def get_child_pop(data, scale_factor=25 * 20.6):

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


def get_extra_pop_info(
    path_df, path_pred, scale_factor=25 * 20.6
):  # , path_save = None):
    """
    path df: info about population
    path pred: path to predictions
    """

    df = get_data(path_df)
    """add child population and proportion of children"""
    scale_factor = 25 * 20.6
    df["child_pop"] = get_child_pop(df, scale_factor=25 * 20.6)
    df["population_abs"] = df["population"] * scale_factor
    df["prop_child"] = df.apply(lambda x: x["child_pop"] / x["population_abs"], axis=1)

    predictions = get_data(path_pred)
    predictions = pd.merge(
        predictions,
        df[["hex_code", "child_pop", "population_abs", "prop_child"]],
        how="left",
        on="hex_code",
    )

    return predictions
    # predictions.to_csv(path_save, index=False)
