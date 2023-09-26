# The pymfm framework

# Copyright (C) 2023,
# Institute for Automation of Complex Power Systems (ACS),
# E.ON Energy Research Center (E.ON ERC),
# RWTH Aachen University

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
# Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import pandas as pd
from datetime import timedelta
from pymfm.control.utils.data_input import BatterySpecs


def near_real_time(measurements_request_dict: dict, battery_specs: BatterySpecs):
    # TO-DO: Amir
    """

    :param measurements_request_dict:
    :param battery_specs:
    :return:
    """
    output = dict.fromkeys(
        [
            "timestamp",
            "initial_SoC_bat_%" "SoC_bat_%",
            "P_bat_kW",
            "P_net_meas_kW",
            "P_net_after_kW",
        ]
    )
    output["timestamp"] = measurements_request_dict["timestamp"]
    # initialize
    output["initial_SoC_bat_%"] = battery_specs.initial_SoC
    import_kW = 0
    export_kW = 0
    bat_Energy_kWh = 0
    bat_initial_Energy_kWh = battery_specs.initial_SoC * battery_specs.bat_capacity_kWh
    bat_min_Energy_kWh = battery_specs.min_SoC * battery_specs.bat_capacity_kWh
    bat_max_Energy_kWh = battery_specs.max_SoC * battery_specs.bat_capacity_kWh
    output["P_bat_kW"] = (
        -measurements_request_dict["P_req_kW"]
        + measurements_request_dict["P_net_meas_kW"]
    )
    if output["P_bat_kW"] > 0:
        bat_Energy_kWh = bat_initial_Energy_kWh - (
            battery_specs.dis_efficiency
            * output["P_bat_kW"]
            * measurements_request_dict["delta_T_h"]
        )
        output["P_bat_kW"] = output["P_bat_kW"] / battery_specs.dis_efficiency
    else:
        bat_Energy_kWh = (
            bat_initial_Energy_kWh
            - (output["P_bat_kW"] * measurements_request_dict["delta_T_h"])
            / battery_specs.ch_efficiency
        )
        output["P_bat_kW"] = output["P_bat_kW"] * battery_specs.ch_efficiency
    # discharging
    if output["P_bat_kW"] > 0:
        act_ptcb = output["P_bat_kW"]
        if abs(output["P_bat_kW"]) < battery_specs.P_dis_max_kW:
            pass
        else:
            import_kW = output["P_bat_kW"] - battery_specs.P_dis_max_kW
            output["P_bat_kW"] = battery_specs.P_dis_max_kW
            bat_Energy_kWh = (
                bat_initial_Energy_kWh
                - battery_specs.dis_efficiency
                * battery_specs.P_dis_max_kW
                * measurements_request_dict["delta_T_h"]
            )
        if bat_Energy_kWh >= bat_min_Energy_kWh:
            pass
        else:
            import_kW = import_kW + (
                (
                    (bat_min_Energy_kWh - bat_Energy_kWh)
                    / measurements_request_dict["delta_T_h"]
                )
            )
            output["P_bat_kW"] = act_ptcb - import_kW

            bat_Energy_kWh = bat_min_Energy_kWh
        output["P_bat_kW"] = float(output["P_bat_kW"])
    # charging
    if output["P_bat_kW"] < 0:
        act_ptcb = output["P_bat_kW"]
        if abs(output["P_bat_kW"]) <= battery_specs.P_ch_max_kW:
            export_kW = 0
            pass
        else:
            export_kW = abs(output["P_bat_kW"]) - battery_specs.P_ch_max_kW
            output["P_bat_kW"] = -battery_specs.P_ch_max_kW
            bat_Energy_kWh = (
                bat_initial_Energy_kWh
                + (battery_specs.P_ch_max_kW * measurements_request_dict["delta_T_h"])
                / battery_specs.ch_efficiency
            )
        if bat_Energy_kWh <= bat_max_Energy_kWh:
            pass
        else:
            export_kW = export_kW + (
                (bat_Energy_kWh - bat_max_Energy_kWh)
                / measurements_request_dict["delta_T_h"]
            )
            output["P_bat_kW"] = -(abs(act_ptcb) - export_kW)
            bat_Energy_kWh = bat_max_Energy_kWh
        output["P_bat_kW"] = float(output["P_bat_kW"])
    output["SoC_bat_%"] = bat_Energy_kWh / battery_specs.bat_capacity_kWh * 100
    output["P_net_meas_kW"] = measurements_request_dict["P_net_meas_kW"]
    output["P_net_after_kW"] = -export_kW + import_kW
    output["P_bat_kW"] = (
        output["P_bat_kW"] * -1
    )  # charging: positiv, discharging: negativ
    return output


