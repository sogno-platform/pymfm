import json
import os
from pymfm.utils.data_input import InputData
from pymfm.utils.control import control
from pymfm.utils import data_output


def open_json(filename):
    with open(filename) as data_file:
        data = json.load(data_file)
    return data


def main():
    fpath = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(fpath, "inputs/rule_based_near_real_time.json")
    data = open_json(filepath)
    input_data = InputData(**data)
    output_df, status = control(input_data)
    print(output_df)


if __name__ == "__main__":
    main()
