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

import logging
from typing import List, Optional, Tuple, Union

import pandas as pd

from pymfm.control.algorithms.base import Algorithm, AlgorithmResult
from pymfm.control.schemas.input import Bulk

log = logging.getLogger(__name__)


def clamp_and_delta(
    value: float,
    upper: Union[float, List[float]] = 0,
    lower: Union[float, List[float]] = 0,
) -> Tuple[float, float]:
    """Clamps value between upper and lower and return it with the difference such that
    lower <= return[0] <= upper and return[0]+return[1]=value
    """
    upper_cap = min(value, *upper) if isinstance(upper, list) else min(value, upper)
    actual = max(upper_cap, *lower) if isinstance(lower, list) else max(upper_cap, lower)
    return actual, value - actual


def _rule_based_step(
    raw_demand_kw: float,
    battery_specs: pd.Series,
    delta_T_h: float,
) -> pd.Series:
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
    met_demand_kw, excess_demand = clamp_and_delta(
        raw_demand_kw,
        upper=[battery_specs.P_dis_max_kW[0], -P_min_soc[0]],
        lower=[-battery_specs.P_ch_max_kW[0], -P_max_soc[0]],
    )
    assert abs(met_demand_kw) <= abs(raw_demand_kw)

    # TODO confirm that setpoints for battery are from battery perspective not network perspective
    # discharging
    if raw_demand_kw > 0:
        P_bat_kw = met_demand_kw / battery_specs.dis_efficiency
    # charging
    else:
        P_bat_kw = met_demand_kw * battery_specs.ch_efficiency

    new_soc = battery_specs.initial_SoC - (P_bat_kw * delta_T_h / battery_specs.bat_capacity_kWh)

    output_ds = pd.Series(index=["SoC_bat", "P_net_after_kW", "P_bat_kW"], dtype=float)
    output_ds["SoC_bat"] = new_soc
    output_ds["P_net_after_kW"] = excess_demand
    output_ds["P_bat_kW"] = -P_bat_kw  # charging: positiv, discharging: negativ
    return output_ds


def _run_rule_based(
    df: pd.DataFrame,
    battery_specs: pd.DataFrame,
    delta_T_h: float,
) -> pd.DataFrame:
    # battery_specs = data.battery_specs
    specs = battery_specs
    if isinstance(specs, list):
        if len(specs) == 1:
            specs = specs[0]
        else:
            raise RuntimeError("Rule based control cannot deal with multiple flex nodes.")

    rows = []
    # XXX think about moving this to the RB algorithm to be analog to optimization based
    for _ts, row in df.iterrows():
        step = _rule_based_step(row.P_required_kW - row.P_available_kW, specs, delta_T_h)
        rows.append(step)
        specs.initial_SoC = step.SoC_bat

    output_df = pd.DataFrame(rows, index=df.index)
    output_df.index.name = "timestamp"  # XXX should be one name everywhere instead of sometimes "time" and sometimes "timestamp"

    battery_id = specs.index[0] if specs.index[0] is not None else "bat"
    output_df.rename(
        columns={
            "P_bat_kW": ("P_bat_kW", battery_id),
            "SoC_bat": ("SoC_bat", battery_id),
        },
        inplace=True,
    )
    return output_df


class RuleBasedAlgorithm(Algorithm):
    """Rule-based battery control algorithm."""

    def run(
        self,
        timeseries: pd.DataFrame,
        df_battery: pd.DataFrame,
        delta_T_h: float,
        day_end=None,
        bulk_data: Optional[Bulk] = None,
        pv_curtailment: bool = False,
    ) -> AlgorithmResult:
        output_df = _run_rule_based(timeseries, df_battery, delta_T_h)

        net_after = output_df.get("P_net_after_kW", pd.Series(dtype=float))
        peak_exp = float(-net_after.min()) if net_after.min() < 0 else 0.0
        peak_imp = float(net_after.max()) if net_after.max() > 0 else 0.0

        return AlgorithmResult(output_df=output_df, peak_imp=peak_imp, peak_exp=peak_exp)
