import json
import os
from datetime import datetime, timedelta
from scipy import interpolate


def calc_load_scaling_factor(households, avg_consumption):
    load_scaling_factor = (households * avg_consumption) / 1000
    return load_scaling_factor


def calc_dynamic_factor(day_of_year):
    dynamic_factor = (
        -0.000000000392 * day_of_year**4
        + 0.00000032 * day_of_year**3
        + -0.0000702 * day_of_year**2
        + 0.0021 * day_of_year
        + 1.24
    )
    return dynamic_factor


def calc_total_load(slp_value, dynamic_factor, load_scaling_factor):
    dynamic_load = (slp_value * dynamic_factor * load_scaling_factor) / 1000
    return dynamic_load


def generate_forecast(input_folder_path, output_folder_path, time_resolution):
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
            # TO-DO: Update uc name
            uc_name = "balancer"
            start_forecast = datetime.strptime(
                data["start_forecast"], "%Y-%m-%dT%H:%M:%SZ"
            )
            end_forecast = datetime.strptime(data["end_forecast"], "%Y-%m-%dT%H:%M:%SZ")
            # TO-DO: Update day end
            day_end = datetime.strptime(data["end_forecast"], "%Y-%m-%dT%H:%M:%SZ")
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

            print(f"Forecast file generated: {absolute_output_file_path}")

    print("All files processed.")

    return forecast_list