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
#substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING 
# BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND 
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import json
import os
from datetime import datetime, timedelta
from scipy import interpolate


def calc_load_scaling_factor(households, avg_consumption):
    """
    Calculate the load scaling factor for a given number of households and average consumption.

    :param households: The number of households.
    :param avg_consumption: The average consumption in kWh per household.
    :return: The load scaling factor.
    """
    load_scaling_factor = (households * avg_consumption) / 1000
    return load_scaling_factor


def calc_dynamic_factor(day_of_year):
    """
    Calculate the dynamic factor for a given day of the year.

    :param day_of_year: The day of the year (1-365).
    :return: The dynamic factor.
    """
    dynamic_factor = (
        -0.000000000392 * day_of_year**4
        + 0.00000032 * day_of_year**3
        + -0.0000702 * day_of_year**2
        + 0.0021 * day_of_year
        + 1.24
    )
    return dynamic_factor


def calc_total_load(slp_value, dynamic_factor, load_scaling_factor):
    """
    Calculate the total load for a given SLP (Standard Load Profile) value, dynamic factor, and load scaling factor.

    :param slp_value: The SLP value for a specific timestamp.
    :param dynamic_factor: The dynamic factor for the day.
    :param load_scaling_factor: The load scaling factor.
    :return: The total dynamic load in kW.
    """
    dynamic_load = (slp_value * dynamic_factor * load_scaling_factor) / 1000
    return dynamic_load


def generate_forecast(input_folder_path, output_folder_path, time_resolution):
    """
    Generate a forecast based on input JSON files and save the results in the output folder.

    :param input_folder_path: Path to the folder containing input JSON files.
    :param output_folder_path: Path to the folder where output JSON files will be saved.
    :param time_resolution: Time resolution in minutes for the forecast.
    :return: A list of forecast data for each input file.
    """
    # Create the output folder if it doesn't exist
    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)

    # Output scenario list
    forecast_list = []

    # Process each JSON file in the input folder
    for filename in os.listdir(input_folder_path):
        if filename.endswith(".json"):
            input_file_path = os.path.join(input_folder_path, filename)

            # Load the input JSON file
            with open(input_file_path) as file:
                data = json.load(file)

            # Extract relevant data from the input JSON
            application = data["application"]
            start_forecast = datetime.strptime(
                data["start_forecast"], "%Y-%m-%dT%H:%M:%SZ"
            )
            end_forecast = datetime.strptime(data["end_forecast"], "%Y-%m-%dT%H:%M:%SZ")
            avg_consumption = data["household_sta"]["metadata"]["avgconsumption"]
            households = data["household_sta"]["metadata"]["households"]
            slp_values = data["household_sta"]["slp_values"]
            pv_forecast = data["pv_forecast"]["pv_values"]

            # Calculate load scaling factor
            load_scaling_factor = calc_load_scaling_factor(households, avg_consumption)

            # Create a list to store the generation and load data
            generation_and_load = []

            # Iterate over the timestamps from uc_start to uc_end with the desired time resolution
            timestamp = start_forecast
            while timestamp <= end_forecast:
                # Calculate the day of the year
                day_of_year = timestamp.timetuple().tm_yday

                # Calculate the dynamic factor
                dynamic_factor = calc_dynamic_factor(day_of_year)

                # Convert timestamp strings to datetime objects
                slp_timestamps = [
                    datetime.strptime(entry["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ")
                    for entry in slp_values
                ]
                pv_timestamps = [
                    datetime.strptime(entry["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ")
                    for entry in pv_forecast
                ]

                # Calculate P_load_kW
                slp_value = interpolate.interp1d(
                    [ts.timestamp() for ts in slp_timestamps],
                    [entry["value"] for entry in slp_values],
                )(timestamp.timestamp())
                p_load_kw = calc_total_load(
                    slp_value, dynamic_factor, load_scaling_factor
                )

                # Calculate P_gen_kW
                pv_value = interpolate.interp1d(
                    [ts.timestamp() for ts in pv_timestamps],
                    [entry["value"] for entry in pv_forecast],
                )(timestamp.timestamp())
                p_gen_kw = pv_value.tolist()  # Convert ndarray to list

                # Add the data point to the list
                generation_and_load.append(
                    {
                        "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                        "P_gen_kW": p_gen_kw,
                        "P_load_kW": p_load_kw,
                    }
                )

                # Increment the timestamp by the desired time resolution
                timestamp += timedelta(minutes=time_resolution)

            # Create the output JSON object
            output_data = {
                "application": application,
                "start_forecast": start_forecast.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "end_forecast": end_forecast.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "generation_and_load": generation_and_load,
            }

            # Add output data of the input file to the output scenario list
            forecast_list.append(output_data)

            # The output file name
            # Get the start date of the forecast
            start_date = datetime.strptime(
                output_data["start_forecast"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ).strftime("%Y-%m-%d")
            output_filename = f"forecast_{start_date}.json"

            # Generate the output file path
            output_file_path = os.path.join(output_folder_path, output_filename)

            # Save the output JSON file
            with open(output_file_path, "w") as file:
                json.dump(output_data, file, indent=4)
            # Get the absolute file path of the generated .json file
            absolute_output_file_path = os.path.abspath(output_file_path)

            print(
                f"Forecast file generated and saved under: {absolute_output_file_path}"
            )

    print("All files processed.")

    return forecast_list
