import pandas as pd
from pyomo.opt import SolverStatus, TerminationCondition
from utils import data_input, data_output
from utils.data_input import (
    InputData,
    ControlLogic as CL,
    OperationMode as OM,
)
from utils import optimization_based as OptB
from utils import rule_based as RB


def mode_logic_handler(data: InputData):
    """

    :param data:
    :return:
    """
    battery_specs = data_input.input_prep(data.battery_specs)

    if data.control_logic == CL.RULE_BASED:
        if data.operation_mode == OM.SCHEDULING:
            df_forecasts = data_input.generation_and_load_to_df(
                data.generation_and_load, start=data.uc_start, end=data.uc_end
            )

            if isinstance(battery_specs, list):
                if len(battery_specs) == 1:
                    battery_specs = battery_specs[0]
                else:
                    raise RuntimeError(
                        "Rule based control can not deal with multiple flex nodes."
                    )
            output_df = None
            delta_T = pd.to_timedelta(df_forecasts.P_load_kW.index.freq)
            for time, P_net_before_kW in df_forecasts.iterrows():
                print(
                    "Input data has been read succesfully. Running scheduling rule based control."
                )
                output = RB.scheduling(P_net_before_kW, battery_specs, delta_T)
                print("Scheduling rule based control finished.")
                if output_df is None:
                    output_df = pd.DataFrame(
                        columns=output.index, index=df_forecasts.index
                    )
                output_df.loc[time] = output
                battery_specs.initial_SoC = (
                    output.bat_energy_kWs / battery_specs.bat_capacity_kWs
                )
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
            output_df = output_df.drop(
                ["bat_energy_kWs", "import_kW", "export_kW"], axis=1
            )
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
            if isinstance(battery_specs, list):
                if len(battery_specs) == 1:
                    battery_specs = battery_specs[0]
                else:
                    raise RuntimeError(
                        "Near real time control can not deal with multiple flex nodes."
                    )
            measurements_request_dict = data_input.measurements_request_to_dict(
                data.measurements_request
            )
            print(
                "Input data has been read succesfully. Running near real time rule based control."
            )
            output_df = RB.near_real_time(measurements_request_dict, battery_specs)
            mode_logic = {
                "ID": data.id,
                "CL": data.control_logic,
                "OM": data.operation_mode,
            }
            print("Near real time rule based control finished.")
            return (
                mode_logic,
                output_df,
                (SolverStatus.ok, TerminationCondition.optimal),
            )

    if data.control_logic == CL.OPTIMIZATION_BASED:
        df_forecasts = data_input.generation_and_load_to_df(
            data.generation_and_load, start=data.uc_start, end=data.uc_end
        )

        P_net_after_kW_limits = data_input.P_net_after_kW_lim_to_df(
            data.P_net_after_kW_limitation, data.generation_and_load
        )
        df_battery_specs = data_input.battery_to_df(battery_specs)
        print(
            "Input data has been read succesfully. Running scheduling optimization based control."
        )
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
        print("Scheduling optimization based control finished.")
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
        mode_logic = {
            "ID": data.id,
            "CL": data.control_logic,
            "OM": data.operation_mode,
        }

        return mode_logic, output_df, solver_status
