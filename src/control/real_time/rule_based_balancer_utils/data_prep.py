import json
from datetime import datetime, timedelta
import dateutil.parser
import pandas as pd
import matplotlib.pyplot as plt
import itertools
import numpy as np


# read from json input file


def read_from_json(measurements_request, flex_specs_input):
    input_dict = dict.fromkeys(
        ["timestamp", "Dynamic_Load_kW", "PV_data", "Preq_kW", "delta_T", "Pnet_meas_kW"]
    )
    flex_specs = dict.fromkeys(
        [
            "initial_SOF",
            "min_SOF",
            "max_SOF",
            "Pf_dis_kW",
            "Pf_ch_kW",
            "Agg_cap_flex",
            "initial_SOF_Forecast",
            "initial_SOF_measured",
        ]
    )
    input_dict["timestamp"] = measurements_request["timestamp"]
    input_dict["Pnet_meas_kW"] = measurements_request["Pnet_meas_kW"]
    input_dict["Pbat_init_kW"] = measurements_request["Pbat_init_kW"]
    input_dict["Preq_kW"] = measurements_request["Preq_kW"]
    input_dict["delta_T"] = measurements_request["delta_T"]
    flex_specs["Agg_cap_flex"] = flex_specs_input["Agg_cap_flex"]
    flex_specs["Pf_dis_kW"] = flex_specs_input["Pf_dis_kW"]
    flex_specs["Pf_ch_kW"] = flex_specs_input["Pf_ch_kW"]
    # percentage to kWh conversion
    flex_specs["initial_SOF"] = float(
        (flex_specs_input["initial_SOF"] / 100) * flex_specs["Agg_cap_flex"]
    )
    flex_specs["min_SOF"] = float(
        (flex_specs_input["min_SOF"] / 100) * flex_specs["Agg_cap_flex"]
    )
    flex_specs["max_SOF"] = float(
        (flex_specs_input["max_SOF"] / 100) * flex_specs["Agg_cap_flex"]
    )

    return input_dict, flex_specs
