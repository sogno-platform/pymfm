import pandas as pd
from datetime import datetime, timedelta
import os
from os import path


class Forecast:
    # load scaling factor calculation
    def load_scaling_factor(self, no_of_households, avg_year_load):
        sum_energy = 1000
        load_scaling_factor = (no_of_households * avg_year_load) / sum_energy
        return load_scaling_factor

    def forecast_calc(self, day_df, NumCust, Eavg, Nscale=1):
        scaling_factor = self.load_scaling_factor(NumCust, Eavg)
        day_df["Dynamic_Load_kW"] = (day_df["Static_Load_W"] * scaling_factor) / 1000
        day_df["Cal_iONS_kW"] = day_df["Dynamic_Load_kW"] - (day_df["PV_data"] * Nscale)
        day_df = day_df.interpolate(method="linear")
        return day_df

    def gute1_forecast(
        self,
        forecast_df,
        time_start,
        time_end,
        pv_metadata,
        load_metadata,
        forecast_level,
        Nscale=1,
    ):
        forecast_start = time_start
        forecast_end = time_end
        day_time_start = forecast_start
        day_time_end = forecast_start + timedelta(hours=24)
        forecast_data = pd.DataFrame()
        while day_time_start < forecast_end:
            day_df = forecast_df.copy()
            mask = (day_df.Timestamp >= day_time_start) & (
                day_df.Timestamp < day_time_end
            )
            day_df = day_df.loc[mask]
            day_forecast_data = self.forecast_calc(
                day_df,
                load_metadata["households"],
                load_metadata["avgconsumption"],
                Nscale,
            )
            forecast_data = pd.concat(
                [forecast_data, day_forecast_data], ignore_index=False
            )
            day_time_start = day_time_end
            day_time_end = day_time_start + timedelta(hours=24)
        forecast_data = forecast_data.set_index("Timestamp")
        return forecast_data

    def forecast(
        self,
        forecast_df,
        time_start,
        time_end,
        pv_metadata,
        load_metadata,
        forecast_level,
    ):
        if forecast_level == 1:
            forecast_data = self.gute1_forecast(
                forecast_df,
                time_start,
                time_end,
                pv_metadata,
                load_metadata,
                forecast_level,
            )
            return forecast_data
