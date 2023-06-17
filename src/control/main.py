import json
import os
import pandas as pd
import dateutil.parser
from control_utils.data_input import InputData
from control_utils.control import control
from control_utils import data_output


def open_json(filename):
    with open(filename) as data_file:
        data = json.load(data_file)
    return data


def main():
    fpath = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(fpath, "inputs/input_offline.json")
    data = open_json(filepath)
    # id = Read_input().read_id(data)
    input_data = InputData(**data)
    output, status = control(input_data)
    print(output)
    data_output.output_visualization(output)

    output = data_output.df_to_output(output, input_data.id, status)
    # print(output.json(by_alias=True, sort_keys=False, indent=4))
    with open("results/output_offline.json", "w") as outfile:
        outfile.write(output.json(by_alias=True, sort_keys=False, indent=4))


if __name__ == "__main__":
    main()
