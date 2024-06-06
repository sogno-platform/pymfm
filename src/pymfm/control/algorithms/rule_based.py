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
# substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
# BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


from typing import List, Tuple, Union

import pandas as pd

from pymfm.control.utils.data_input import BatterySpecs


def clamp_and_delta(
    value: float, upper: Union[float, List[float]] = 0, lower: Union[float, List[float]] = 0
) -> Tuple[float, float]:
    """Clamps value between upper and lower and return it with the difference such that
    lower <= return[0] <= upper and return[0]+return[1]=value
    """
    if isinstance(upper, list):
        upper_cap = min(value, *upper)
    else:
        upper_cap = min(value, upper)
    if isinstance(lower, list):
        acutal = max(upper_cap, *lower)
    else:
        acutal = max(upper_cap, lower)
    return (acutal, value - acutal)


def combined_rule_based(raw_demand_kw: float, battery_specs: BatterySpecs, delta_T_h: float):
    output_ds = pd.Series(
        index=[
            "SoC_bat",
            "P_net_after_kW",
            "P_bat_kW",
        ],
        dtype=float,
    )
    # P value that reaches max state of charge in delta_T_h, from network perspective
    # / ch_efficency as the net can but in more charge due to loss from efficency
    P_max_soc = (
        (battery_specs.max_SoC - battery_specs.initial_SoC)
        * battery_specs.bat_capacity_kWh
        / (delta_T_h * battery_specs.ch_efficiency)
    )
    # P value that reaches min state of charge in delta_T_h, from network perspective
    # is negative which corresponds to discharging correctly
    # * ch_efficency as the battery loses more charge than it provides to the net
    P_min_soc = (
        (battery_specs.min_SoC - battery_specs.initial_SoC)
        * battery_specs.bat_capacity_kWh
        * battery_specs.dis_efficiency
        / delta_T_h
    )

    # limit power delivered by max charging and discharging and max available charge/capacity
    # TODO confirm that P_max are power received on network side not on battery side.
    met_demand_kw, access_demand = clamp_and_delta(
        raw_demand_kw, upper=[battery_specs.P_dis_max_kW, -P_min_soc], lower=[-battery_specs.P_ch_max_kW, -P_max_soc]
    )
    assert abs(met_demand_kw) > abs(raw_demand_kw)

    # TODO confirm that setpoints for battery are from battery perspective not network perspective
    # discharging
    if raw_demand_kw > 0:
        P_bat_kw = met_demand_kw / battery_specs.dis_efficiency
    # charging
    else:
        P_bat_kw = met_demand_kw * battery_specs.ch_efficiency

    output_ds.SoC_bat = battery_specs.initial_SoC - (P_bat_kw * delta_T_h / battery_specs.bat_capacity_kWh)
    output_ds.P_net_after_kW = access_demand
    output_ds.P_bat_kW = -P_bat_kw  # charging: positiv, discharging: negativ
    return output_ds
