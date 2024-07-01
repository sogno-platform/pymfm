# The pymfm framework

# Copyright (C) 2023,
# Institute for Automation of Complex Power Systems (ACS),
# E.ON Energy Research Center (E.ON ERC),
# RWTH Aachen University

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software
# and associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the # rights to use, copy, modify, merge, publish, distribute,
# sublicense, and/or sell copies of the Software, and to permit# persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
# BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import itertools
import json
import os

import matplotlib.pyplot as plt
import pandas as pd

from pymfm.control.utils.common import BaseModel
from pymfm.control.utils.data_input import ControlLogic as CL
from pymfm.control.utils.data_input import OperationMode as OM


def visualize_and_save_plots(mode_logic: dict, dataframe: pd.DataFrame, output_directory: str):
    """Visualize control output data from a DataFrame and save plots as SVG files based on control logic and operation mode.

    Parameters
    ----------
    mode_logic : dict
        containing control logic and operation mode information.
    dataframe : pd.DataFrame
        containing data to be visualized.
    output_directory : str
        Directory where the SVG plots will be saved.
    """
    if mode_logic["CL"] == CL.OPTIMIZATION_BASED:
        # First subplot for 'P_net_after_kW', 'upperb', and 'lowerb'
        plt.figure(figsize=(12, 8))
        plt.plot(
            dataframe.index,
            dataframe["P_net_after_kW"],
            linestyle="--",
            label="P_net_after_kW",
            c="olivedrab",
            lw=2,
        )
        plt.plot(dataframe.index, dataframe["upperb"], label="Upperbound", c="red", lw=2)
        plt.plot(dataframe.index, dataframe["lowerb"], label="Lowerbound", c="red", lw=2)
        plt.title("Net power after and its Boundaries")
        plt.xlabel("Timestamp")
        plt.ylabel("Value")
        plt.grid(True)
        plt.legend()

        # Save the first plot to an SVG file in the specified output directory
        output_file1 = os.path.join(output_directory, f"{mode_logic['ID']}_p_net_after_and_boundries_plot.svg")
        plt.savefig(output_file1, format="svg")

        # Second subplot for power output ('P_net_before_kW', 'P_net_after_kW', and battery power)
        plt.figure(figsize=(12, 8))

        plt.plot(
            dataframe.index,
            dataframe["P_net_before_kW"],
            label="P_net_before_kW",
            c="hotpink",
            lw=2,
        )
        plt.plot(
            dataframe.index,
            dataframe["P_net_after_kW"],
            linestyle="--",
            label="P_net_after_kW",
            c="olivedrab",
            lw=2,
        )
        plt.plot(
            dataframe.index,
            dataframe["P_bat_total_kW"],
            label="P_bat_total_kW",
            c="turquoise",
            lw=2,
        )

        plt.title("The Power Balance")
        plt.xlabel("Timestamp")
        plt.grid(True)
        plt.legend()

        # Save the second plot to an SVG file in the specified output directory
        output_file2 = os.path.join(output_directory, f"{mode_logic['ID']}_power_balance_plot.svg")
        plt.savefig(output_file2, format="svg")

        # Third subplot for battery state of charge ('SoC_bat_n_%')
        plt.figure(figsize=(12, 8))

        # Columns to plot for battery state of charge (detect dynamically)
        battery_soc_columns = [col for col in dataframe.columns if "SoC_bat" in col]
        # Generate a list of distinct colors
        color_cycle = itertools.cycle(plt.cm.tab20.colors)

        for col in battery_soc_columns:
            color = next(color_cycle)
            plt.plot(dataframe.index, dataframe[col], label=col, c=color, lw=2)

        plt.title("State of Charges of the Batteries")
        plt.xlabel("Timestamp")
        plt.grid(True)
        plt.legend()

        # Save the third plot to an SVG file in the specified output directory
        output_file3 = os.path.join(output_directory, f"{mode_logic['ID']}_battery_soc_plot.svg")
        plt.savefig(output_file3, format="svg")

        plt.close()  # Close the current figure to free up resources

    if mode_logic["CL"] == CL.RULE_BASED:
        if mode_logic["OM"] == OM.SCHEDULING:
            # Create a plot for 'P_net_before_kW', 'P_net_after_kW', and 'P_bat_1_kW'
            plt.figure(figsize=(12, 8))

            plt.plot(
                dataframe.index,
                dataframe["P_net_before_kW"],
                label="P_net_before_kW",
                c="hotpink",
                lw=2,
            )
            plt.plot(
                dataframe.index,
                dataframe["P_net_after_kW"],
                linestyle="--",
                label="P_net_after_kW",
                c="olivedrab",
                lw=2,
            )
            plt.plot(
                dataframe.index,
                dataframe["P_bat_1_kW"],
                label="P_bat_1_kW",
                c="turquoise",
                lw=2,
            )

            # Customize the plot (labels, titles, legends, etc.) as needed
            plt.xlabel("Timestamp")
            plt.grid(True)
            plt.legend()

            # Save the plot as an SVG image under the given directory
            output_file = os.path.join(output_directory, f"{mode_logic['ID']}_output_plot.svg")
            plt.savefig(output_file, format="svg")
            plt.close()  # Close the current figure to free up resources

    # Get the absolute file path of the generated .json file
    absolute_output_directory_path = os.path.abspath(output_directory)
    print(f"Output .svg plots generated and saved under: {absolute_output_directory_path}")


