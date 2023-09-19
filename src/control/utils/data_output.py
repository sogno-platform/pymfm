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
    """

    :param mode_logic:
    :param dataframe:
    :param output_directory:
    :return:
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
        plt.plot(
            dataframe.index, dataframe["upperb"], label="Upperbound", c="red", lw=2
        )
        plt.plot(
            dataframe.index, dataframe["lowerb"], label="Lowerbound", c="red", lw=2
        )
        plt.title("Net power after and its Boundaries")
        plt.xlabel("Timestamp")
        plt.ylabel("Value")
        plt.grid(True)
        plt.legend()

        # Save the first plot to an SVG file in the specified output directory
        output_file1 = os.path.join(
            output_directory, f"{mode_logic['ID']}_p_net_after_and_boundries_plot.svg"
        )
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
        output_file2 = os.path.join(
            output_directory, f"{mode_logic['ID']}_power_balance_plot.svg"
        )
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
        output_file3 = os.path.join(
            output_directory, f"{mode_logic['ID']}_battery_soc_plot.svg"
        )
        plt.savefig(output_file3, format="svg")

        plt.close()  # Close the current figure to free up resources

    if mode_logic["CL"] == CL.RULE_BASED:
        if mode_logic["OM"] == OM.SCHEDULING:
            # Plotting the DataFrame
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
            output_file = os.path.join(
                output_directory, f"{mode_logic['ID']}_output_plot.svg"
            )
            plt.savefig(output_file, format="svg")
            plt.close()  # Close the current figure to free up resources
    # Get the absolute file path of the generated .json file
    absolute_output_directory_path = os.path.abspath(output_directory)
    print(
        f"Output .svg plots generated and saved under: {absolute_output_directory_path}"
    )


def prepare_json(mode_logic: dict, output_df: pd.DataFrame, output_directory: str):
    """

    :param mode_logic:
    :param output_df:
    :param output_directory:
    :return:
    """
    if mode_logic["CL"] == CL.RULE_BASED:
        if mode_logic["OM"] == OM.NEAR_REAL_TIME:
            formatted_data = {
                "id": mode_logic["ID"],
                "application": "pymfm",
                "control_logic": "rule_based",
                "operation_mode": "near_real_time",
                "timestamp": output_df["timestamp"].isoformat(),
                "initial_SoC_bat_%": output_df["initial_SoC_bat_%"] * 100,
                "SoC_bat_%": output_df["SoC_bat_%"],
                "P_bat_kW": output_df["P_bat_kW"],
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

    # Get the absolute file path of the generated .json file
    absolute_output_file_path = os.path.abspath(output_file)
    print(f"Output .json file generated and saved under: {absolute_output_file_path}")
