import json
import os
from utils.data_input import InputData
from utils.mode_logic_handler import mode_logic_handler
from utils import data_output


def open_json(filename):
    with open(filename) as data_file:
        data = json.load(data_file)
    return data


def main(control_method: str):
    fpath = os.path.dirname(os.path.abspath(__file__))
    if control_method == "scheduling_optimization_based":
        # Optimizer based control
        filepath = os.path.join(fpath, "inputs/scheduling_optimization_based.json")
    elif control_method == "scheduling_rule_based":
        # Rule based control
        filepath = os.path.join(fpath, "inputs/scheduling_rule_based.json")
    elif control_method == "near_real_time_rule_based":
        # Optimizer based control
        filepath = os.path.join(fpath, "inputs/near_real_time_rule_based.json")
    else:
        print("You have entered an invalid controlling method.")
    data = open_json(filepath)
    input_data = InputData(**data)
    mode_logic, output_df, status = mode_logic_handler(input_data)

    data_output.prepare_json(mode_logic, output_df, output_directory="results/")

    data_output.visualize_and_save_plots(
        mode_logic, output_df, output_directory="results/"
    )


if __name__ == "__main__":
    main(control_method="near_real_time_rule_based")
