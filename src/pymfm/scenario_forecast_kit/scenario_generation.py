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


def generate_scenario(forecast_input_file, scenario_input_file, output_file):
    """
    Generate a scenario JSON file by merging information from two input JSON files.

    :param forecast_input_file: Path to the forecast input JSON file.
    :param scenario_input_file: Path to the scenario input JSON file.
    :param output_file: Path to the output JSON file to save the merged scenario.
    :return: None
    """
    # Read the content of the first input JSON file
    with open(forecast_input_file, "r") as file1:
        forecast_data = json.load(file1)

    # Read the content of the second input JSON file
    with open(scenario_input_file, "r") as file2:
        scenario_data = json.load(file2)

    # Extract the required information from each dictionary
    id_data = scenario_data["id"]
    app_data = forecast_data["application"]
    control_logic = scenario_data["control_logic"]
    operation_mode = scenario_data["operation_mode"]
    uc_start = scenario_data["uc_start"]
    uc_end = scenario_data["uc_end"]
    day_end = scenario_data["day_end"]
    generation_and_load_data = forecast_data["generation_and_load"]
    battery_specs_data = scenario_data["battery_specs"]
    # Check if "pv_curtailment" data is present in scenario_data
    pv_curtailment = scenario_data.get("pv_curtailment", None)
    # Check if "bulk" data is present in scenario_data
    bulk_data = scenario_data.get("bulk", None)
    # Check if "P_net_after_kW_limitation" data is present in scenario_data
    P_net_after_kW_data = scenario_data.get("P_net_after_kW_limitation", None)

    # Extract the values from the "generation_and_load" data
    generation_and_load_values = forecast_data["generation_and_load"]

    # Create a new dictionary for "generation_and_load" with updated structure
    # Add "pv_curtailment" data to the new dictionary if it exists in scenario_data
    if pv_curtailment:
        generation_and_load = {
            "pv_curtailment": scenario_data["pv_curtailment"],
            "values": generation_and_load_values,
        }
    else:
        generation_and_load = {"values": generation_and_load_values}

    # Create a set of timestamps from the first .json file
    generation_and_load_timestamps = {
        entry["timestamp"] for entry in generation_and_load_data
    }

    # Check if uc_start, uc_end, and day_end are present in the generation_and_load_timestamps
    if uc_start not in generation_and_load_timestamps:
        print(
            f"Warning: uc_start '{uc_start}' is not present in generation_and_load timestamps."
        )
    if uc_end not in generation_and_load_timestamps:
        print(
            f"Warning: uc_end '{uc_end}' is not present in generation_and_load timestamps."
        )
    if day_end not in generation_and_load_timestamps:
        print(
            f"Warning: day_end '{day_end}' is not present in generation_and_load timestamps."
        )

    # Merge the extracted information into a new dictionary
    new_data = {
        "id": id_data,
        "application": app_data,
        "control_logic": control_logic,
        "operation_mode": operation_mode,
        "uc_start": uc_start,
        "uc_end": uc_end,
        "day_end": day_end,
        "generation_and_load": generation_and_load,
        "battery_specs": battery_specs_data,
    }

    # Add "bulk" data to the new dictionary if it exists in scenario_data
    if bulk_data:
        new_data["bulk"] = bulk_data

    # Add "P_net_after_kW_limitation" data to the new dictionary if it exists in scenario_data
    if P_net_after_kW_data:
        new_data["P_net_after_kW_limitation"] = P_net_after_kW_data

    # Convert the new dictionary to a JSON string
    new_json_string = json.dumps(new_data, indent=4)

    # Write the JSON string to the output file
    with open(output_file, "w") as json_file:
        json_file.write(new_json_string)
    # Get the absolute file path of the generated .json file
    absolute_output_file_path = os.path.abspath(output_file)
    print(f"Scenario file generated and saved under: {absolute_output_file_path}")
