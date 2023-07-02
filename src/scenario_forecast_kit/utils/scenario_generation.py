import json
import os

def generate_scenario(forecast_input_file, scenario_input_file, output_file):
    # Read the content of the first input JSON file
    with open(forecast_input_file, "r") as file1:
        data1 = json.load(file1)

    # Read the content of the second input JSON file
    with open(scenario_input_file, "r") as file2:
        data2 = json.load(file2)

    # Extract the required information from each dictionary
    app_data = data1["application"]
    uc_name = data2["uc_name"]
    uc_start = data2["uc_start"]
    uc_end = data2["uc_end"]
    day_end = data2["day_end"]
    bulk_data = data2["bulk"]
    import_export_data = data2["import_export_limitation"]
    generation_and_load_data = data1["generation_and_load"]
    battery_specs_data = data2["battery_specs"]

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

    # Create a set of existing timestamps from the second .json file
    existing_timestamps = {entry["timestamp"] for entry in import_export_data}

    # Iterate through timestamps from the first .json file
    for entry in generation_and_load_data:
        timestamp = entry["timestamp"]
        if timestamp not in existing_timestamps:
            default_entry = {
                "timestamp": timestamp,
                "with_import_limit": False,
                "with_export_limit": False,
                "import_limit": 0,
                "export_limit": 0,
            }
            import_export_data.append(default_entry)

    # Sort the import_export_data list based on the "timestamp" key in ascending order
    import_export_data.sort(key=lambda item: item["timestamp"])

    # Fill missing import/export limits in import_export_data
    for entry in import_export_data:
        if "import_limit" in entry and "export_limit" not in entry:
            entry["with_import_limit"] = True
            entry["with_export_limit"] = False
            entry["export_limit"] = 0
        elif "export_limit" in entry and "import_limit" not in entry:
            entry["with_import_limit"] = False
            entry["with_export_limit"] = True
            entry["import_limit"] = 0

    # Merge the extracted information into a new dictionary
    new_data = {
        "application": app_data,
        "uc_name": uc_name,
        "uc_start": uc_start,
        "uc_end": uc_end,
        "day_end": day_end,
        "bulk": bulk_data,
        "import_export_limitation": [
            {
                "timestamp": item["timestamp"],
                "with_import_limit": item["import_limit"] > 0,
                "with_export_limit": item["export_limit"] > 0,
                "import_limit": item["import_limit"],
                "export_limit": item["export_limit"],
            }
            for item in import_export_data
        ],
        "generation_and_load": generation_and_load_data,
        "battery_specs": battery_specs_data,
    }

    # Convert the new dictionary to a JSON string
    new_json_string = json.dumps(new_data, indent=4)

    # Write the JSON string to the output file
    with open(output_file, "w") as json_file:
        json_file.write(new_json_string)
    # Get the absolute file path of the generated .json file
    absolute_output_file_path = os.path.abspath(output_file)
    print(f"Scenario file generated and saved under: {absolute_output_file_path}")
