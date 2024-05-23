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


from datetime import timedelta
from typing import List, Optional, Tuple, Union

import pandas as pd

from pymfm.control.utils.data_input import BatterySpecs, MeasurementsRequest


def clamp_and_delta(
    value: float, upper: Union[float, List[float]] = 0, lower: Union[float, List[float]] = 0
) -> Tuple[float, float]:
    """Clamps value between upper and lower and return it with the difference such that
    lower <= return[0] <= upper and return[0]+return[1]=value
    """
    if isinstance(upper, list):
        upper_cap = min(value, *upper)
    else:
        upper_cap = min(value, upper)
    if isinstance(lower, list):
        acutal = max(upper_cap, *lower)
    else:
        acutal = max(upper_cap, lower)
    return (acutal, value - acutal)


def combined_rule_based(raw_demand_kw: float, battery_specs: BatterySpecs, delta_T_h: float):
    output_ds = pd.Series(
        index=[
            "SoC_bat_per",
            "P_net_after_kW",
            "P_bat_kW",
            # "import_kW",
            # "export_kW",
        ],
        dtype=float,
    )
    # P value that reaches max state of charge in delta_T_h, from network perspective
    # / ch_efficency as the net can but in more charge due to loss from efficency
    P_max_soc = (
        (battery_specs.max_SoC - battery_specs.initial_SoC)
        * battery_specs.bat_capacity_kWh
        / (delta_T_h * battery_specs.ch_efficiency)
    )
    # P value that reaches min state of charge in delta_T_h, from network perspective
    # is negative which corresponds to discharging correctly
    # * ch_efficency as the battery loses more charge than it provides to the net
    P_min_soc = (
        (battery_specs.min_SoC - battery_specs.initial_SoC)
        * battery_specs.bat_capacity_kWh
        * battery_specs.dis_efficiency
        / delta_T_h
    )

    # limit power delivered by max charging and discharging and max available charge/capacity
    # TODO confirm that P_max are power received on network side not on battery side.
    met_demand_kw, access_demand = clamp_and_delta(
        raw_demand_kw, upper=[battery_specs.P_dis_max_kW, P_min_soc], lower=[-battery_specs.P_ch_max_kW, -P_max_soc] 
    )

    # TODO confirm that setpoints for battery are from battery perspective not network perspective
    # discharging
    if raw_demand_kw > 0:
        P_bat_kw = met_demand_kw / battery_specs.dis_efficiency
    # charging
    else:
        P_bat_kw = met_demand_kw * battery_specs.ch_efficiency

    output_ds.SoC_bat_per = battery_specs.initial_SoC - (P_bat_kw * delta_T_h / battery_specs.bat_capacity_kWh)
    output_ds.P_net_after_kW = access_demand 
    output_ds.P_bat_kW = -P_bat_kw  # charging: positiv, discharging: negativ
    return output_ds


