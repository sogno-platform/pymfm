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

import datetime
import logging
from typing import Tuple

import pandas as pd
from pyomo.opt import SolverStatus, TerminationCondition

from pymfm.control.algorithms.base import Algorithm, AlgorithmResult
from pymfm.control.algorithms.optimization import run_scheduling
from pymfm.control.algorithms.rule_based import RuleBasedAlgorithm
from pymfm.control.schemas.input import Bulk, ControlLogic, InputData
from pymfm.control.schemas.output import BalancerOutput, validate_timestep
from pymfm.control.utils.common import extract_df, get_freq

log = logging.getLogger(__name__)


# Algorithm factory

def build_algorithm(control_logic: ControlLogic) -> Algorithm:
    """Return the Algorithm implementation for the given control logic."""
    if control_logic == ControlLogic.RULE_BASED:
        return RuleBasedAlgorithm()
    if control_logic == ControlLogic.OPTIMIZATION_BASED:
        # Import here to avoid circular imports; OptimisationAlgorithm is thin
        from pymfm.control.algorithms._optimization_algorithm import OptimisationAlgorithm
        return OptimisationAlgorithm()
    raise ValueError(f"Unknown control logic: {control_logic!r}")


# Input conversion

def prep_data(data: InputData) -> Tuple[pd.DataFrame, pd.DataFrame, float]:
    """Convert an InputData object into DataFrames for algorithm consumption.

    Returns
    -------
    df : pd.DataFrame
        Forecast timeseries with optional power bounds, freq-indexed.
    df_battery_specs : pd.DataFrame
        Battery specs indexed by battery id.
    delta_T_h : float
        Timestep in hours.
    """
    if data.generation_and_load is None:
        raise ValueError("generation_and_load must be provided.")

    df_power = extract_df(data.generation_and_load, attr="values", index_col="timestamp")
    df_limits = extract_df(data, attr="P_net_after_kW_limitation", index_col="timestamp")
    df_battery_specs = extract_df(data, attr="battery_specs", index_col="id")

    delta_T_h = data.generation_and_load.delta_T_h
    if delta_T_h is None:
        delta_T_h = get_freq(df_power, df_limits).nanos * 1e-9 / 3600

    df = df_power.asfreq(f"{delta_T_h}h")
    if df_limits is not None:
        df = df.join(df_limits)

    return df, df_battery_specs, delta_T_h


# Algorithm runner — converts AlgorithmResult → BalancerOutput

def run_algorithm(
    algorithm: Algorithm,
    timeseries: pd.DataFrame,
    df_battery_specs: pd.DataFrame,
    delta_T_h: float,
    day_end: datetime.datetime | None,
    bulk: Bulk | None,
    pv_curtailment: bool,
    job_id: str,
) -> Tuple[BalancerOutput, Tuple]:
    """Run *algorithm* and package the result into a BalancerOutput.

    Returns
    -------
    (BalancerOutput, (status_str, details))
    """
    algo_result: AlgorithmResult = algorithm.run(
        timeseries=timeseries,
        df_battery=df_battery_specs,
        delta_T_h=delta_T_h,
        day_end=day_end,
        bulk_data=bulk,
        pv_curtailment=pv_curtailment,
    )

    output_df = algo_result.output_df

    # Always attach P_net_before_kW
    output_df = output_df.copy()
    output_df["P_net_before_kW"] = timeseries.P_required_kW - timeseries.P_available_kW

    output_ts = [
        validate_timestep(row.to_dict())
        for _time, row in output_df.reset_index().iterrows()
    ]

    balancer_output = BalancerOutput(
        id=job_id,
        peak_imp=algo_result.peak_imp,
        peak_exp=algo_result.peak_exp,
        schedule=output_ts,
    )

    solver_ok = algo_result.solver_status[1] == TerminationCondition.optimal
    status_tuple = ("ok", "optimal") if solver_ok else ("failed", str(algo_result.solver_status))

    return balancer_output, status_tuple
