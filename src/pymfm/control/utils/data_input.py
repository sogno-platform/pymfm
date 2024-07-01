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


import json
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Union

import pandas as pd
from astral.location import LocationInfo
from astral.sun import sun
from pydantic import Field, field_validator

from pymfm.control.utils.common import BaseModel, StrEnum


class ControlLogic(StrEnum):
    """
    An enumeration class representing control logic options.
    """

    RULE_BASED = "rule_based"  # Rule-based control logic.
    OPTIMIZATION_BASED = "optimization_based"  # Optimization-based control logic.


class OperationMode(StrEnum):
    """
    An enumeration class representing operation mode options.
    """

    NEAR_REAL_TIME = "near_real_time"  # Near real-time operation mode.
    SCHEDULING = "scheduling"  # Scheduling operation mode.


class Bulk(BaseModel):
    """
    Pydantic model representing bulk energy data.
    """

    bulk_start: datetime = Field(
        ...,
        alias="bulk_start",
        description="The start datetime of the bulk energy operation.",
    )
    bulk_end: datetime = Field(
        ...,
        alias="bulk_end",
        description="The end datetime of the bulk energy operation.",
    )
    bulk_energy_kWh: float = Field(
        ...,
        alias="bulk_energy_kWh",
        description="The bulk energy in kilowatt-hours (kWh).",
    )


class P_net_after_kWLimitation(BaseModel):
    """
    Pydantic model representing P_net_after limitations.
    """

    timestamp: datetime = Field(
        ...,
        alias="timestamp",
        description="The timestamp when the limitation is applied.",
    )
    upper_bound: Optional[float] = Field(
        None,
        alias="upper_bound",
        description="The upper bound value for P_net_after (optional).",
    )
    lower_bound: Optional[float] = Field(
        None,
        alias="lower_bound",
        description="The lower bound value for P_net_after (optional).",
    )


class GenerationAndLoadValues(BaseModel):
    """
    Pydantic model representing generation and load forecast data at a specific timestamp.
    """

    timestamp: datetime = Field(..., alias="timestamp", description=" The timestamp of the data.")
    P_available_kW: float = Field(
        ...,
        alias="P_available_kW",
        description="The generated power in kilowatts (kW).",
    )
    P_required_kW: float = Field(..., alias="P_required_kW", description="The load power in kilowatts (kW).")


class GenerationAndLoad(BaseModel):
    """
    Pydantic model representing a collection of generation and load data.
    """

    pv_curtailment: bool = Field(
        False,
        alias="bulk",
        description="The photovoltaic (PV) curtailment value (optional).",
    )
    values: List[GenerationAndLoadValues] = Field(
        ..., alias="values", description="A list of generation and load data values."
    )
    delta_T_h: Optional[float] = Field(None, alias="delta_T_h", description="The time difference in hours (h).")


class BatterySpecs(BaseModel):
    """
    Pydantic model representing battery specifications consisting of:
    String values of battery "type" and "id" and Float values of initital SoC in %,
    maximum charging and discharging powers in kW, min and max SoC in %, battery capacity in kWh,
    and (dis)charging efficiency (0<efficiency<=1)
    """

    id: Optional[str]  # The unique identifier for the battery (optional).
    bat_type: str = Field(
        ...,
        alias="bat_type",
        description="The type of the battery. Can be 'cbes' (community battery energy storage) or 'hbes' (household battery energy storage).",
    )
    initial_SoC: float = Field(
        ...,
        le=1.0,
        ge=0.0,
        alias="initial_SoC",
        description="The initial state of charge of the battery (SoC) in percentage at control_start.",
    )
    final_SoC: Optional[float] = Field(
        None,
        le=1.0,
        ge=0.0,
        alias="final_SoC",
        description="The final state of charge of the battery (SoC) in percentage at uc_end (optional).",
    )
    P_dis_max_kW: float = Field(
        ...,
        alias="P_dis_max_kW",
        description="The maximum dischargable power of the battery in kilowatts (kW).",
    )
    P_ch_max_kW: float = Field(
        ...,
        alias="P_ch_max_kW",
        description="The maximum chargable power of the battery in kilowatts (kW).",
    )
    min_SoC: float = Field(
        ...,
        le=1.0,
        ge=0.0,
        alias="min_SoC",
        description="The minimum state of charge of the battery in percentage.",
    )
    max_SoC: float = Field(
        ...,
        le=1.0,
        ge=0.0,
        alias="max_SoC",
        description="The maximum state of charge of the battery in percentage.",
    )
    bat_capacity_kWh: float = Field(
        ...,
        alias="bat_capacity_kWh",
        description="The full capacity of battery assets (100% SoC) in kilowatt-hours (kWh).",
    )
    ch_efficiency: float = Field(
        default=1.0,
        le=1.0,
        ge=0.0,
        alias="ch_efficiency",
        description="The charging efficiency of the battery (default: 1.0).",
    )
    dis_efficiency: float = Field(
        default=1.0,
        le=1.0,
        ge=0.0,
        alias="dis_efficiency",
        description="The discharging efficiency of the battery (default: 1.0).",
    )