def near_real_time(
    measurements_request: MeasurementsRequest,
    battery_specs: BatterySpecs,
    delta_T_h: float = None,
):
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
    # output_ds = dict.fromkeys(
    #     [
    #         "timestamp",
    #         "initial_SoC_bat_%",
    #         "SoC_bat_%",
    #         "P_bat_kW",
    #         "P_net_meas_kW",
    #         "P_net_after_kW",
    #     ]
    # )
    delta_T_h = delta_T_h if delta_T_h else measurements_request.delta_T_h
    output_ds = pd.Series(
        index=[
            # "timestamp", # XXX should be handled by logic handler
            "initial_SoC_bat_per",
            "SoC_bat_per",
            "P_bat_kW",
            "P_net_meas_kW",
            "P_net_after_kW",
            "bat_energy_kWh",
            "import_kW",
            "export_kW",
        ],
        dtype=float,
    )
    # "timestamp",
    #         "initial_SoC_bat_per",
    #         "SoC_bat_per",
    #         "P_bat_kW",
    #         "P_net_meas_kW",
    #         "P_net_after_kW",
    #         "bat_energy_kWh",
    #         "import_kW",
    #         "export_kW",
    # output_ds.timestamp = measurements_request.timestamp
    # initialize
    # output_ds.initial_SoC_bat_per = battery_specs.initial_SoC * 100
    output_ds.import_kW = 0
    output_ds.export_kW = 0
    output_ds.bat_energy_kWh = 0
    bat_initial_Energy_kWh = battery_specs.initial_SoC * battery_specs.bat_capacity_kWh
    bat_min_Energy_kWh = battery_specs.min_SoC * battery_specs.bat_capacity_kWh
    bat_max_Energy_kWh = battery_specs.max_SoC * battery_specs.bat_capacity_kWh
    output_ds.P_bat_kW = measurements_request.P_net_meas_kW - measurements_request.P_req_kW
    if output_ds.P_bat_kW > 0:
        output_ds.bat_energy_kWh = bat_initial_Energy_kWh - (
            battery_specs.dis_efficiency
            * output_ds.P_bat_kW
            * delta_T_h  # XXX should this not be devided by efficiency ?
        )
        output_ds.P_bat_kW = output_ds.P_bat_kW / battery_specs.dis_efficiency
    else:
        output_ds.bat_energy_kWh = (
            bat_initial_Energy_kWh - (output_ds.P_bat_kW * delta_T_h) / battery_specs.ch_efficiency
        )
        output_ds.P_bat_kW = output_ds.P_bat_kW * battery_specs.ch_efficiency
    # discharging
    if output_ds.P_bat_kW > 0:
        # act_ptcb = output_ds.P_bat_kW
        if abs(output_ds.P_bat_kW) >= battery_specs.P_dis_max_kW:
            output_ds.import_kW = output_ds.P_bat_kW - battery_specs.P_dis_max_kW
            output_ds.P_bat_kW = battery_specs.P_dis_max_kW
            output_ds.bat_energy_kWh = (
                bat_initial_Energy_kWh - battery_specs.dis_efficiency * battery_specs.P_dis_max_kW * delta_T_h
            )
        if output_ds.bat_energy_kWh >= bat_min_Energy_kWh:
            output_ds.import_kW = output_ds.import_kW + ((bat_min_Energy_kWh - output_ds.bat_energy_kWh) / delta_T_h)
            output_ds.P_bat_kW = output_ds.P_bat_kW - output_ds.import_kW

            output_ds.bat_energy_kWh = bat_min_Energy_kWh
        output_ds.P_bat_kW = float(output_ds.P_bat_kW)
    # charging
    if output_ds.P_bat_kW < 0:
        # act_ptcb = output_ds.P_bat_kW
        if (
            abs(output_ds.P_bat_kW) <= battery_specs.P_ch_max_kW
        ):  # XXX there should be a an efficiency modifier in here right?
            output_ds.export_kW = 0
        else:
            output_ds.export_kW = abs(output_ds.P_bat_kW) - battery_specs.P_ch_max_kW
            output_ds.P_bat_kW = -battery_specs.P_ch_max_kW
            output_ds.bat_energy_kWh = (
                bat_initial_Energy_kWh + (battery_specs.P_ch_max_kW * delta_T_h) / battery_specs.ch_efficiency
            )
        if output_ds.bat_energy_kWh > bat_max_Energy_kWh:
            output_ds.export_kW = output_ds.export_kW + ((output_ds.bat_energy_kWh - bat_max_Energy_kWh) / delta_T_h)
            output_ds.P_bat_kW = (
                output_ds.P_bat_kW + output_ds.export_kW
            )  # was -(abs(output_ds.P_bat_kW) - output_ds.export_kW) can be simplified
            output_ds.bat_energy_kWh = bat_max_Energy_kWh
        output_ds.P_bat_kW = float(output_ds.P_bat_kW)
    output_ds.SoC_bat_per = output_ds.bat_energy_kWh / battery_specs.bat_capacity_kWh * 100
    output_ds.P_net_meas_kW = measurements_request.P_net_meas_kW
    output_ds.P_net_after_kW = output_ds.import_kW - output_ds.export_kW
    output_ds.P_bat_kW = output_ds.P_bat_kW * -1  # charging: positiv, discharging: negativ
    return output_ds


