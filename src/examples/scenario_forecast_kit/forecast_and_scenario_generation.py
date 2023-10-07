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


from pymfm.scenario_forecast_kit.forecast_generation import generate_forecast
from pymfm.scenario_forecast_kit.scenario_generation import generate_scenario


def main():
    """
    Example usage of scenario generation.
    This function generates a forecast based on input data and then generates a scenario
    by merging the generated forecast with additional scenario data.

    :return: None
    """

    forecast_input_folder = "inputs/forecast"
    forecast_output_folder = "outputs/forecast"
    time_resolution = 10  # in minutes

    forecast_data = generate_forecast(
        forecast_input_folder, forecast_output_folder, time_resolution
    )

    forecast_input_file = "outputs/forecast/forecast_2021-04-01.json"
    scenario_input_file = "inputs/scenario/scenario_src_2021-04-01.json"
    scenario_output_file = "outputs/scenario/test.json"

    generate_scenario(forecast_input_file, scenario_input_file, scenario_output_file)


if __name__ == "__main__":
    main()
