import json


class Forecast_output:
    def write_forecast_output(
        self, forecast_df, pv_metadata, load_metadata, forecast_level
    ):
        data = {}
        Pteiforecast = {}
        units = {}
        metadata = {}
        Pteiforecast["version"] = "1.0"
        forecast_df["NumericValue"] = forecast_df["Cal_iONS_kW"]
        forecast_df = forecast_df.reset_index()
        if forecast_level == 1:
            forecast_data = forecast_df[["Timestamp", "NumericValue"]].to_json(
                orient="records", date_format="iso", index=True
            )
            units["time"] = "ISO8601"
            units["Pteipower"] = "kW"
            metadata["PV_slope"] = pv_metadata["slope"]
            metadata["PV_facing"] = pv_metadata["facing"]
            metadata["PV_kwp"] = pv_metadata["kwp"]
            metadata["Load_avgconsumption"] = load_metadata["avgconsumption"]
            metadata["Load_households"] = load_metadata["households"]
            Pteiforecast["metadata"] = metadata
            Pteiforecast["units"] = units

            data["Pteiforecast"] = Pteiforecast
            Pteiforecast["values"] = json.loads(forecast_data)
        return json.dumps(data)

    """"
        with open('Forecast.json', 'w') as outfile:
            json.dump(data, outfile, sort_keys=False, indent=4)
    """