def scheduling(P_load_gen: pd.Series, battery_specs: BatterySpecs, delta_T_h: float):
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
        datetime TimeDelta object (in day unit) representing time intervals of the forecast time series.

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
            "timestamp",
            "initial_SoC_bat_per",
            "SoC_bat_per",
            "P_net_before_kW",
            "P_net_after_kW",
            "P_bat_kW",
            "bat_energy_kWh",
            "import_kW",
            "export_kW",
        ],
        dtype=float,
    )

    # "P_net_before_kW",
    # "P_net_after_kW",
    # "P_bat_kW",
    # "SoC_bat",
    # "bat_energy_kWh",
    # "import_kW",
    # "export_kW",

    output_ds.import_kW = 0
    output_ds.export_kW = 0
    output_ds.bat_energy_kWh = 0
    bat_min_Energy_kWh = battery_specs.min_SoC * battery_specs.bat_capacity_kWh
    bat_max_Energy_kWh = battery_specs.max_SoC * battery_specs.bat_capacity_kWh
    bat_initial_Energy_kWh = battery_specs.initial_SoC * battery_specs.bat_capacity_kWh
    # Convert timedelta to float in terms of seconds

    output_ds.P_net_before_kW = P_load_gen.P_load_kW - P_load_gen.P_gen_kW

    output_ds.P_bat_kW = output_ds.P_net_before_kW  # same initially

    # Pure netto energy
    # discharging
    if output_ds.P_bat_kW > 0:
        output_ds.P_bat_kW = output_ds.P_bat_kW / battery_specs.dis_efficiency
        output_ds.bat_energy_kWh = bat_initial_Energy_kWh - (output_ds.P_bat_kW * delta_T_h)
    # charging
    else:
        output_ds.P_bat_kW = output_ds.P_bat_kW * battery_specs.ch_efficiency

        output_ds.bat_energy_kWh = bat_initial_Energy_kWh - (output_ds.P_bat_kW * delta_T_h)
    # Correct for limits of equipment
    # discharging
    if output_ds.P_bat_kW > 0:
        if abs(output_ds.P_bat_kW) >= battery_specs.P_dis_max_kW:
            output_ds.import_kW = output_ds.P_bat_kW - battery_specs.P_dis_max_kW
            output_ds.P_bat_kW = battery_specs.P_dis_max_kW
            output_ds.bat_energy_kWh = bat_initial_Energy_kWh - (
                battery_specs.dis_efficiency * battery_specs.P_dis_max_kW * delta_T_h
            )
        if output_ds.bat_energy_kWh < bat_min_Energy_kWh:
            output_ds.import_kW = output_ds.import_kW + ((bat_min_Energy_kWh - output_ds.bat_energy_kWh) / delta_T_h)
            output_ds.P_bat_kW = output_ds.P_bat_kW - output_ds.import_kW
            output_ds.bat_energy_kWh = bat_min_Energy_kWh
    # charging
    if output_ds.P_bat_kW < 0:
        if abs(output_ds.P_bat_kW) <= battery_specs.P_ch_max_kW:
            output_ds.export_kW = 0
        else:
            output_ds.export_kW = abs(output_ds.P_bat_kW) - battery_specs.P_ch_max_kW
            output_ds.P_bat_kW = -battery_specs.P_ch_max_kW
            output_ds.bat_energy_kWh = (
                bat_initial_Energy_kWh + (battery_specs.P_ch_max_kW * delta_T_h) / battery_specs.ch_efficiency
            )
        if output_ds.bat_energy_kWh > bat_max_Energy_kWh:
            output_ds.export_kW = output_ds.export_kW + ((output_ds.bat_energy_kWh - bat_max_Energy_kWh) / delta_T_h)
            output_ds.P_bat_kW = -(abs(output_ds.P_bat_kW) - (output_ds.export_kW))
            output_ds.bat_energy_kWh = bat_max_Energy_kWh
        output_ds.P_bat_kW = float(output_ds.P_bat_kW)

    output_ds.P_net_after_kW = -output_ds.export_kW + output_ds.import_kW
    output_ds.SoC_bat_per = (output_ds.bat_energy_kWh / battery_specs.bat_capacity_kWh) * 100
    output_ds.P_bat_kW = output_ds.P_bat_kW * -1  # charging: positiv, discharging: negativ

    return output_ds
