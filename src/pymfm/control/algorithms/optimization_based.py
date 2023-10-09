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


from datetime import datetime
from typing import Tuple
import pandas as pd
from typing import Tuple
from pyomo.environ import SolverFactory
from pyomo.core import *
from pymfm.control.utils.data_input import Bulk
from pyomo.opt import SolverStatus
import pyomo.kernel as pmo


# Constraints


def power_balance(model, t):
    """
    The power balance constraint.

    :param model: The pyomo model.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    return (
        model.P_load_kW[t]
        + sum(model.P_ch_bat_kW[n, t] for n in model.N)
        + model.P_exp_kW[t] * model.x_exp[t]
        == sum(model.P_dis_bat_kW[n, t] for n in model.N)
        + model.P_imp_kW[t] * model.x_imp[t]
        + model.P_PV_kW[t]
    )


def bat_charging(model, n, t):
    """
    The battery charging/discharging constraint.
    Updates the state of charge (SoC) of the battery for the next timestamp t accordingly.

    :param model: The pyomo model.
    :param n: The battery index.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    return model.SoC_bat[n, t + model.dT] == model.SoC_bat[n, t] + model.dT.seconds * (
        (model.P_ch_bat_kW[n, t] / model.ch_eff_bat[n]) / model.bat_capacity_kWs[n]
    ) - model.dT.seconds * (
        (model.P_dis_bat_kW[n, t] * model.dis_eff_bat[n]) / model.bat_capacity_kWs[n]
    )


def bat_init_SoC(model, n):
    """
    The battery initial state of charge constraint.
    Initializes the initial state of charges of the batteries to the first timestamp t.

    :param model: The pyomo model.
    :param n: The battery index.
    :return: The constraint itself.
    """
    return model.SoC_bat[n, model.start_time] == model.ini_SoC_bat[n]


def bat_max_ch_power(model, n, t):
    """
    The battery maximum charging power constraint.
    Limits the charging power of the batteries according to their maximum charging powers.

    :param model: The pyomo model.
    :param n: The battery index.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    return model.P_ch_bat_kW[n, t] <= float(model.P_ch_bat_max_kW[n]) * model.x_ch[n, t]


def bat_max_dis_power(model, n, t):
    """
    The battery maximum discharging power constraint.
    Limits the discharging power of the batteries according to their maximum discharging powers.

    :param model: The pyomo model.
    :param n: The battery index.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    return (
        model.P_dis_bat_kW[n, t] <= float(model.P_dis_bat_max_kW[n]) * model.x_dis[n, t]
    )


def bat_min_SoC(model, n, t):
    """
    The battery minimum state of charge (SoC) constraint.
    Limits the SoC of the batteries according to their minimum allowed SoCs.

    :param model: The pyomo model.
    :param n: The battery index.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    return float(model.min_SoC_bat[n]) <= model.SoC_bat[n, t]


def bat_max_SoC(model, n, t):
    """
    The battery maximum state of charge (SoC) constraint.
    Limits the SoC of the batteries according to their maximum allowed SoCs.

    :param model: The pyomo model.
    :param n: The battery index.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    return model.SoC_bat[n, t] <= model.max_SoC_bat[n]


def P_net_after_kW_lower_bound(model, t):
    """
    The P_net_after_kW lower bound constraint.
    If there is a lower bound for timestamp t, it limits the P_net_after_kW (= P_imp_kW - P_exp_kW) accordingly.

    :param model: The pyomo model.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    if model.with_lower_bound[t]:
        return (
            model.lower_bound_kW[t]
            <= model.P_imp_kW[t] * model.x_imp[t] - model.P_exp_kW[t] * model.x_exp[t]
        )
    else:
        return Constraint.Feasible


def P_net_after_kW_upper_bound(model, t):
    """
    The P_net_after_kW upper bound constraint.
    If there is a upper bound for timestamp t, it limits the P_net_after_kW (= P_imp_kW - P_exp_kW) accordingly.

    :param model: The pyomo model.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    if model.with_upper_bound[t]:
        return (
            model.P_imp_kW[t] * model.x_imp[t] - model.P_exp_kW[t] * model.x_exp[t]
            <= model.upper_bound_kW[t]
        )
    else:
        return Constraint.Feasible


