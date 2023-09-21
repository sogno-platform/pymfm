from pymfm.scenario_forecast_kit.forecast_generation import generate_forecast
from pymfm.scenario_forecast_kit.scenario_generation import generate_scenario


def main():
    """
    The main function of the program, illustrating an example usage scenario.
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
