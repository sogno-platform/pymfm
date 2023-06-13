import pandas as pd
from datetime import datetime, timedelta
import json
import os
import dateutil.parser

class Prepare:

    def read_forecast_input(self, data, forecast_level, interpolate_pv_first = True):

        pv_data = pd.DataFrame()
        h_data = pd.DataFrame()
        pv_metadata = data['pvpro_backwards']['metadata']
        load_metadata = data['household_dyn']['metadata']
        for pv_item in data['pvpro_backwards']['values']:
            pv_data = pv_data.append(
                {'Timestamp': pv_item['Timestamp'], 'PV_data': pv_item['NumericValue']},
                ignore_index=True)
        pv_data['Timestamp'] = pd.to_datetime(pd.to_datetime(pv_data['Timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S'))
        pv_data = pv_data.set_index('Timestamp')
        if interpolate_pv_first:
            pv_data = pv_data.resample("0.25H").asfreq()
        pv_data = pv_data.interpolate(method='linear', limit_direction='forward')

        for h_item in data['household_dyn']['values']:
            h_data = h_data.append({'Timestamp': h_item['Timestamp'], 'Static_Load_W': h_item['NumericValue']},
                                   ignore_index=True)
            h_data['Timestamp'] = pd.to_datetime(
                pd.to_datetime(h_data['Timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S'))
        h_data = h_data.set_index('Timestamp')
        h_data = h_data.interpolate(method='linear', limit_direction='forward')

        # forecast data (combine pv and load)
        forecast_df = pd.merge(h_data, pv_data, left_index=True, right_index=True)
        if not interpolate_pv_first:
            forecast_df = forecast_df.resample("0.25H").asfreq()
            forecast_df = forecast_df.interpolate(method='linear', limit_direction='forward')
        forecast_df = forecast_df.interpolate(method='linear', limit_direction='forward')
        time_start = pd.to_datetime(dateutil.parser.parse(data['start_forecast']).strftime('%Y-%m-%d %H:%M:%S'))
        forecast_df = forecast_df.reset_index()
        time_end = pd.to_datetime(dateutil.parser.parse(data['end_forecast']).strftime('%Y-%m-%d %H:%M:%S'))


        return forecast_df, time_start, pv_metadata, load_metadata, time_end, forecast_level