def scheduling(P_load_gen: pd.Series, battery_specs: BatterySpecs, delta_T: timedelta):
    # TO-DO: Amir
    """

    :param P_load_gen:
    :param battery_specs:
    :param delta_T:
    :return:
    """
    # initialize
    output_ds = pd.Series(
        index=[
            "P_net_before_kW",
            "P_net_after_kW",
            "P_bat_kW",
            "SoC_bat",
            "bat_energy_kWs",
            "import_kW",
            "export_kW",
        ],
        dtype=float,
    )
    output_ds.import_kW = 0
    output_ds.export_kW = 0
    output_ds.bat_energy_kWs = 0
    # Convert timedelta to float in terms of seconds
    delta_time_in_sec = delta_T.total_seconds()
    output_ds.P_bat_kW = P_load_gen.P_load_kW - P_load_gen.P_gen_kW

    if output_ds.P_bat_kW > 0:
        output_ds.bat_energy_kWs = (
            battery_specs.initial_SoC * battery_specs.bat_capacity_kWs
            - (battery_specs.dis_efficiency * output_ds.P_bat_kW * delta_time_in_sec)
        )
        output_ds.P_bat_kW = output_ds.P_bat_kW / battery_specs.dis_efficiency
    else:
        output_ds.bat_energy_kWs = (
            battery_specs.initial_SoC * battery_specs.bat_capacity_kWs
            - (output_ds.P_bat_kW * delta_time_in_sec) / battery_specs.ch_efficiency
        )
        output_ds.P_bat_kW = output_ds.P_bat_kW * battery_specs.ch_efficiency
    # discharging
    if output_ds.P_bat_kW > 0:
        act_ptcb = output_ds.P_bat_kW
        if abs(output_ds.P_bat_kW) >= battery_specs.P_dis_max_kW:
            output_ds.import_kW = output_ds.P_bat_kW - battery_specs.P_dis_max_kW
            output_ds.P_bat_kW = battery_specs.P_dis_max_kW
            output_ds.bat_energy_kWs = (
                battery_specs.initial_SoC * battery_specs.bat_capacity_kWs
                - (
                    battery_specs.dis_efficiency
                    * battery_specs.P_dis_max_kW
                    * delta_time_in_sec
                )
            )
        if (
            output_ds.bat_energy_kWs
            < battery_specs.min_SoC * battery_specs.bat_capacity_kWs
        ):
            output_ds.import_kW = output_ds.import_kW + (
                (
                    battery_specs.min_SoC * battery_specs.bat_capacity_kWs
                    - output_ds.bat_energy_kWs
                )
                / delta_time_in_sec
            )
            output_ds.P_bat_kW = act_ptcb - output_ds.import_kW
            output_ds.bat_energy_kWs = (
                battery_specs.min_SoC * battery_specs.bat_capacity_kWs
            )
    # charging
    if output_ds.P_bat_kW < 0:
        act_ptcb = output_ds.P_bat_kW
        if abs(output_ds.P_bat_kW) <= battery_specs.P_ch_max_kW:
            output_ds.export_kW = 0
            pass
        else:
            output_ds.export_kW = abs(output_ds.P_bat_kW) - battery_specs.P_ch_max_kW
            output_ds.P_bat_kW = -battery_specs.P_ch_max_kW
            output_ds.bat_energy_kWs = (
                battery_specs.initial_SoC * battery_specs.bat_capacity_kWs
                + (battery_specs.P_ch_max_kW * delta_time_in_sec)
                / battery_specs.ch_efficiency
            )
        if (
            output_ds.bat_energy_kWs
            > battery_specs.max_SoC * battery_specs.bat_capacity_kWs
        ):
            output_ds.export_kW = output_ds.export_kW + (
                (
                    output_ds.bat_energy_kWs
                    - battery_specs.max_SoC * battery_specs.bat_capacity_kWs
                )
                / delta_time_in_sec
            )
            output_ds.P_bat_kW = -(abs(act_ptcb) - (output_ds.export_kW))
            output_ds.bat_energy_kWs = (
                battery_specs.max_SoC * battery_specs.bat_capacity_kWs
            )
        output_ds.P_bat_kW = float(output_ds.P_bat_kW)
    output_ds.P_net_before_kW = P_load_gen.P_load_kW - P_load_gen.P_gen_kW
    output_ds.P_net_after_kW = -output_ds.export_kW + output_ds.import_kW
    output_ds.SoC_bat = (
        output_ds.bat_energy_kWs / battery_specs.bat_capacity_kWs
    ) * 100
    output_ds.P_bat_kW = (
        output_ds.P_bat_kW * -1
    )  # charging: positiv, discharging: negativ

    return output_ds