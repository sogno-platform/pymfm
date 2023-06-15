import json

from forecast_utils.data_prep import Prepare
from forecast_utils.data_output import Forecast_output
from forecast_utils.forecasts import Forecast
import argparse


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-level', '--level', action="store", help='Provides forecast level')
    args = parser.parse_args()
    print('++++++++++++++++++')
    print(args)
    print('#####################')
    forecast_level = int(args.level)

    forecast_input_file = 'Forecast_POST_2021_07_05_V1.json'
    with open(forecast_input_file) as data_file:
        data = json.load(data_file)



    forecast_df, time_start, pv_metadata, load_metadata, time_end, forecast_level = \
        Prepare().read_forecast_input(data, forecast_level)
    forecast_data = Forecast().forecast(forecast_df, time_start, time_end, pv_metadata, load_metadata, forecast_level)
    forecast_results = Forecast_output().write_forecast_output(forecast_data.copy(), pv_metadata,
                                                               load_metadata, forecast_level)
    print(forecast_results)


if __name__ == "__main__":
    main()
