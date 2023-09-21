import os
from pymfm.control.utils.data_input import InputData, open_json
from pymfm.control.utils.mode_logic_handler import mode_logic_handler
from pymfm.control.utils import data_output


def main():
    fpath = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(fpath, "inputs/scheduling_optimization_based.json")
    data = open_json(filepath)
    input_data = InputData(**data)
    mode_logic, output_df, status = mode_logic_handler(input_data)

    data_output.prepare_json(mode_logic, output_df, output_directory="outputs/")

    data_output.visualize_and_save_plots(
        mode_logic, output_df, output_directory="outputs/"
    )


if __name__ == "__main__":
    main()
