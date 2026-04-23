# The pymfm framework
#
# Copyright (C) 2023, Institute for Automation of Complex Power Systems (ACS),
# E.ON Energy Research Center (E.ON ERC), RWTH Aachen University
#
# Licensed under the Apache License, Version 2.0 (the "License").
#
# Pure Pyomo constraint functions.
# Each function takes only the model (and optional indices) and returns a
# Pyomo constraint expression or Constraint.Feasible.
# No I/O, no solver references, no DataFrame logic belongs here.

import pandas as pd
from pyomo.core import Constraint


def power_balance(model, t):
    """
    The power balance constraint.

    :param model: The pyomo model.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    return (
        model.P_required_kW[t]
        + sum(model.P_ch_bat_kW[n, t] for n in model.N)
        + model.P_exp_kW[t] * model.is_exp[t]
        == sum(model.P_dis_bat_kW[n, t] for n in model.N)
        + model.P_imp_kW[t] * model.is_imp[t]
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


def bat_final_SoC(model, n):
    """
    The battery final state of charge (SoC) constraint.
    Secures that batteries reach their final desired SoC at the very end timestamp t. If the battery type is
    household (hbes), then final desired SoC to be reached at the timestamp t, where daylight ends (day_end).

    :param model: The pyomo model.
    :param n: The battery index.
    :return: The constraint itself.
    """
    if model.final_SoC_bat[n] is None:
        return Constraint.Feasible
    if model.bat_type[n] == "hbes":
        return model.SoC_bat[n, model.day_end] == model.max_SoC_bat[n]
    return model.SoC_bat[n, model.end_time] == model.final_SoC_bat[n]


def bat_max_ch_power(model, n, t):
    """
    The battery maximum charging power constraint.
    Limits the charging power of the batteries according to their maximum charging powers.

    :param model: The pyomo model.
    :param n: The battery index.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    return model.P_ch_bat_kW[n, t] <= float(model.P_ch_bat_max_kW[n]) * model.is_ch[n, t]


def bat_max_dis_power(model, n, t):
    """
    The battery maximum discharging power constraint.
    Limits the discharging power of the batteries according to their maximum discharging powers.

    :param model: The pyomo model.
    :param n: The battery index.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    return model.P_dis_bat_kW[n, t] <= float(model.P_dis_bat_max_kW[n]) * model.is_dis[n, t]


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
    if pd.isna(model.lower_bound_kW[t]):
        return Constraint.Feasible
    return (
        model.lower_bound_kW[t]
        <= model.P_imp_kW[t] * model.is_imp[t] - model.P_exp_kW[t] * model.is_exp[t]
    )


def P_net_after_kW_upper_bound(model, t):
    """
    The P_net_after_kW upper bound constraint.
    If there is a upper bound for timestamp t, it limits the P_net_after_kW (= P_imp_kW - P_exp_kW) accordingly.

    :param model: The pyomo model.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    if pd.isna(model.upper_bound_kW[t]):
        return Constraint.Feasible
    return (
        model.P_imp_kW[t] * model.is_imp[t] - model.P_exp_kW[t] * model.is_exp[t]
        <= model.upper_bound_kW[t]
    )


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
    return model.is_ch[n, t] + model.is_dis[n, t] <= 1


def imp_exp_binary(model, t):
    """
    The import/export binary constraint.
    Auxiliary constraint used to prevent prevent both export and import at the same timestamp t.

    :param model: The pyomo model.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    return model.is_imp[t] + model.is_exp[t] <= 1


def deficit_case_1(model, t):
    """
    First deficit case constraint.
    If you are short on power in a timestamp t, you are not allowed to import more than you do before beeing controlled.

    :param model: The pyomo model.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    if model.P_net_before_kW[t] >= 0:
        return model.P_imp_kW[t] * model.is_imp[t] <= model.P_net_before_kW[t]
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
        return model.P_imp_kW[t] * model.is_imp[t] <= 0
    return Constraint.Feasible


def penalty_for_imp(model, t):
    """
    Penalty constraint for imports.
    Added to prevent unnecessary minimal imports. Penalty variable peak_imp is in the objective function,
    reprsents the peak import, and shall be trying to be minimized.

    :param model: The pyomo model.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    return model.P_imp_kW[t] * model.is_imp[t] <= model.peak_imp


def penalty_for_exp(model, t):
    """
    Penalty constraint for exports.
    Added to prevent unnecessary minimal exports. Penalty variable peak_exp is in the objective function,
    represents the peak export and shall be minimized.

    :param model: The pyomo model.
    :param t: The timestamp index.
    :return: The constraint itself.
    """
    return model.P_exp_kW[t] * model.is_exp[t] <= model.peak_exp


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
    return model.P_PV_kW[t] == model.P_PV_limit_kW[t]


def obj_rule(model):
    """
    The objective function.
    Objective: Minimize the power exchange with the grid (Minimum interaction with the grid)
    Power import and export as well as their peak values (peak) are minimized.
    :param model: The pyomo model.
    :return: The objective function itself.
    """
    return (
        sum(
            model.P_exp_kW[t] * model.is_exp[t] + model.P_imp_kW[t] * model.is_imp[t]
            for t in model.T
        )
        + model.peak_exp
        + model.peak_imp
    )