def bat_final_SoC(model, n):
    """
    The battery final state of charge (SoC) constraint.
    Secures that batteries reach their final desired SoC at the very end timestamp t. If the battery type is
    household (hbes), then final desired SoC to be reached at the timestamp t, where daylight ends (day_end).

    :param model: The pyomo model.
    :param n: The battery index.
    :return: The constraint itself.
    """
    if model.final_SoC_bat[n] is not None:
        # Household battery should reach its maximum SoC at the end of the day (= either predefined or sunset)
        if model.bat_type[n] == "hbes":
            return model.SoC_bat[n, model.day_end] == model.max_SoC_bat[n]
        else:
            return model.SoC_bat[n, model.end_time] == model.final_SoC_bat[n]
    else:
        return Constraint.Feasible


def bulk_energy(model):
    # Delivery(+)/reception(-) of bulk amount of energy from the flexibility assets
    """
    The bulk energy constraint.

    :param model: The pyomo model.
    :return: The constraint itself.
    """
    return (
        sum(
            sum(
                (
                    model.P_dis_bat_kW[n, t] * model.dis_eff_bat[n]
                    - (model.P_ch_bat_kW[n, t]) / model.ch_eff_bat[n]
                )
                * model.dT.seconds
                for t in model.T_bulk
            )
            for n in model.N
        )
        == -model.bulk_energy_kWs[0]
    )


def ch_dis_binary(model, n, t):
    """
    The charge/discharge binary constraint.
    Auxiliary constraint used to prevent batteries from being both charged and discharged at the same timestamp t.

    :param model: The pyomo model.
    :param n: The battery index.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    return model.x_ch[n, t] + model.x_dis[n, t] <= 1


def imp_exp_binary(model, t):
    """
    The import/export binary constraint.
    Auxiliary constraint used to prevent prevent both export and import at the same timestamp t.

    :param model: The pyomo model.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    return model.x_imp[t] + model.x_exp[t] <= 1


def deficit_case_1(model, t):
    """
    First deficit case constraint.
    If you are short on power in a timestamp t, you are not allowed to import more than you do before beeing controlled.

    :param model: The pyomo model.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    if model.P_net_before_kW[t] >= 0:
        return model.P_imp_kW[t] * model.x_imp[t] <= model.P_net_before_kW[t]
    else:
        return Constraint.Feasible


def deficit_case_2(model, n, t):
    """
    Second deficit case constraint.
    If you are short on power in a timestamp t, you are not allowed to charge any of the batteries.

    :param model: The pyomo model.
    :param n: The battery index.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    if model.P_net_before_kW[t] >= 0:
        return model.P_ch_bat_kW[n, t] <= 0
    else:
        return Constraint.Feasible


def surplus_case_1(model, t):
    """
    First surplus case constraint.
    In case of power surplus, batteries should not be charged with a power more than exported power in any timestamp t.
    The goal here is to be sure that batteries are not being charged with the imported power and just with the power surplus.

    :param model: The pyomo model.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    if model.P_net_before_kW[t] <= 0:
        return (
            sum((model.P_ch_bat_kW[n, t]) / model.ch_eff_bat[n] for n in model.N)
            <= -model.P_net_before_kW[t]
        )
    else:
        return Constraint.Feasible


def surplus_case_2(model, t):
    """
    Second surplus case constraint.
    In case of power surplus, it is not allowed to import power.

    :param model: The pyomo model.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    if model.P_net_before_kW[t] <= 0:
        # Note for the future works: As P_imp_kW and x_imp are separated from each other, make sure to always
        # use P_imp_kW in all of the constraints.
        # From now on x_imp can be 1 and P_imp_kW can be 0. Therefore, user MUST use P_imp_kW in the constraints.
        return model.P_imp_kW[t] * model.x_imp[t] <= 0
    else:
        return Constraint.Feasible


