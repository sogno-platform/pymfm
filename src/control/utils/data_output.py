from importlib.metadata import version
import pandas as pd
from datetime import datetime
from pydantic import BaseModel as PydBaseModel, Field
from pyomo.opt import SolverStatus, TerminationCondition
import matplotlib.pyplot as plt
import os


class BaseModel(PydBaseModel):
    class Config:
        allow_population_by_field_name = True
        json_encoders = {datetime: lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")}


class TimeseriesData(BaseModel):
    time: datetime = Field(..., alias="timestamp")
    # XXX this alias should really be Value but it is probably to late to change api
    values: dict[str, float] = Field(..., alias="values")


class ControlOutput(BaseModel):
    version: str
    units: dict[str, str] = Field(default_factory=dict)
    output: list[TimeseriesData]


# XXX not sure why it is structured like this but this is needed to keep the response the same
class ControlOutputWrapper(BaseModel):
    status: str = Field(default="success")
    details: str = Field(default="ok")
    control_output: ControlOutput = Field(..., alias="control_output")


def prep_optimizer_output(
    import_export_profile: pd.Series,
    pv_profile: pd.Series,
    bat_p_supply_profiles: pd.DataFrame,
    bat_soc_supply_profiles: pd.DataFrame,
    df_forecasts: pd.DataFrame,
    imp_exp_upperb,
    imp_exp_lowerb,
):
    result_overview = pd.DataFrame(index=df_forecasts.index)
    result_overview["P_net_forecast"] = (
        df_forecasts["P_load_kW"] - df_forecasts["P_gen_kW"]
    )
    result_overview["P_net_controlled"] = df_forecasts["P_load_kW"] - pv_profile
    result_overview["P_PV_forecast"] = df_forecasts["P_gen_kW"]
    result_overview["P_PV_controlled"] = pv_profile
    result_overview["import_export"] = import_export_profile
    result_overview["upperb"] = imp_exp_upperb
    result_overview["lowerb"] = imp_exp_lowerb
    for col in bat_p_supply_profiles.columns:
        result_overview[f"P_{col}_kW"] = bat_p_supply_profiles[col]
        result_overview[f"SoC_{col}_%"] = bat_soc_supply_profiles[col] * 100

    return result_overview


def values_mapper(col_name: str):
    if col_name.startswith("P_bat"):
        return col_name.removeprefix("P_bat")
    return col_name


def battery_data_output(
    output: pd.DataFrame, status: tuple[SolverStatus, TerminationCondition]
) -> ControlOutputWrapper:
    # Remove "kW" from column names
    output.columns = output.columns.str.replace("_kW", "")
    value_cols = output.columns[
        output.columns.map(lambda col: col == "time" or col.startswith("P_bat"))
    ]
    output = output[value_cols].to_dict(orient="index")
    output = [{"time": time, "values": d} for time, d in output.items()]
    out = ControlOutput(
        version=version("pymfm"),
        units={"time": "ISO8601", "P": "kW"},
        output=output,
    )

    wrapped_output = ControlOutputWrapper(
        status=status[0], details=status[1], control_output=out
    )
    return wrapped_output


def produce_json_output(dataframe):
    """
    Produces a JSON output from a pandas DataFrame with two different time series.

    Parameters:
        dataframe (pandas.DataFrame): The DataFrame containing the data to output.

    Returns:
        None
    """

    # Set output file
    output_file = "results/output.json"

    # Convert the 'timestamp' column to string format
    dataframe['timestamp'] = dataframe.index.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    # Create a dictionary to hold the data for each time series
    json_data = {
        'import_export_upperb_lowerb': {
            'timestamp': dataframe['timestamp'].tolist(),
            'import_export': dataframe['import_export'].tolist(),
            'upperb': dataframe['upperb'].tolist(),
            'lowerb': dataframe['lowerb'].tolist()
        },
        'other_columns': {
            'timestamp': dataframe['timestamp'].tolist(),
        }
    }

    # Add other columns to the 'other_columns' time series in the dictionary
    other_columns = dataframe.columns.difference(['import_export', 'upperb', 'lowerb'])
    for column in other_columns:
        json_data['other_columns'][column] = dataframe[column].tolist()

    # Save the dictionary as JSON to the specified output file
    with open(output_file, 'w') as json_file:
        import json
        json.dump(json_data, json_file)



def produce_excel_output(dataframe):
    """
    Produces an Excel output from a pandas DataFrame with two different time series
    in two separate sheets.

    Parameters:
        dataframe (pandas.DataFrame): The DataFrame containing the data to output.

    Returns:
        None
    """
    # Convert 'timestamp' to timezone-unaware datetime
    dataframe.index = dataframe.index.tz_localize(None)

    # Set output file
    output_file = "results/output.xlsx"

    # Create a Pandas ExcelWriter object
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:

        # Write everything other than import-export data time series to the 'output' sheet
        other_columns = dataframe.columns.difference(['import_export', 'upperb', 'lowerb', 'timestamp'])
        other_columns_df = dataframe[other_columns]
        other_columns_df.to_excel(writer, sheet_name='output')

        # Write the 'import_export_upperb_lowerb' time series to the second sheet
        import_export_upperb_lowerb_df = dataframe[['import_export', 'upperb', 'lowerb']]
        import_export_upperb_lowerb_df.to_excel(writer, sheet_name='import_export_upperb_lowerb')


def visualize_and_save_plots(dataframe: pd.DataFrame):
    """
    Visualizes and saves multiple plots from a pandas DataFrame.

    Parameters:
        dataframe (pandas.DataFrame): The DataFrame containing the data to plot.

    Returns:
        None
    """
    output_directory = "results/"

    # First subplot for 'import_export', 'upperb', and 'lowerb'
    plt.figure(figsize=(12, 8))
    plt.plot(dataframe.index, dataframe['import_export'], label='Total Import and Export')
    plt.plot(dataframe.index, dataframe['upperb'], label='Upperbound')
    plt.plot(dataframe.index, dataframe['lowerb'], label='Lowerbound')
    plt.title("Plot of Total Import and Export and its Boundries")
    plt.xlabel("Timestamp")
    plt.ylabel("Value")
    plt.grid(True)
    plt.legend()
    
    # Save the first plot to a file in the specified output directory
    output_file1 = os.path.join(output_directory, "import_export_upperb_lowerb_plot.png")
    plt.savefig(output_file1)
    
    # Second subplot for other columns
    plt.figure(figsize=(12, 8))
    other_columns = dataframe.columns.difference(['import_export', 'upperb', 'lowerb'])
    for column in other_columns:
        plt.plot(dataframe.index, dataframe[column], label=column)
    plt.title("Output Plot")
    plt.xlabel("Timestamp")
    plt.ylabel("Value")
    plt.grid(True)
    plt.legend()
    
    # Save the second plot to a file in the specified output directory
    output_file2 = os.path.join(output_directory, "output_plot.png")
    plt.savefig(output_file2)

    plt.close()  # Close the current figure to free up resources