class InputData(BaseModel):
    """
    Pydantic model representing input data for each use case including control logic,
    operation mode, use case start and end time, load and generation forecast, day end time,
    bulk window, power boundaries, measurement and requested powers, and battery specifications.
    """

    id: str  # The unique identifier for the input data.
    application: str  # The application name.
    control_logic: ControlLogic = Field(
        ...,
        alias="control_logic",
        description="The control logic used for decision-making.",
    )
    operation_mode: OperationMode = Field(
        ..., alias="operation_mode", description="The operation mode of the controller."
    )
    control_start: Optional[datetime] = Field(
        None,
        alias="control_start",
        description="The start datetime of the control operation.",
    )
    control_end: Optional[datetime] = Field(None, alias="control_end", description="The end datetime of the control operation.")
    job_start: Optional[datetime] = Field(
        None,
        alias="job_start",
        description="The start datetime when the job is executed for the first time.",
    )
    job_end: Optional[datetime] = Field(
        None, alias="job_end", description="The end datetime after which no update on the control schedule is done."
    )
    repeat_seconds: Optional[float] = None
    generation_and_load: GenerationAndLoad = Field(
        ...,
        alias="generation_and_load",
        description="Generation and load data (optional).",
    )
    day_end: Optional[datetime] = Field(
        None,
        alias="day_end",
        description="The end of the sunlight for the day timestamp (optional).",
    )
    bulk: Optional[Bulk] = Field(None, alias="bulk", description="Bulk energy data (optional).")
    P_net_after_kW_limitation: Optional[List[P_net_after_kWLimitation]] = Field(
        None,
        alias="P_net_after_kW_limitation",
        description="P_net_after limitations (optional).",
    )
    battery_specs: Union[BatterySpecs, List[BatterySpecs]]  # Battery specifications.

    # TODO rethink validation
    # @validator("generation_and_load")
    # def generation_and_load_start_before_timewindow(cls, meas, values):
    #     """
    #     Validator to ensure generation_and_load starts before or at control_start.

    #     :param meas: The value of generation_and_load.
    #     :param values: The values dictionary.
    #     :return: The validated value.
    #     """
    #     control_start = values["control_start"]
    #     # Check if generation_and_load starts before or at control_start
    #     if control_start < meas.values[0].timestamp:
    #         raise ValueError(
    #             f"generation_and_load have to start at or before control_start. generation_and_load start at {meas.values[0].timestamp} control_start was {control_start}"
    #         )
    #     return meas

    # @validator("generation_and_load")
    # def generation_and_load_end_after_timewindow(cls, meas: dict, values: dict) -> dict:
    #     """
    #     Validator to ensure generation_and_load ends after or at uc_end.

    #     :param meas: The value of generation_and_load.
    #     :param values: The values dictionary.
    #     :return: The validated value
    #     """
    #     uc_end = values["uc_end"]
    #     # Check if generation_and_load ends after or at uc_end
    #     if uc_end > meas.values[-1].timestamp:
    #         raise ValueError(
    #             f"generation_and_load have to end at or after uc_end. generation_and_load end at {meas.values[-1].timestamp} uc_end was {uc_end}"
    #         )
    #     return meas

    @field_validator("day_end")
    def set_day_end(cls, v, values):
        """
        Validator to set day_end if not provided, based on sunset time in Berlin.

        :param v: The value of day_end.
        :param values: The values dictionary.
        :return: The validated value.
        """
        generation_and_load = values.data.get("generation_and_load")

        # Check if day_end is not provided
        if v is not None:
            return v
        # Calculate the sunset time for control_start date and location (Berlin)
        berlin_location = LocationInfo("Berlin", "Germany", "Europe/Berlin", 52.52, 13.40)
        s = sun(berlin_location.observer, date=values.data["control_start"].date())

        # Set day_end to the sunset time
        sunset_time = s["sunset"].astimezone(timezone.utc)

        if generation_and_load and isinstance(generation_and_load, GenerationAndLoad):
            timestamps = [data_point.timestamp for data_point in generation_and_load.values]
            # Find the nearest timestamp in generation_and_load data to sunset_time
            nearest_timestamp = min(timestamps, key=lambda t: abs(t - sunset_time))
            return nearest_timestamp
        return v
