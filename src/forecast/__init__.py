import azure.functions as func
from forecast_utils.data_prep import Prepare
from forecast_utils.data_output import Forecast_output
from forecast_utils.forecasts import Forecast


def main(req: func.HttpRequest) -> func.HttpResponse:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-level", "--level", action="store", help="Provides forecast level"
    )
    args = parser.parse_args()
    forecast_level = int(args.level)
    data = req.get_json()
    (
        forecast_df,
        time_start,
        pv_metadata,
        load_metadata,
        time_end,
        forecast_level,
    ) = Prepare().read_forecast_input(data, forecast_level)
    forecast_data = Forecast().forecast(
        forecast_df, time_start, time_end, pv_metadata, load_metadata, forecast_level
    )
    forecast_results = Forecast_output().write_forecast_output(
        forecast_data.copy(), pv_metadata, load_metadata, forecast_level
    )
    return func.HttpResponse(body=forecast_results, mimetype="application/json")
