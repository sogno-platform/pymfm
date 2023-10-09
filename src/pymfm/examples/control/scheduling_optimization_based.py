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


import os
from pymfm.control.utils.data_input import InputData, open_json
from pymfm.control.utils.mode_logic_handler import mode_logic_handler
from pymfm.control.utils import data_output


def main():
    """
    Example usage of scheduling optimization based control.

    This function reads input data from "inputs/scheduling_optimization_based.json" JSON file, 
    processes it using the `mode_logic_handler`, prepares output data, 
    saves output JSON files under "outputs/", 
    and saves visualized data through plots under "outputs/" as SVG files.

    :return: None
    """
    # Get the current directory of the script
    fpath = os.path.dirname(os.path.abspath(__file__))

    # Construct the file path for the input JSON file
    filepath = os.path.join(fpath, "inputs/scheduling_optimization_based.json")

    # Open and load the JSON data from the file
    data = open_json(filepath)

    # Create an InputData object from the loaded data
    input_data = InputData(**data)

    # Execute the control logic handler to process the input data
    mode_logic, output_df, status = mode_logic_handler(input_data)

    # Prepare and save control output data as JSON files
    data_output.prepare_json(mode_logic, output_df, output_directory="outputs/")

    # Visualize and save control output data as SVG plots
    data_output.visualize_and_save_plots(
        mode_logic, output_df, output_directory="outputs/"
    )


if __name__ == "__main__":
    main()
