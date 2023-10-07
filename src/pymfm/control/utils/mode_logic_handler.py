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
#substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING 
# BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND 
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import pandas as pd
from pyomo.opt import SolverStatus, TerminationCondition
from pymfm.control.utils import data_input, data_output
from pymfm.control.utils.data_input import (
    InputData,
    ControlLogic as CL,
    OperationMode as OM,
)
from pymfm.control.algorithms import optimization_based as OptB
from pymfm.control.algorithms import rule_based as RB


def mode_logic_handler(data: InputData):
    """
    Handle different control logic modes and operation modes.

    :param data: InputData object containing input data.
    :return: Tuple containing mode logic information, output DataFrame, and solver status.
    """
    # Prepare battery specifications, converting battery percentage to absolute values
    battery_specs = data_input.input_prep(data.battery_specs)

    if data.control_logic == CL.RULE_BASED:
        if data.operation_mode == OM.SCHEDULING:
            # Prepare the forecasted data
            df_forecasts = data_input.generation_and_load_to_df(
                data.generation_and_load, start=data.uc_start, end=data.uc_end
            )

            # If multiple battery nodes are present, handle them
            if isinstance(battery_specs, list):
                if len(battery_specs) == 1:
                    battery_specs = battery_specs[0]
                else:
                    raise RuntimeError(
                        "Rule based control cannot deal with multiple flex nodes."
                    )

            # Initialize the output DataFrame
            output_df = None
            delta_T = pd.to_timedelta(df_forecasts.P_load_kW.index.freq)
            print(
                "Input data has been read successfully. Running scheduling rule-based control."
            )

            # Iterate through forecasted data and perform scheduling
            for time, P_net_before_kW in df_forecasts.iterrows():
                output = RB.scheduling(P_net_before_kW, battery_specs, delta_T)

                # Initialize output DataFrame if not created
                if output_df is None:
                    output_df = pd.DataFrame(
                        columns=output.index, index=df_forecasts.index
                    )

                # Append the output for the current time
                output_df.loc[time] = output

                # Update initial SoC for the next time step
                battery_specs.initial_SoC = (
                    output.bat_energy_kWs / battery_specs.bat_capacity_kWs
                )
            print("Scheduling rule-based control finished.")

            # Rename columns for battery-specific data
            if battery_specs.id is not None:
                output_df.rename(
                    {"P_bat_kW": f"P_{battery_specs.id}_kW"}, inplace=True, axis=1
                )
                output_df.rename(
                    {"SoC_bat": f"SoC_{battery_specs.id}_%"}, inplace=True, axis=1
                )
            else:
                output_df.rename({"P_bat_kW": "P_bat_1_kW"}, inplace=True, axis=1)
                output_df.rename({"SoC_bat": "SoC_bat_1_%"}, inplace=True, axis=1)

            # Drop unnecessary columns
            output_df = output_df.drop(
                ["bat_energy_kWs", "import_kW", "export_kW"], axis=1
            )

            # Define mode_logic information
            mode_logic = {
                "ID": data.id,
                "CL": data.control_logic,
                "OM": data.operation_mode,
            }

            return (
                mode_logic,
                output_df,
                (SolverStatus.ok, TerminationCondition.optimal),
            )

        if data.operation_mode == OM.NEAR_REAL_TIME:
            # Handle near real-time rule-based control
            if isinstance(battery_specs, list):
                if len(battery_specs) == 1:
                    battery_specs = battery_specs[0]
                else:
                    raise RuntimeError(
                        "Near real-time control cannot deal with multiple flex nodes."
                    )

            # Prepare measurements request data
            measurements_request_dict = data_input.measurements_request_to_dict(
                data.measurements_request
            )

            print(
                "Input data has been read successfully. Running near real-time rule-based control."
            )

            # Perform near real-time rule-based control
            output_df = RB.near_real_time(measurements_request_dict, battery_specs)

            # Define mode_logic information
            mode_logic = {
                "ID": data.id,
                "CL": data.control_logic,
                "OM": data.operation_mode,
            }

            print("Near real-time rule-based control finished.")
            return (
                mode_logic,
                output_df,
                (SolverStatus.ok, TerminationCondition.optimal),
            )

    if data.control_logic == CL.OPTIMIZATION_BASED:
        # Prepare forecasted data
        df_forecasts = data_input.generation_and_load_to_df(
            data.generation_and_load, start=data.uc_start, end=data.uc_end
        )

        # Prepare power limitations data
        P_net_after_kW_limits = data_input.P_net_after_kW_lim_to_df(
            data.P_net_after_kW_limitation, data.generation_and_load
        )

        # Prepare battery specifications data
        df_battery_specs = data_input.battery_to_df(battery_specs)

        print(
            "Input data has been read successfully. Running scheduling optimization-based control."
        )

        # Perform scheduling optimization-based control
        (
            P_net_after_kW,
            PV_profile,
            P_bat_kW_df,
            P_bat_total_kW,
            SoC_bat_df,
            upper_bound_kW,
            lower_bound_kW,
            solver_status,
        ) = OptB.scheduling(
            df_forecasts,
            df_battery_specs,
            data.day_end,
            data.bulk,
            P_net_after_kW_limits,
            data.generation_and_load.pv_curtailment,
        )

        print("Scheduling optimization-based control finished.")

        # Prepare the output DataFrame
        output_df = OptB.prep_output_df(
            P_net_after_kW,
            PV_profile,
            P_bat_kW_df,
            P_bat_total_kW,
            SoC_bat_df,
            df_forecasts,
            upper_bound_kW,
            lower_bound_kW,
        )

        # Define mode_logic information
        mode_logic = {
            "ID": data.id,
            "CL": data.control_logic,
            "OM": data.operation_mode,
        }

        return mode_logic, output_df, solver_status
