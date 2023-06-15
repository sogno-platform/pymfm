import json
from datetime import datetime, timedelta
import dateutil.parser
import pandas as pd
import matplotlib.pyplot as plt
import itertools
import numpy as np


# read from json input file


def read_from_json(measurements, flex_specs_input):
    input_dict = dict.fromkeys(
        ["Time", "Dynamic_Load_kW", "PV_data", "Preq_kW", "delta_T", "Cal_iONS_kW"]
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
    input_dict["Time"] = measurements["Time"]
    input_dict["Cal_iONS_kW"] = measurements["Cal_iONS_kW"]
    input_dict["Ptcb_Init_kW"] = measurements["Ptcb_Init_kW"]
    input_dict["Preq_kW"] = measurements["Preq_kW"]
    input_dict["delta_T"] = measurements["delta_T"]
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
