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
from pyomo.opt import SolverStatus, TerminationCondition

from pymfm.control.algorithms import optimization_based as OptB
from pymfm.control.algorithms import rule_based as RB
from pymfm.control.utils.common import extract_df, get_freq
from pymfm.control.utils.data_input import BatterySpecs, ControlLogic as CL
from pymfm.control.utils.data_input import InputData
from pymfm.control.utils.data_output import BalancerOutput, validate_timestep


def mode_logic_handler(
    # df: pd.DataFrame,
    # df_battery_specs: pd.DataFrame,
    # delta_T_h: float,
    data: InputData,
) -> Tuple[BalancerOutput, tuple[SolverStatus, TerminationCondition]]:
    """
    Handle different control logic modes and operation modes.

    :param data: InputData object containing input data.
    :return: Tuple containing mode logic information, output DataFrame, and solver status.
    """
    # Prepare battery specifications, converting battery percentage to absolute values
    # battery_specs = data_input.input_prep(data.battery_specs)

    # prep data as Dataframes and default outputs
    df, df_battery_specs, delta_T_h = prep_data(data)
    solver_status = (SolverStatus.ok, TerminationCondition.optimal)
    peak_exp = None
    peak_imp = None

    if data.control_logic == CL.RULE_BASED:
        output_df = RB.rule_based(df, df_battery_specs, delta_T_h)

    elif data.control_logic == CL.OPTIMIZATION_BASED:
        print(
            "Input data has been read successfully. Running scheduling optimization-based control."
        )

        # Perform scheduling optimization-based control
        (output_batteries, output_system, output_static, solver_status) = (
            OptB.scheduling(
                df,
                df_battery_specs,
                data.day_end,
                data.bulk,
                data.generation_and_load.pv_curtailment,
            )
        )

        print("Scheduling optimization-based control finished.")

        # postprocess
        ## prep batteries output
        tmp = output_batteries.P_ch_bat_kW - output_batteries.P_dis_bat_kW
        tmp.columns = pd.MultiIndex.from_product([["P_bat_kW"], tmp.columns])
        output_df = output_batteries.join(tmp)
        output_df.drop(
            ["is_ch", "is_dis", "P_ch_bat_kW", "P_dis_bat_kW"],
            axis="columns",
            level=0,
            inplace=True,
        )
        # output_df.columns = ["|".join(col) for col in output_df.columns.to_flat_index()]
        ## prep system output
        output_system["P_net_after_kW"] = (
            output_system.P_imp_kW - output_system.P_exp_kW
        )
        output_system.drop(
            ["is_imp", "is_exp", "P_exp_kW", "P_imp_kW"], axis="columns", inplace=True
        )

        ## combine
        output_system.columns = pd.MultiIndex.from_product(
            [output_system.columns, [""]]
        )
        output_df = output_df.join(output_system)
        peak_exp = output_static.peak_exp
        peak_imp = output_static.peak_imp

    else:
        raise AttributeError(
            "control logic needs to be either `rule_base` or `optimization`"
        )

    output_ts = [
        validate_timestep(data.to_dict())
        for time, data in output_df.reset_index().iterrows()
    ]

    out = BalancerOutput(
        id=data.id, peak_imp=peak_imp, peak_exp=peak_exp, schedule=output_ts
    )

    return (
        out,
        solver_status,
    )


def prep_data(data: InputData):
    if data.generation_and_load is None:
        raise RuntimeWarning(
            "Generation and load not specified"
        )  # TODO generation and load should be named something else.

    # Prepare forecasted data
    df_power = extract_df(
        data.generation_and_load, attr="values", index_col="timestamp"
    )

    # Prepare power limitations data
    df_limits = extract_df(
        data, attr="P_net_after_kW_limitation", index_col="timestamp"
    )

    # Prepare battery specifications data
    df_battery_specs = extract_df(data, attr="battery_specs", index_col="id")
    delta_T_h = data.generation_and_load.delta_T_h
    if delta_T_h is None:
        delta_T_h = get_freq(df_power, df_limits).nanos * 1e-9 / 3600

    df = df_power.asfreq(f"{delta_T_h}H")
    if df_limits is not None:
        df = df.join(df_limits)

    # TODO readd start and stop time
    return df, df_battery_specs, delta_T_h