def penalty_for_imp(model, t):
    """
    Penalty constraint for imports.
    Added to prevent unnecessary minimal imports. Penalty variable alpha_imp is in the objective function,
    reprsents the peak import, and shall be trying to be minimized.

    :param model: The pyomo model.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    return model.P_imp_kW[t] * model.x_imp[t] <= model.alpha_imp


def penalty_for_exp(model, t):
    """
    Penalty constraint for exports.
    Added to prevent unnecessary minimal exports. Penalty variable alpha_exp is in the objective function,
    represents the peak export and shall be minimized.

    :param model: The pyomo model.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    return model.P_exp_kW[t] * model.x_exp[t] <= model.alpha_exp


def hbes_avoid_diss(model, n, t):
    """
    The constraint to avoid discharging of the household batteries (hbes).
    Household batteries are not allowed to be discharged during the optimization horizon.

    :param model: The pyomo model.
    :param n: The battery index.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    if model.bat_type[n] == "hbes":
        return model.P_dis_bat_kW[n, t] <= 0
    else:
        return Constraint.Feasible


def pv_curtailment_constr(model, t):
    """
    The PV generation curtailment constraint.
    If curtailment is allowed, PV production will be kept below its limits (PV forecast).

    :param model: The pyomo model.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    if model.pv_curtailment:
        return model.P_PV_kW[t] <= model.P_PV_limit_kW[t]
    else:
        return model.P_PV_kW[t] == model.P_PV_limit_kW[t]


def obj_rule(model):
    """
    The objective function.
    Objective: Minimize the power exchange with the grid (Minimum interaction with the grid)
    Power import and export as well as their peak values (alpha) are minimized.
    :param model: The pyomo model.
    :return: The objective function itself.
    """
    return (
        sum(
            model.P_exp_kW[t] * model.x_exp[t] + model.P_imp_kW[t] * model.x_imp[t]
            for t in model.T
        )
        + model.alpha_exp
        + model.alpha_imp
    )


