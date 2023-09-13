import pandas as pd
import matplotlib.pyplot as plt
import os
import json
from utils.data_input import (
    ControlLogic as CL,
    OperationMode as OM,
)


def visualize_and_save_plots(
    mode_logic: dict, dataframe: pd.DataFrame, output_directory: str
):
    if mode_logic["CL"] == CL.OPTIMIZATION_BASED:
        # First subplot for 'P_net_after_kW', 'upperb', and 'lowerb'
        plt.figure(figsize=(12, 8))
        plt.plot(
            dataframe.index,
            dataframe["P_net_after_kW"],
            label="Total Import and Export",
        )
        plt.plot(dataframe.index, dataframe["upperb"], label="Upperbound")
        plt.plot(dataframe.index, dataframe["lowerb"], label="Lowerbound")
        plt.title("Plot of Total Import and Export (=P_net_after_kW) and its Boundries")
        plt.xlabel("Timestamp")
        plt.ylabel("Value")
        plt.grid(True)
        plt.legend()

        # Save the first plot to a file in the specified output directory
        output_file1 = os.path.join(
            output_directory, "import_export_upperb_lowerb_plot.png"
        )
        plt.savefig(output_file1)

        # Second subplot for other columns
        plt.figure(figsize=(12, 8))
        plt.plot(
            dataframe.index, dataframe["P_PV_controlled_kW"], label="P_PV_controlled_kW"
        )
        plt.plot(
            dataframe.index, dataframe["P_PV_forecast_kW"], label="P_PV_forecast_kW"
        )
        plt.plot(dataframe.index, dataframe["P_bat_1_kW"], label="P_bat_1_kW")
        plt.plot(dataframe.index, dataframe["P_bat_2_kW"], label="P_bat_2_kW")
        plt.plot(dataframe.index, dataframe["P_net_after_kW"], label="P_net_after_kW")
        plt.plot(
            dataframe.index,
            dataframe["P_net_before_controlled_PV_kW"],
            label="P_net_before_controlled_PV_kW",
        )
        plt.plot(dataframe.index, dataframe["P_net_before_kW"], label="P_net_before_kW")
        plt.plot(dataframe.index, dataframe["SoC_bat_1_%"], label="SoC_bat_1_%")
        plt.plot(dataframe.index, dataframe["SoC_bat_2_%"], label="SoC_bat_2_%")
        plt.title("Output Plot")
        plt.xlabel("Timestamp")
        plt.ylabel("Value")
        plt.grid(True)
        plt.legend()

        # Save the second plot to a file in the specified output directory
        output_file2 = os.path.join(output_directory, "output_plot.png")
        plt.savefig(output_file2)

        plt.close()  # Close the current figure to free up resources

    if mode_logic["CL"] == CL.RULE_BASED:
        if mode_logic["OM"] == OM.SCHEDULING:
            # Plotting the DataFrame
            plt.figure(figsize=(12, 8))  # Adjust the figure size as needed
            plt.plot(
                dataframe.index, dataframe["P_net_before_kW"], label="P_net_before_kW"
            )
            plt.plot(
                dataframe.index, dataframe["P_net_after_kW"], label="P_net_after_kW"
            )
            plt.plot(dataframe.index, dataframe["P_bat_1_kW"], label="P_bat_1_kW")
            plt.plot(dataframe.index, dataframe["SoC_bat_1_%"], label="SoC_bat_1_%")

            # Customize the plot (labels, titles, legends, etc.) as needed
            plt.xlabel("Timestamp")
            plt.ylabel("Values")
            plt.title("Output Plot for Rule Based Scheduling")
            plt.grid(True)
            plt.legend()

            # Save the plot as an image under the given directory
            output_file = os.path.join(output_directory, "output_plot.png")
            plt.savefig(output_file)
            plt.close()  # Close the current figure to free up resources


def prepare_json(mode_logic: dict, output_df: pd.DataFrame, output_path: str):
    if mode_logic["CL"] == CL.RULE_BASED:
        if mode_logic["OM"] == OM.NEAR_REAL_TIME:
            formatted_data = {
                "id": mode_logic["ID"],
                "application": "pymfm",
                "control_logic": "rule_based",
                "operation_mode": "near_real_time",
                "timestamp": output_df["timestamp"].isoformat(),
                "P_bat_kW": output_df["P_bat_kW"],
                "SoC_bat": output_df["SoC_bat"],
                "P_net_meas_kW": output_df["P_net_meas_kW"],
                "P_net_after_kW": output_df["P_net_after_kW"],
            }

            # Serialize the formatted data to a JSON string with indentation for readability
            json_string = json.dumps(formatted_data, indent=4)

            # Write the JSON string to a file
            with open(output_path, "w") as json_file:
                json_file.write(json_string)
                # Save the dictionary as JSON to the specified output file
            # with open(output_path, "w") as json_file:
            #    json.dump(json_data, json_file)

        if mode_logic["OM"] == OM.SCHEDULING:
            # Extract the timestamps as strings
            output_df["timestamp"] = output_df.index.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            # Create the JSON structure
            result = {
                "id": mode_logic["ID"],
                "application": "pymfm",
                "control_logic": "rule_based",
                "operation_mode": "scheduling",
                "uc_start": output_df.index[0].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "uc_end": output_df.index[-1].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "results": output_df.to_dict(orient="records"),
            }

            # Serialize the JSON data with indentation for readability
            json_string = json.dumps(result, indent=4)

            # Write the JSON string to a file
            with open(output_path, "w") as json_file:
                json_file.write(json_string)

    if mode_logic["CL"] == CL.OPTIMIZATION_BASED:
        # Extract the timestamps as strings and reset the index
        output_df["timestamp"] = output_df.index.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # Create the JSON structure
        result = {
            "id": mode_logic["ID"],
            "application": "pymfm",
            "control_logic": "optimization_based",
            "operation_mode": "scheduling",
            "uc_start": output_df.index[0].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "uc_end": output_df.index[-1].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "results": output_df.to_dict(orient="records"),
        }

        # Serialize the JSON data with indentation for readability
        json_string = json.dumps(result, indent=4)

        # Write the JSON string to a file
        with open(output_path, "w") as json_file:
            json_file.write(json_string)
