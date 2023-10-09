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


import pandas as pd
from datetime import timedelta
from pymfm.control.utils.data_input import BatterySpecs


def near_real_time(measurements_request_dict: dict, battery_specs: BatterySpecs):
    """
    For this operation mode, rule based logic is implemented on the net power measurement of
    the microgrid respecting battery boundaries.
    In case of a (near) real time power requests from the microgrid, this request is resecpted
    by the microgrid community battery energy storage (cbes).

    Parameters
    ----------
    measurements_request_dict : dict of dict
        In the measurement_request dictionary, for each time stamp (datetime), the corresponding
        float values for the requested (P_req_kW) and measured (P_net_meas_kW) net power
        consumption of the microgrid (in kW).
    battery_specs : pymfm.control.utils.data_input.BatterySpecs 
        BatterySpecs class and the corresponding pydantic model representing
        string values of battery "type" and "id" and float values of initital SoC in %,
        maximum charging and discharging powers in kW, min and max SoC in %, battery capacity in kWh,
        and (dis)charging efficiency (0<efficiency<=1)

    Returns
    -------
    output : dict
        In the output dictionary and for each measurement "timestamp" (datetime), the corresponding
        initial SoC "initial_SoC_bat_%" and final SoC "SoC_bat_%" before and after control action in % (float),
        community battery energy storage cbes power setpoint "P_bat_kW" in kW (float), 
        and net power consumption before "P_net_meas_kW" and after "P_net_after_kW" control action in kW (float)
        are returned.

    """
    output = dict.fromkeys(
        [
            "timestamp",
            "initial_SoC_bat_%",
            "SoC_bat_%",
            "P_bat_kW",
            "P_net_meas_kW",
            "P_net_after_kW",
        ]
    )
    output["timestamp"] = measurements_request_dict["timestamp"]
    # initialize
    output["initial_SoC_bat_%"] = battery_specs.initial_SoC * 100
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
    """
    For the scheduling operation mode and with the rule based logic, the same control method as
    in (near) real time is implemented. However, this logic is implemented on the net power
    forecast profile of the microgrid and not on the power measured at each instance.

    Parameters
    ----------
    P_load_gen : pd.Series
        load and generation forecast time series of float type
    param battery_specs : pymfm.control.utils.data_input.BatterySpecs
        BatterySpecs class and the corresponding pydantic model representing
        string values of battery "type" and "id" and float values of initital SoC (between 0 and 1),
        maximum charging and discharging powers in kW, min and max SoC (between 0 and 1), battery capacity in kWh,
        and (dis)charging efficiency (0<efficiency<=1)
    delta_T : timedelta
        Pandas TimeDelta object (in day unit) representing time intervals of the forecast time series.

    Returns
    -------
    output_ds: pd.Series 
        In the output Pandas series and for each forecast timestamp, the corresponding
        net power consumption before "P_net_before_kW" and after "P_net_after_kW" control action in kW,
        community battery energy storage (cbes) power setpoint in kW , battery SoC in % "SoC_bat" and its
        associated energy in kWs "bat_energy_kWs", and imported "import_kW" and exported "export_kW" powers
        afer control action in kW are reported.
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
