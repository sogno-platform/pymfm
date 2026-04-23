# The pymfm framework
#
# Scheduling orchestration — calls model builder, solver, and post-processing.
# This is the single public entry point for optimisation-based control.

import logging
from datetime import datetime

import pandas as pd
from pyomo.core import Var
from pyomo.opt import SolverStatus, TerminationCondition

from pymfm.control.exceptions import InfeasibleError
from pymfm.control.schemas.input import Bulk
from pymfm.control.algorithms.optimization.model import build_model
from pymfm.control.algorithms.optimization.solver import get_solver

log = logging.getLogger(__name__)


def run_scheduling(
    timeseries: pd.DataFrame,
    df_battery: pd.DataFrame,
    day_end: datetime | None,
    bulk_data: Bulk | None,
    pv_curtailment: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, tuple[SolverStatus, TerminationCondition]]:
    """
    The scheduling optimization function which acts upon the load and generation forecast data considering
    battery specifications, optimization horizon, and power boundaries.
    Depending on the input data, bulk delivery/reception and PV curtailment can also be satisfied.


    Parameters
    ----------
    timeseries : pd.DataFrame
        load and generation forecast time series of float type.
    df_battery : pd.DataFrame
        battery specifications of float and string types.
    day_end : datetime
        user-defined end of the day (datetime) till which household batteries should reach
        maximum SoC. By default, its value is set to then sun-set time.
    bulk_data : Bulk
        Class related to the bulk delivery/reception of energy from batteries including bulk_start
        and _end datetime and the bulk_energy_kWh float.
    pv_curtailment : bool
        If true, PV generation can be curtailed.

    Returns
    -------
    output_batteries : pd.DataFrame
        Per-battery results (MultiIndex columns: variable × battery_id).
    output_system : pd.DataFrame
        System-level results (P_PV_kW, P_net_after_kW, peak_imp/peak_exp).
    output_static : pd.Series
        Scalar results (peak_imp, peak_exp).
    solver_status : tuple[SolverStatus, TerminationCondition]
    """
    solver = get_solver()
    model = build_model(timeseries, df_battery, day_end, bulk_data, pv_curtailment)

    result = solver.solve(model)
    status = result.solver

    termination = status.termination_condition
    if termination in (TerminationCondition.infeasible, TerminationCondition.infeasibleOrUnbounded):
        raise InfeasibleError("Optimisation problem has no feasible solution.")

    log.info("Solver finished: status=%s termination=%s", status.status, termination)

    return _extract_results(model, df_battery)


def _extract_results(
    model, df_battery: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, tuple]:
    """Extract variable values from the solved model into DataFrames."""
    output_system = pd.DataFrame(index=model.T).rename_axis("time")
    output_static = pd.Series(dtype=float)
    battery_frames = []

    for name, var in model.component_map(ctype=Var).items():
        series = pd.Series(var.extract_values(), name=name)
        if series.empty:
            continue
        first_idx = series.index[0]
        if isinstance(first_idx, tuple):
            unstacked = series.unstack(level=0)
            unstacked.columns = pd.MultiIndex.from_tuples([(name, col) for col in unstacked.columns])
            battery_frames.append(unstacked)
        elif first_idx is None:
            output_static[name] = var.get_values()[None]
        else:
            output_system = output_system.join(series)

    if battery_frames:
        output_batteries = pd.concat(battery_frames, axis=1)
        output_batteries.index.name = "time"
        # SoC_bat is indexed over T_SoC_bat (N+1 points) while power variables
        # use T (N points). Trim to the optimization horizon so the extra final
        # SoC state does not produce a row with None power values.
        output_batteries = output_batteries.reindex(list(model.T))
    else:
        output_batteries = pd.DataFrame(index=model.T).rename_axis("time")

    if not output_batteries.empty:
        # Apply efficiency corrections to reported battery power
        output_batteries.P_ch_bat_kW = output_batteries.P_ch_bat_kW * df_battery.ch_efficiency
        output_batteries.P_dis_bat_kW = output_batteries.P_dis_bat_kW / df_battery.dis_efficiency

    return (
        output_batteries,
        output_system,
        output_static,
        (SolverStatus.ok, TerminationCondition.optimal),
    )