def scheduling(
    P_load_gen: pd.Series,
    df_battery: pd.DataFrame,
    day_end: datetime,
    bulk_data: Bulk,
    P_net_after_kW_limits: pd.DataFrame,
    pv_curtailment: bool,
) -> Tuple[
    pd.Series,
    pd.DataFrame,
    pd.Series,
    pd.DataFrame,
    pd.Series,
    pd.Series,
    pd.Series,
    Tuple[str,str],
]:
    """The scheduling optimization function which acts upon the load and generation forecast data considering
    battery specifications, optimization horizon, and power boundaries.
    Depending on the input data, bulk delivery/reception and PV curtailment can also be satisfied.


    Parameters
    ----------
    P_load_gen : pd.Series
        load and generation forecast time series of float type.
    df_battery : pd.DataFrame
        battery specifications of float and string types.
    day_end : datetime
        user-defined end of the day (datetime) till which household batteries should reach
        maximum SoC. By default, its value is set to then sun-set time.
    bulk_data : Bulk
        Class related to the bulk delivery/reception of energy from batteries including bulk_start
        and _end datetime and the bulk_energy_kWh float.
    P_net_after_kW_limits : pd.DataFrame
        consisiting of upper and lower bound float time series (kW) and
        the integer identifiers for the existance of any upper or lower bounds.
    pv_curtailment : bool
        If true, PV generation can be curtailed.

        (solver.status, solver.termination_condition),

    Returns
    -------
    Tuple[ pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.Series, pd.Series, Tuple[Any, Any], ]
        pv_profile: Series containing the PV (Photovoltaic) profile.
        P_bat_kW_df: DataFrame containing battery power for different nodes.
        P_bat_total_kW: Series containing the total battery power.
        SoC_bat_df: DataFrame containing battery state of charge for different nodes.
        P_net_after_kW: Series containing net power after control.
        P_net_after_kW_upperb: Series containing upper bounds for net power after control.
        P_net_after_kW_lowerb: Series containing lower bounds for net power after control.
        (str, str): status and details from the solver
    """

    # Selected optimization solver
    optimization_solver = SolverFactory("gurobi")
    # optimization_solver = SolverFactory("scip")

    # Initialize necessary values from the inputs
    load = P_load_gen.P_load_kW
    generation = P_load_gen.P_gen_kW
    start_time = load.index[0]
    end_time = load.index[-1]
    delta_T = pd.to_timedelta(load.index.freq)
    opt_horizon = pd.date_range(
        start_time, end_time + delta_T, freq=delta_T, inclusive="left"
    )
    sof_horizon = pd.date_range(
        start_time, end_time + delta_T, freq=delta_T, inclusive="both"
    )
    if bulk_data is not None:
        bulk_horizon = pd.date_range(
            bulk_data.bulk_start, bulk_data.bulk_end, freq=delta_T, inclusive="both"
        )

    considered_load_forecast = load[
        opt_horizon
    ]  # Only the specified time instances in the load forecast will be taken into account
    considered_generation_forecast = generation[
        opt_horizon
    ]  # Only the specified time instances in the generation forecast will be taken into account

    #####################################################################################################
    ##################################       OPTIMIZATION MODEL          #################################
    model = ConcreteModel()

    # Index sets
    # Index set with aggregated battery identifiers
    model.N = list(df_battery.index)
    # Index set with optimization horizon time step identifiers
    model.T = tuple(opt_horizon)
    # Index set with battery horizon time step identifiers
    model.T_SoC_bat = tuple(sof_horizon)
    # Index set with bulk horizon time step identifiers
    if bulk_data is not None:
        model.T_bulk = tuple(bulk_horizon)

    # Parameters
    ######################################################################################################
    # TimeDelta in one time step
    model.dT = delta_T
    model.start_time = start_time
    model.end_time = end_time
    model.day_end = day_end
    # P_net_after_kW (import-export) limits for every each timestamp enabling the microgrid to go full islanding (if both are zero)
    model.upper_bound_kW = P_net_after_kW_limits.upper_bound
    model.lower_bound_kW = P_net_after_kW_limits.lower_bound
    model.with_upper_bound = P_net_after_kW_limits.with_upper_bound
    model.with_lower_bound = P_net_after_kW_limits.with_lower_bound
    # Forecast parameters
    # Total load and generation forecast
    model.P_net_before_kW = considered_load_forecast - considered_generation_forecast
    # Load
    model.P_load_kW = considered_load_forecast
    # Generation limits
    model.P_PV_limit_kW = considered_generation_forecast
    # Battery parameters
    # Type of the battery
    # cbes: comunity battery energy storage, hbes: household battery energy storage
    model.bat_type = df_battery.bat_type
    # Minimum allowable state of charge of the battery n
    model.min_SoC_bat = df_battery.min_SoC
    # Maximum allowable state of charge of the battery n
    model.max_SoC_bat = df_battery.max_SoC
    # State of charge value of battery n at the beginning of the optimization horizon
    model.ini_SoC_bat = df_battery.initial_SoC
    # The value of the final state of charge (if given) to be reached for the battery n at the end of the optimization horizon
    model.final_SoC_bat = df_battery.final_SoC
    # Capacity of the battery n (kWsec)
    model.bat_capacity_kWs = df_battery.bat_capacity_kWs
    # Maximum charging power of the battery n (KW)
    model.P_ch_bat_max_kW = df_battery.P_ch_max_kW
    # Maximum discharging power of the battery n (KW)
    model.P_dis_bat_max_kW = df_battery.P_dis_max_kW
    # Charging efficiency of the battery n
    model.ch_eff_bat = df_battery.ch_efficiency
    # Discharging efficiency of the battery n
    model.dis_eff_bat = df_battery.dis_efficiency
    # Bulk parameters (bulk energy)
    if bulk_data is not None:
        # Bulk energy of battery assets (kWsec)
        model.bulk_energy_kWs = pd.Series([bulk_data.bulk_energy_kWh]) * 3600
    if pv_curtailment is not None:
        model.pv_curtailment = pv_curtailment
    else:
        model.pv_curtailment = False

    # Variables
    ######################################################################################################
    # Power output of PV in timestamp t
    model.P_PV_kW = Var(model.T, within=NonNegativeReals)
    # Power demand of the community in timestamp t
    model.P_dem_kW = Var(model.T, within=NonNegativeReals)
    # PV power feeding the load in timestamp t
    model.P_PV_dem_kW = Var(model.T, within=NonNegativeReals)
    # State of charge of the battery n in timestamp t
    model.SoC_bat = Var(model.N, model.T_SoC_bat, within=NonNegativeReals)
    # Charge power of the battery n in timestamp t
    model.P_ch_bat_kW = Var(model.N, model.T, within=NonNegativeReals)
    # Discharge power of the battery n in timestamp t
    model.P_dis_bat_kW = Var(model.N, model.T, within=NonNegativeReals)
    # Export power to the grid in timestamp t
    model.P_exp_kW = Var(model.T, within=NonNegativeReals)
    # Import power from the grid in timestamp t
    model.P_imp_kW = Var(model.T, within=NonNegativeReals)
    # Penalty variable for import (maximum value of P_imp_kW over time)
    model.alpha_imp = Var(within=NonNegativeReals)
    # Penalty variable for export (maximum value of P_exp_kW over time)
    model.alpha_exp = Var(within=NonNegativeReals)
    # Binary variables
    # Binary variable having 1 if battery n is charged at timestamp t
    model.x_ch = Var(model.N, model.T, within=pmo.Binary)
    # Binary variable having 1 if battery n is discharged at timestamp t
    model.x_dis = Var(model.N, model.T, within=pmo.Binary)
    # Binary variable having 1 if battery n imports power at timestamp t
    model.x_imp = Var(model.T, within=pmo.Binary)
    # Binary variable having 1 if battery n exports power at timestamp t
    model.x_exp = Var(model.T, within=pmo.Binary)

    # Constraints
    ######################################################################################################
    model.power_balance = Constraint(model.T, rule=power_balance)
    model.bat_charging = Constraint(model.N, model.T, rule=bat_charging)
    model.bat_init_SoC = Constraint(model.N, rule=bat_init_SoC)
    model.bat_final_SoC = Constraint(model.N, rule=bat_final_SoC)
    if bulk_data is not None:
        model.bulk_energy = Constraint(rule=bulk_energy)
    model.bat_max_ch_power = Constraint(model.N, model.T, rule=bat_max_ch_power)
    model.bat_max_dis_power = Constraint(model.N, model.T, rule=bat_max_dis_power)
    model.bat_min_SoC = Constraint(model.N, model.T_SoC_bat, rule=bat_min_SoC)
    model.bat_max_SoC = Constraint(model.N, model.T_SoC_bat, rule=bat_max_SoC)
    model.P_net_after_kW_upper_bound = Constraint(
        model.T, rule=P_net_after_kW_upper_bound
    )
    model.P_net_after_kW_lower_bound = Constraint(
        model.T, rule=P_net_after_kW_lower_bound
    )
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

    # Objective function and solver
    ######################################################################################################
    model.obj = Objective(rule=obj_rule, sense=minimize)
    solver = optimization_solver.solve(model).solver

    #####################################################################################################
    ##################################       POST PROCESSING             ################################
    # Initialize DataFrames and Series to store post-processing results
    P_bat_kW_df = pd.DataFrame(index=model.T, columns=df_battery.index)
    P_bat_total_kW = pd.Series(
        index=model.T, dtype=float
    )  # Total battery power (discharging: negative, charging: positive)
    P_net_after_kW = pd.Series(index=model.T, dtype=float)
    bat_ch = pd.DataFrame(index=model.T, columns=df_battery.index)
    bat_dis = pd.DataFrame(index=model.T, columns=df_battery.index)
    SoC_bat_df = pd.DataFrame(index=model.T_SoC_bat, columns=df_battery.index)
    lower_bound = pd.Series(index=model.T, dtype=float)
    upper_bound = pd.Series(index=model.T, dtype=float)

    # Loop through time steps to calculate and store post-processing results
    for t in model.T:
        # Calculate net power after considering import and export
        P_net_after_kW[t] = value(
            model.x_imp[t] * model.P_imp_kW[t] - model.x_exp[t] * model.P_exp_kW[t]
        )
        total_supply = 0
        # Loop through battery nodes (n) to calculate battery power and total supply
        for n in model.N:
            total_supply += value(
                -model.x_dis[n, t] * model.P_dis_bat_kW[n, t] / model.dis_eff_bat[n]
            ) + value(model.x_ch[n, t] * model.P_ch_bat_kW[n, t] * model.ch_eff_bat[n])

            P_bat_kW_df.loc[t, n] = value(
                -model.x_dis[n, t] * model.P_dis_bat_kW[n, t] / model.dis_eff_bat[n]
                + model.x_ch[n, t] * model.P_ch_bat_kW[n, t] * model.ch_eff_bat[n]
            )
        # Store the total supply in P_bat_total_kW
        P_bat_total_kW[t] = total_supply

        # Check if lower and upper bounds exist for this time step and store them
        if model.with_lower_bound[t]:
            lower_bound[t] = model.lower_bound_kW[t]
        if model.with_upper_bound[t]:
            upper_bound[t] = model.upper_bound_kW[t]

    # Loop through battery nodes (col) to extract charging, discharging, and SoC data
    for col in df_battery.index:
        bat_ch[col] = model.P_ch_bat_kW[col, :]()
        bat_dis[col] = model.P_dis_bat_kW[col, :]()
        SoC_bat_df[col] = model.SoC_bat[col, :]()

    # Extract the PV profile data
    PV_profile = pd.Series(model.P_PV_kW[:](), index=model.T)

    return (
        PV_profile,
        P_bat_kW_df,
        P_bat_total_kW,
        SoC_bat_df,
        P_net_after_kW,
        upper_bound,
        lower_bound,
        (solver.status, solver.termination_condition),
    )


