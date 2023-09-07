import json
import os
from pymfm.src.control.utils.data_input import InputData
from pymfm.utils.mode_logic_handler import mode_logic_handler
from pymfm.utils import data_output





def open_json(filename):
    with open(filename) as data_file:
        data = json.load(data_file)
    return data


def main():
    filepath = os.path.join(fpath, "inputs/optimization_based_scheduling.json")
    data = open_json(filepath)
    input_data = InputData(**data)
    output_df, status = mode_logic_handler(input_data)
    print(output_df)

    data_output.visualize_and_save_plots(
        output_df, output_directory="results/"
    )
    data_output.produce_json_output(
        output_df, output_path="results/output.json"
    )
    data_output.produce_excel_output(
        output_df, output_path="results/output.xlsx"
    )


if __name__ == "__main__":
    main()
