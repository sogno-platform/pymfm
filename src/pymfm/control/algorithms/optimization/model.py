# The pymfm framework
#
# Pyomo model construction.
# Assembles variables, parameters, and constraints from prepared DataFrames.
# Does not touch the solver or post-processing.

import pandas as pd
import pyomo.kernel as pmo
from pyomo.core import (
    ConcreteModel,
    Constraint,
    NonNegativeReals,
    Objective,
    Var,
    minimize,
)

from pymfm.config import settings
from pymfm.control.schemas.input import Bulk
from pymfm.control.algorithms.optimization.constraints import (
    bat_charging,
    bat_final_SoC,
    bat_init_SoC,
    bat_max_SoC,
    bat_max_ch_power,
    bat_max_dis_power,
    bat_min_SoC,
    bulk_energy,
    ch_dis_binary,
    deficit_case_1,
    deficit_case_2,
    hbes_avoid_diss,
    imp_exp_binary,
    obj_rule,
    P_net_after_kW_lower_bound,
    P_net_after_kW_upper_bound,
    penalty_for_exp,
    penalty_for_imp,
    power_balance,
    pv_curtailment_constr,
    surplus_case_1,
    surplus_case_2,
)


def build_model(
    timeseries: pd.DataFrame,
    df_battery: pd.DataFrame,
    day_end,
    bulk_data: Bulk | None,
    pv_curtailment: bool,
) -> ConcreteModel:
    """Build and return a fully-constrained Pyomo ConcreteModel.

    Parameters
    ----------
    timeseries:
        DataFrame indexed by timestamp with columns ``P_required_kW``,
        ``P_available_kW``, and optionally ``upper_bound`` / ``lower_bound``.
    df_battery:
        DataFrame indexed by battery id with battery spec columns.
    day_end:
        Datetime at which HBES batteries must reach max SoC (may be None).
    bulk_data:
        Optional bulk energy specification.
    pv_curtailment:
        Whether PV curtailment is permitted.
    """
    load = timeseries.P_required_kW
    generation = timeseries.P_available_kW
    start_time = load.index[0]
    end_time = load.index[-1]
    delta_T = pd.to_timedelta(load.index.freq)

    opt_horizon = pd.date_range(start_time, end_time + delta_T, freq=delta_T, inclusive="left")
    soc_horizon = pd.date_range(start_time, end_time + delta_T, freq=delta_T, inclusive="both")

    model = ConcreteModel()

    # ---- Index sets --------------------------------------------------------
    model.N = list(df_battery.index)
    model.T = tuple(opt_horizon)
    model.T_SoC_bat = tuple(soc_horizon)
    if bulk_data is not None:
        bulk_horizon = pd.date_range(bulk_data.bulk_start, bulk_data.bulk_end, freq=delta_T, inclusive="both")
        model.T_bulk = tuple(bulk_horizon)

    # ---- Scalar parameters -------------------------------------------------
    model.dT = delta_T
    model.start_time = start_time
    model.end_time = end_time
    model.day_end = day_end
    model.pv_curtailment = pv_curtailment if pv_curtailment is not None else False

    # ---- Forecast parameters -----------------------------------------------
    model.P_net_before_kW = load[opt_horizon] - generation[opt_horizon]
    model.P_required_kW = load[opt_horizon]
    model.P_PV_limit_kW = generation[opt_horizon]

    if "upper_bound" in timeseries:
        model.upper_bound_kW = timeseries.upper_bound
    if "lower_bound" in timeseries:
        model.lower_bound_kW = timeseries.lower_bound

    # ---- Battery parameters ------------------------------------------------
    model.bat_type = df_battery.bat_type
    model.min_SoC_bat = df_battery.min_SoC
    model.max_SoC_bat = df_battery.max_SoC
    model.ini_SoC_bat = df_battery.initial_SoC
    model.final_SoC_bat = df_battery.final_SoC
    model.bat_capacity_kWs = df_battery.bat_capacity_kWh * settings.seconds_per_hour
    model.P_ch_bat_max_kW = df_battery.P_ch_max_kW
    model.P_dis_bat_max_kW = df_battery.P_dis_max_kW
    model.ch_eff_bat = df_battery.ch_efficiency
    model.dis_eff_bat = df_battery.dis_efficiency

    if bulk_data is not None:
        model.bulk_energy_kWs = pd.Series([bulk_data.bulk_energy_kWh]) * settings.seconds_per_hour

    # ---- Decision variables ------------------------------------------------
    model.P_PV_kW = Var(model.T, within=NonNegativeReals)
    model.SoC_bat = Var(model.N, model.T_SoC_bat, within=NonNegativeReals)
    model.P_ch_bat_kW = Var(model.N, model.T, within=NonNegativeReals)
    model.P_dis_bat_kW = Var(model.N, model.T, within=NonNegativeReals)
    model.P_exp_kW = Var(model.T, within=NonNegativeReals)
    model.P_imp_kW = Var(model.T, within=NonNegativeReals)
    model.peak_imp = Var(within=NonNegativeReals)
    model.peak_exp = Var(within=NonNegativeReals)
    # Binaries
    model.is_ch = Var(model.N, model.T, within=pmo.Binary)
    model.is_dis = Var(model.N, model.T, within=pmo.Binary)
    model.is_imp = Var(model.T, within=pmo.Binary)
    model.is_exp = Var(model.T, within=pmo.Binary)

    # ---- Constraints -------------------------------------------------------
    model.power_balance = Constraint(model.T, rule=power_balance)
    model.bat_charging = Constraint(model.N, model.T, rule=bat_charging)
    model.bat_init_SoC = Constraint(model.N, rule=bat_init_SoC)
    model.bat_final_SoC = Constraint(model.N, rule=bat_final_SoC)
    model.bat_max_ch_power = Constraint(model.N, model.T, rule=bat_max_ch_power)
    model.bat_max_dis_power = Constraint(model.N, model.T, rule=bat_max_dis_power)
    model.bat_min_SoC = Constraint(model.N, model.T_SoC_bat, rule=bat_min_SoC)
    model.bat_max_SoC = Constraint(model.N, model.T_SoC_bat, rule=bat_max_SoC)
    model.ch_dis_binary = Constraint(model.N, model.T, rule=ch_dis_binary)
    model.imp_exp_binary = Constraint(model.T, rule=imp_exp_binary)
    model.penalty_for_imp = Constraint(model.T, rule=penalty_for_imp)
    model.penalty_for_exp = Constraint(model.T, rule=penalty_for_exp)
    model.deficit_case_1 = Constraint(model.T, rule=deficit_case_1)
    model.deficit_case_2 = Constraint(model.N, model.T, rule=deficit_case_2)
    model.surplus_case_1 = Constraint(model.T, rule=surplus_case_1)
    model.surplus_case_2 = Constraint(model.T, rule=surplus_case_2)
    model.hbes_avoid_diss = Constraint(model.N, model.T, rule=hbes_avoid_diss)
    model.pv_curtailment_constr = Constraint(model.T, rule=pv_curtailment_constr)

    if bulk_data is not None:
        model.bulk_energy = Constraint(rule=bulk_energy)
    if "upper_bound" in timeseries:
        model.P_net_after_kW_upper_bound = Constraint(model.T, rule=P_net_after_kW_upper_bound)
    if "lower_bound" in timeseries:
        model.P_net_after_kW_lower_bound = Constraint(model.T, rule=P_net_after_kW_lower_bound)

    # ---- Objective ---------------------------------------------------------
    model.obj = Objective(rule=obj_rule, sense=minimize)

    return model
