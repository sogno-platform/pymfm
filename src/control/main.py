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


def main(optimizer=True):
    fpath = os.path.dirname(os.path.abspath(__file__))
    if optimizer == True:
        # Optimizer based control
        filepath = os.path.join(fpath, "inputs/optimizer_offline.json")
    else:
        # Rule based control
        filepath = os.path.join(fpath, "inputs/rule_based_offline.json")
    data = open_json(filepath)
    input_data = InputData(**data)
    output, status = control(input_data)
    print(output)
    data_output.output_visualization(output)

    output = data_output.df_to_output(output, status)
    with open("results/output_offline.json", "w") as outfile:
        outfile.write(output.json(by_alias=True, sort_keys=False, indent=4))


if __name__ == "__main__":
    main(optimizer=True)
