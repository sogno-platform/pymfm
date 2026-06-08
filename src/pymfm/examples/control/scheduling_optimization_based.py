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

from pymfm.control.schemas.input import InputData
from pymfm.control.utils.data_prep import build_algorithm, prep_data, run_algorithm
from pymfm.control.utils.visualization import visualize_and_save_plots


def main():
    """
    Example usage of scheduling optimization based control.

    This function reads input data from "inputs/scheduling_optimization_based.json" JSON file,
    processes it using the control algorithm, prepares output data,
    saves output JSON files under "outputs/",
    and saves visualized data through plots under "outputs/" as SVG files.

    :return: None
    """
    # Get the current directory of the script
    fpath = os.path.dirname(os.path.abspath(__file__))

    # Construct the file path for the input JSON file
    filepath = os.path.join(fpath, "inputs/scheduling_optimization_based.json")

    # Open and load the JSON data from the file
    with open(filepath) as f:
        input_data = InputData(**json.load(f))

    df, df_battery, delta_T_h = prep_data(input_data)
    sliced_df = df[input_data.control_start : input_data.control_end]

    # Execute the control logic handler to process the input data
    algorithm = build_algorithm(input_data.control_logic)
    algo_result = algorithm.run(
        sliced_df, df_battery, delta_T_h,
        day_end=input_data.day_end,
        bulk_data=input_data.bulk,
        pv_curtailment=input_data.generation_and_load.pv_curtailment,
    )

    result, (status, details) = run_algorithm(
        algorithm=algorithm,
        timeseries=sliced_df,
        df_battery_specs=df_battery,
        delta_T_h=delta_T_h,
        day_end=input_data.day_end,
        bulk=input_data.bulk,
        pv_curtailment=input_data.generation_and_load.pv_curtailment,
        job_id=input_data.id,
    )

    # Prepare and save control output data as JSON files
    os.makedirs("outputs", exist_ok=True)
    out_json = os.path.join("outputs", f"{input_data.id}_output.json")
    with open(out_json, "w") as f:
        f.write(result.model_dump_json(indent=2))
    print(f"Result saved to {os.path.abspath(out_json)}")

    # Visualize and save control output data as SVG plots
    visualize_and_save_plots(
        control_logic=input_data.control_logic,
        operation_mode=input_data.operation_mode,
        job_id=input_data.id,
        dataframe=algo_result.output_df,
        output_directory="outputs/",
    )


if __name__ == "__main__":
    main()
