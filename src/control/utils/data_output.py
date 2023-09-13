import pandas as pd
import matplotlib.pyplot as plt
import os
import json
import itertools
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
            dataframe["total_import_export_kW"],
            label="Total Import and Export",
            c="blue",
            lw=2,
        )
        plt.plot(
            dataframe.index, dataframe["upperb"], label="Upperbound", c="orange", lw=2
        )
        plt.plot(
            dataframe.index, dataframe["lowerb"], label="Lowerbound", c="green", lw=2
        )
        plt.title("Plot of Total Import and Export and its Boundaries")
        plt.xlabel("Timestamp")
        plt.ylabel("Value")
        plt.grid(True)
        plt.legend()

        # Set alpha (opacity) for overlapping lines
        alpha = 0.6

        # Apply alpha to the lines to simulate overlapping
        lines = plt.gca().lines
        for line in lines[1:]:
            line.set_alpha(alpha)

        # Save the first plot to an SVG file in the specified output directory
        output_file1 = os.path.join(
            output_directory, f"{mode_logic['ID']}_import_export_upperb_lowerb_plot.svg"
        )
        plt.savefig(output_file1, format="svg")

        # Second subplot for other columns
        plt.figure(figsize=(12, 8))

        # Get a list of all columns to plot except timestamp index
        cols_to_plot = [col for col in dataframe.columns if col != "timestamp"]
        cols_to_plot.remove("upperb")
        cols_to_plot.remove("lowerb")
        cols_to_plot.remove("P_PV_forecast_kW")
        cols_to_plot.remove("P_net_before_controlled_PV_kW")
        cols_to_plot.remove("P_PV_controlled_kW")
        cols_to_plot.remove("total_import_export_kW")


        # Generate a list of distinct colors
        color_cycle = itertools.cycle(plt.cm.tab20.colors)

        for col in cols_to_plot:
            color = next(color_cycle)
            plt.plot(dataframe.index, dataframe[col], label=col, c=color, lw=2)

        plt.title("Output Plot")
        plt.xlabel("Timestamp")
        plt.grid(True)
        plt.legend()

        # Apply alpha to the lines to simulate overlapping
        lines = plt.gca().lines
        for line in lines[1:]:
            line.set_alpha(alpha)

        # Remove y-axis labels
        plt.yticks([])

        # Save the second plot to an SVG file in the specified output directory
        output_file2 = os.path.join(
            output_directory, f"{mode_logic['ID']}_output_plot.svg"
        )
        plt.savefig(output_file2, format="svg")

        plt.close()  # Close the current figure to free up resources

    if mode_logic["CL"] == CL.RULE_BASED:
        if mode_logic["OM"] == OM.SCHEDULING:
            # Plotting the DataFrame
            plt.figure(figsize=(12, 8))

            # Get a list of all columns to plot except timestamp index
            cols_to_plot = [col for col in dataframe.columns if col != "timestamp"]

            # Generate a list of distinct colors
            color_cycle = itertools.cycle(plt.cm.tab20.colors)

            for col in cols_to_plot:
                color = next(color_cycle)
                plt.plot(dataframe.index, dataframe[col], label=col, c=color, lw=2)

            # Customize the plot (labels, titles, legends, etc.) as needed
            plt.xlabel("Timestamp")
            plt.grid(True)
            plt.legend()

            # Set alpha (opacity) for overlapping lines
            alpha = 0.6

            # Apply alpha to the lines to simulate overlapping
            lines = plt.gca().lines
            for line in lines[1:]:
                line.set_alpha(alpha)

            # Remove y-axis labels
            plt.yticks([])

            # Save the plot as an SVG image under the given directory
            output_file = os.path.join(
                output_directory, f"{mode_logic['ID']}_output_plot.svg"
            )
            plt.savefig(output_file, format="svg")
            plt.close()  # Close the current figure to free up resources


def prepare_json(mode_logic: dict, output_df: pd.DataFrame, output_directory: str):
    if mode_logic["CL"] == CL.RULE_BASED:
        if mode_logic["OM"] == OM.NEAR_REAL_TIME:
            formatted_data = {
                "id": mode_logic["ID"],
                "application": "pymfm",
                "control_logic": "rule_based",
                "operation_mode": "near_real_time",
                "timestamp": output_df["timestamp"].isoformat(),
                "P_bat_kW": output_df["P_bat_kW"],
                "SoC_bat_%": output_df["SoC_bat"],
                "P_net_meas_kW": output_df["P_net_meas_kW"],
                "P_net_after_kW": output_df["P_net_after_kW"],
            }

            # Serialize the formatted data to a JSON string with indentation for readability
            json_string = json.dumps(formatted_data, indent=4)

            # Write the JSON string to a file
            output_file = os.path.join(
                output_directory, f"{mode_logic['ID']}_output.json"
            )
            with open(output_file, "w") as json_file:
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
            output_file = os.path.join(
                output_directory, f"{mode_logic['ID']}_output.json"
            )
            with open(output_file, "w") as json_file:
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
        output_file = os.path.join(output_directory, f"{mode_logic['ID']}_output.json")
        with open(output_file, "w") as json_file:
            json_file.write(json_string)