def prep_output_df(
    pv_profile: pd.Series,
    P_bat_kW_df: pd.DataFrame,
    P_bat_total_kW: pd.Series,
    SoC_bat_df: pd.DataFrame,
    P_net_after_kW: pd.Series,
    df_forecasts: pd.DataFrame,
    P_net_after_kW_upperb: pd.Series,
    P_net_after_kW_lowerb: pd.Series,
):
    """
    Prepare the output DataFrame of scheduling optimization based mode.

    Parameters
    ---------- 
    pv_profile : pd.Series
        containing the PV profile.
    P_bat_kW_df : DataFrame
        containing battery power for different nodes.
    P_bat_total_kW : pd.Series
        containing the total battery power.
    SoC_bat_df : DataFrame
        containing battery state of charge for different nodes.
    P_net_after_kW : pd.Series
        containing net power after control.
    df_forecasts : DataFrame
        containing forecasted data.
    P_net_after_kW_upperb : pd.Series
        containing upper bounds for net power after control.
    P_net_after_kW_lowerb : pd.Series
        containing lower bounds for net power after control.

    Returns
    ----------    
    output_df : DataFrame
        containing prepared output data.

    """
    # Create an empty output DataFrame with the same index as df_forecasts
    output_df = pd.DataFrame(index=df_forecasts.index)

    # Calculate 'P_net_before_kW' as the difference between load and generation
    output_df["P_net_before_kW"] = df_forecasts["P_load_kW"] - df_forecasts["P_gen_kW"]

    # Calculate 'P_net_before_controlled_PV_kW' as the difference between load and controlled PV
    output_df["P_net_before_controlled_PV_kW"] = df_forecasts["P_load_kW"] - pv_profile

    # Add columns for PV forecast and controlled PV
    output_df["P_PV_forecast_kW"] = df_forecasts["P_gen_kW"]
    output_df["P_PV_controlled_kW"] = pv_profile

    # Add columns for net power after control, upper bounds, and lower bounds
    output_df["P_net_after_kW"] = P_net_after_kW
    output_df["upperb"] = P_net_after_kW_upperb
    output_df["lowerb"] = P_net_after_kW_lowerb

    # Iterate through columns in P_bat_kW_df and SoC_bat_df to add battery-related data
    for col in P_bat_kW_df.columns:
        output_df[f"P_{col}_kW"] = P_bat_kW_df[col]
        output_df[f"SoC_{col}_%"] = SoC_bat_df[col] * 100

    # Add the total battery power column
    output_df["P_bat_total_kW"] = P_bat_total_kW

    return output_df
