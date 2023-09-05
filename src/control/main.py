import json
import os
import pandas as pd
import dateutil.parser
from utils.data_input import InputData
from utils.control import control
from utils import data_output


def open_json(filename):
    with open(filename) as data_file:
        data = json.load(data_file)
    return data


def main(control_method: str):
    fpath = os.path.dirname(os.path.abspath(__file__))
    if control_method == 'optimizer':
        # Optimizer based control
        filepath = os.path.join(fpath, "inputs/optimizer_offline.json")
    elif control_method == 'rule_based':
        # Rule based control
        filepath = os.path.join(fpath, "inputs/rule_based_offline.json")
    elif control_method == 'near_real_time':
        # Optimizer based control
        filepath = os.path.join(fpath, "inputs/near_real_time.json")
    else:
        print("You have entered an invalid controlling method.")
    data = open_json(filepath)
    input_data = InputData(**data)
    output_df, status = control(input_data)
    print(output_df)

    #data_output.visualize_and_save_plots(output_df)
    #data_output.produce_json_output(output_df)
    #data_output.produce_excel_output(output_df)

    #battery_data_output = data_output.battery_data_output(output_df, status)
    #with open("results/output_offline_batteries.json", "w") as outfile:
    #    outfile.write(battery_data_output.json(by_alias=True, sort_keys=False, indent=4))


if __name__ == "__main__":
    main(control_method='optimizer')