def prepare_json(mode_logic: dict, output_df: pd.DataFrame, output_directory: str):
    """Prepare and save output control data as JSON files based on control logic and operation mode.


    Parameters
    ----------
    mode_logic : dict
        containing control logic and operation mode information.
    output_df : pd.DataFrame
        containing data to be saved as JSON.
    output_directory : str
        Directory where the JSON files will be saved.
    """
    if mode_logic["CL"] == CL.RULE_BASED:
        if mode_logic["OM"] == OM.NEAR_REAL_TIME:
            # Prepare JSON data for near real-time rule-based mode
            formatted_data = {
                "id": mode_logic["ID"],
                "application": "pymfm",
                "control_logic": "rule_based",
                "operation_mode": "near_real_time",
                "timestamp": output_df["timestamp"].isoformat(),
                "initial_SoC_bat_%": output_df["initial_SoC_bat_%"],
                "SoC_bat_%": output_df["SoC_bat_%"],
                "P_bat_kW": output_df["P_bat_kW"],
                "P_net_meas_kW": output_df["P_net_meas_kW"],
                "P_net_after_kW": output_df["P_net_after_kW"],
            }

            # Serialize the formatted data to a JSON string with indentation for readability
            json_string = json.dumps(formatted_data, indent=4)

            # Write the JSON string to a file
            output_file = os.path.join(output_directory, f"{mode_logic['ID']}_output.json")
            with open(output_file, "w") as json_file:
                json_file.write(json_string)
                # Save the dictionary as JSON to the specified output file
            # with open(output_path, "w") as json_file:
            #    json.dump(json_data, json_file)

        if mode_logic["OM"] == OM.SCHEDULING:
            # Prepare JSON data for scheduling rule-based mode
            # Extract the timestamps as strings
            output_df["timestamp"] = output_df.index.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            # Create the JSON structure
            result = {
                "id": mode_logic["ID"],
                "application": "pymfm",
                "control_logic": "rule_based",
                "operation_mode": "scheduling",
                "control_start": output_df.index[0].strftime("%Y-%m-%dT%H:%M:%S.%fZ"), # TODO start names changed which one should that be control_start or job_start
                "uc_end": output_df.index[-1].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "results": output_df.to_dict(orient="records"),
            }

            # Serialize the JSON data with indentation for readability
            json_string = json.dumps(result, indent=4)

            # Write the JSON string to a file
            output_file = os.path.join(output_directory, f"{mode_logic['ID']}_output.json")
            with open(output_file, "w") as json_file:
                json_file.write(json_string)

    if mode_logic["CL"] == CL.OPTIMIZATION_BASED:
        # Prepare JSON data for scheduling optimization-based mode
        # Extract the timestamps as strings and reset the index
        output_df["timestamp"] = output_df.index.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # Create the JSON structure
        result = {
            "id": mode_logic["ID"],
            "application": "pymfm",
            "control_logic": "optimization_based",
            "operation_mode": "scheduling",
            "control_start": output_df.index[0].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "uc_end": output_df.index[-1].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "results": output_df.to_dict(orient="records"),
        }

        # Serialize the JSON data with indentation for readability
        json_string = json.dumps(result, indent=4)

        # Write the JSON string to a file
        output_file = os.path.join(output_directory, f"{mode_logic['ID']}_output.json")
        with open(output_file, "w") as json_file:
            json_file.write(json_string)

    # Get the absolute file path of the generated .json file
    absolute_output_file_path = os.path.abspath(output_file)
    print(f"Output .json file generated and saved under: {absolute_output_file_path}")


from datetime import datetime
from importlib.metadata import version
from typing import Dict, List, Optional

import pandas as pd
from pydantic import Field


# class BaseModel(PydBaseModel):
#     class Config:
#         allow_population_by_field_name = True
#         json_encoders = {datetime: lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")}
#         use_enum_values = True


class ResultTimeseries(BaseModel):
    time: datetime
    soc_bat: Dict[str, float] = Field(..., alias="SoC_bat")
    p_bat_kw: Dict[str, float] = Field(..., alias="P_bat_kW")
    p_pv_kw: Optional[float] = Field(None, alias="P_PV_kW")
    p_net_before_kw: float = Field(..., alias="P_net_before_kW")
    p_net_after_kw: float = Field(..., alias="P_net_after_kW")


class BalancerOutput(BaseModel):
    id: str  # XXX this is weird place to have the have, it should be at the highest level
    version: str = version("pymfm")
    peak_imp: Optional[float] = None
    peak_exp: Optional[float] = None
    schedule: List[ResultTimeseries]
    # units: Dict[str, str] = Field(default_factory=dict) # TODO readd


# XXX not sure why it is structured like this but this is needed to keep the response the same
class BalancerOutputWrapper(BaseModel):
    status: str = Field(default="success")
    details: str = Field(default="ok")
    balancer_output: BalancerOutput = Field(..., alias="Balancer_output")


def unstack_keys(d: dict):
    out = dict()
    for key, val in d.items():
        next = out
        # single level column can be done directly
        if isinstance(key, str):
            out[key] = val
            continue
        for k in key:
            # skip empty strings, None etc. these only exist becaus pandas does not like columns with different levels in one DF
            if not k:
                continue
            # if valid key extend the outstructure if necessary and walk.
            last_valid = k
            current = next
            if k not in current:
                current[k] = {}
            next = current[k]
        current[last_valid] = val
    return out


def validate_timestep(d: dict) -> ResultTimeseries:
    return ResultTimeseries(**unstack_keys(d))
