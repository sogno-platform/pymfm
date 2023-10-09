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


from typing import Dict, Optional, List, Union
import json
import pandas as pd
from pydantic import BaseModel as PydBaseModel, Field, ValidationError, validator
from datetime import datetime, timezone, timedelta
from enum import Enum
from astral.sun import sun
from astral.location import LocationInfo


def open_json(filename):
    """
    Open and load JSON data from a file.

    :param filename: The name of the JSON file to open.
    :return: Loaded JSON data as a Python dictionary or list.
    """
    # Open the JSON file in read mode
    with open(filename) as data_file:
        # Load and parse the JSON data
        data = json.load(data_file)

    # Return the loaded data as a Python dictionary or list
    return data


class BaseModel(PydBaseModel):
    """
    Base Pydantic model with configuration settings to allow population by field name.
    """

    class Config:
        allow_population_by_field_name = True


class StrEnum(str, Enum):
    """
    An enumeration class for representing string-based enums.
    """

    pass


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

    timestamp: datetime = Field(
        ..., alias="timestamp", description=" The timestamp of the data."
    )
    P_gen_kW: float = Field(
        ..., alias="P_gen_kW", description="The generated power in kilowatts (kW)."
    )
    P_load_kW: float = Field(
        ..., alias="P_load_kW", description="The load power in kilowatts (kW)."
    )


class GenerationAndLoad(BaseModel):
    """
    Pydantic model representing a collection of generation and load data.
    """

    pv_curtailment: Optional[float] = Field(
        None,
        alias="bulk",
        description="The photovoltaic (PV) curtailment value (optional).",
    )
    values: List[GenerationAndLoadValues] = Field(
        ..., alias="values", description="A list of generation and load data values."
    )


class MeasurementsRequest(BaseModel):
    """
    Pydantic model representing near (real) time measurement and request.
    """

    timestamp: datetime = Field(
        ..., alias="timestamp", description="The timestamp of the measurement and request."
    )
    P_req_kW: Optional[float] = Field(
        ...,
        alias="P_req_kW",
        description="The requested power in kilowatts (kW) (optional).",
    )
    delta_T_h: float = Field(
        ..., alias="delta_T_h", description="The time difference in hours (h)."
    )
    P_net_meas_kW: float = Field(
        ...,
        alias="P_net_meas_kW",
        description="The measured net power in kilowatts (kW).",
    )


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
        alias="initial_SoC",
        description="The initial state of charge of the battery (SoC) in percentage at uc_start.",
    )
    final_SoC: Optional[float] = Field(
        None,
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
        alias="min_SoC",
        description="The minimum state of charge of the battery in percentage.",
    )
    max_SoC: float = Field(
        ...,
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
        alias="ch_efficiency",
        description="The charging efficiency of the battery (default: 1.0).",
    )
    dis_efficiency: float = Field(
        default=1.0,
        alias="dis_efficiency",
        description="The discharging efficiency of the battery (default: 1.0).",
    )
    bat_capacity_kWs: float = (
        0.0  # The capacity of the battery assets in kilowatt-seconds (kWs).
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
    uc_start: datetime = Field(
        ...,
        alias="uc_start",
        description="The start datetime of the control operation.",
    )
    uc_end: datetime = Field(
        ..., alias="uc_end", description="The end datetime of the control operation."
    )
    generation_and_load: Optional[GenerationAndLoad] = Field(
        None,
        alias="generation_and_load",
        description="Generation and load data (optional).",
    )
    day_end: Optional[datetime] = Field(
        None,
        alias="day_end",
        description="The end of the sunlight for the day timestamp (optional).",
    )
    bulk: Optional[Bulk] = Field(
        None, alias="bulk", description="Bulk energy data (optional)."
    )
    P_net_after_kW_limitation: Optional[List[P_net_after_kWLimitation]] = Field(
        None,
        alias="P_net_after_kW_limitation",
        description="P_net_after limitations (optional).",
    )
    measurements_request: Optional[MeasurementsRequest] = Field(
        None,
        alias="measurements_request",
        description="Measurements request data (optional).",
    )
    battery_specs: Union[BatterySpecs, List[BatterySpecs]]  # Battery specifications.

    @validator("generation_and_load")
    def generation_and_load_start_before_timewindow(cls, meas, values):
        """
        Validator to ensure generation_and_load starts before or at uc_start.

        :param meas: The value of generation_and_load.
        :param values: The values dictionary.
        :return: The validated value.
        """
        uc_start = values["uc_start"]
        # Check if generation_and_load starts before or at uc_start
        if uc_start < meas.values[0].timestamp:
            raise ValueError(
                f"generation_and_load have to start at or before uc_start. generation_and_load start at {meas.values[0].timestamp} uc_start was {uc_start}"
            )
        return meas

    @validator("generation_and_load")
    def generation_and_load_end_after_timewindow(cls, meas : dict , values : dict) -> dict:
        
        """
        Validator to ensure generation_and_load ends after or at uc_end.

        :param meas: The value of generation_and_load.
        :param values: The values dictionary.
        :return: The validated value
        """
        uc_end = values["uc_end"]
        # Check if generation_and_load ends after or at uc_end
        if uc_end > meas.values[-1].timestamp:
            raise ValueError(
                f"generation_and_load have to end at or after uc_end. generation_and_load end at {meas.values[-1].timestamp} uc_end was {uc_end}"
            )
        return meas

    @validator("day_end", always=True)
    def set_day_end(cls, v, values):
        """
        Validator to set day_end if not provided, based on sunset time in Berlin.

        :param v: The value of day_end.
        :param values: The values dictionary.
        :return: The validated value.
        """
        generation_and_load = values.get("generation_and_load")

        # Check if day_end is not provided
        if v is None:
            # Calculate the sunset time for uc_start date and location (Berlin)
            berlin_location = LocationInfo(
                "Berlin", "Germany", "Europe/Berlin", 52.52, 13.40
            )
            s = sun(berlin_location.observer, date=values["uc_start"].date())

            # Set day_end to the sunset time
            sunset_time = s["sunset"].astimezone(timezone.utc)

            if generation_and_load and isinstance(
                generation_and_load, GenerationAndLoad
            ):
                timestamps = [
                    data_point.timestamp for data_point in generation_and_load.values
                ]
                # Find the nearest timestamp in generation_and_load data to sunset_time
                nearest_timestamp = min(timestamps, key=lambda t: abs(t - sunset_time))
                return nearest_timestamp
            return v
        else:
            return v


def minutes_horizon(starttime: datetime, endtime: datetime) -> float:
    """Calculate the time horizon in minutes between two timestamps.

    Parameters
    ----------
    starttime : datetime
        The start timestamp
    endtime : datetime
        The end timestamp.

    Returns
    -------
    float
        The time horizon in minutes.
    """
    # Calculate the time difference in seconds and convert to minutes
    time_delta = endtime - starttime
    total_seconds = time_delta.total_seconds()
    minutes = total_seconds / 60
    return minutes


def input_prep(battery_specs: Union[BatterySpecs, List[BatterySpecs]]):
    """
    Prepare battery specifications by transforming battery percentages to absolute values
    and saving battery capacity also in kWs.

    :param battery_specs: Battery specifications.
    :return: Updated battery specifications.
    """
    # Transform battery percentage values to absolute values and calculate capacity in kWs
    if isinstance(battery_specs, list):
        for battery in battery_specs:
            # Transform battery percent to absolute
            battery.min_SoC /= 100
            battery.max_SoC /= 100
            battery.initial_SoC /= 100
            if battery.final_SoC is not None:
                battery.final_SoC /= 100
            battery.bat_capacity_kWs = battery.bat_capacity_kWh * 3600
    else:
        # Transform battery percent to absolute
        battery_specs.min_SoC /= 100
        battery_specs.max_SoC /= 100
        battery_specs.initial_SoC /= 100
        battery_specs.final_SoC /= 100
        battery_specs.bat_capacity_kWs = battery_specs.bat_capacity_kWh * 3600

    return battery_specs


def generation_and_load_to_df(
    meas: GenerationAndLoad, start: datetime = None, end: datetime = None
) -> pd.DataFrame:
    """Convert generation and load data to a DataFrame within a specified time range.

    Parameters
    ----------
    meas : GenerationAndLoad
        Generation and load data.
    start : datetime, optional
        Start timestamp for filtering data, by default None
    end : datetime, optional
        End timestamp for filtering data, by default None

    Returns
    -------
    pd.DataFrame
        containing filtered generation and load data.
    """    
    # Convert GenerationAndLoad objects to a DataFrame, set index to timestamp, and filter by time range
    df_forecasts = pd.json_normalize([mes.dict(by_alias=False) for mes in meas.values])
    df_forecasts.set_index("timestamp", inplace=True)
    df_forecasts.index.freq = pd.infer_freq(df_forecasts.index)
    df_forecasts = df_forecasts.loc[start:end]
    return df_forecasts


def battery_to_df(
    battery_specs: Union[BatterySpecs, List[BatterySpecs]]
) -> pd.DataFrame:
    """
    Convert battery specifications to a DataFrame.

    :param battery_specs: Battery specifications.
    :return: DataFrame containing battery specifications.
    """
    # Convert BatterySpecs objects to a DataFrame, set index to 'id' if available
    if isinstance(battery_specs, list):
        df_battery = pd.json_normalize(
            [battery.dict(by_alias=False) for battery in battery_specs]
        )
    else:
        df_battery = pd.json_normalize(battery_specs.dict(by_alias=False))

    if ~df_battery.id.isna().any():
        df_battery.set_index("id", inplace=True)  # Set index to 'id' if available

    return df_battery


def measurements_request_to_dict(measurements_request: MeasurementsRequest):
    """
    Convert measurements request to a dictionary.

    :param measurements_request: Measurements and request.
    :return: Dictionary containing measurements and request data.
    """
    # Convert MeasurementsRequest object to a dictionary
    measurements_request_dict = {
        "timestamp": measurements_request.timestamp,
        "P_req_kW": measurements_request.P_req_kW,
        "delta_T_h": measurements_request.delta_T_h,
        "P_net_meas_kW": measurements_request.P_net_meas_kW,
    }
    return measurements_request_dict


def P_net_after_kW_lim_to_df(
    P_net_after_kW_limits: List[P_net_after_kWLimitation],
    gen_load_data: List[GenerationAndLoad],
) -> pd.DataFrame:
    """Convert P_net_after_kWLimitation data (upper and lower bouns of microgrid power) to a DataFrame.

    Parameters
    ----------
    P_net_after_kW_limits : List[P_net_after_kWLimitation]
        List of P_net_after_kWLimitation objects.
    gen_load_data : List[GenerationAndLoad]
        List of GenerationAndLoad objects.

    Returns
    -------
    pd.DataFrame
        containing P_net_after_kWLimitation data
    """    
    # Check if P_net_after_kW_limits is None
    if P_net_after_kW_limits is None:
        # Create a DataFrame with default values and use timestamps from gen_load_data
        all_timestamps = set(item.timestamp for item in gen_load_data.values)
        missing_data = pd.DataFrame(
            {
                "upper_bound": [0] * len(all_timestamps),
                "with_upper_bound": [False] * len(all_timestamps),
                "lower_bound": [0] * len(all_timestamps),
                "with_lower_bound": [False] * len(all_timestamps),
            },
            index=list(all_timestamps),
        )
        missing_data.index.name = "timestamp"  # Set the index name
        return missing_data

    # Convert the list of P_net_after_kWLimitation objects to a DataFrame
    df = pd.DataFrame([item.dict() for item in P_net_after_kW_limits])
    df.set_index("timestamp", inplace=True)

    # Adding new columns and filling default values
    df["with_upper_bound"] = df["upper_bound"].notnull()
    df["with_lower_bound"] = df["lower_bound"].notnull()
    df.fillna(0, inplace=True)

    # Handle timestamps not present in P_net_after_kWLimitation but in generation_and_load
    all_timestamps = set(df.index).union(
        set(item.timestamp for item in gen_load_data.values)
    )
    missing_timestamps = list(set(all_timestamps).difference(df.index))
    missing_data = pd.DataFrame(
        {
            "upper_bound": [0] * len(missing_timestamps),
            "with_upper_bound": [False] * len(missing_timestamps),
            "lower_bound": [0] * len(missing_timestamps),
            "with_lower_bound": [False] * len(missing_timestamps),
        },
        index=missing_timestamps,
    )

    # Concatenate the two DataFrames
    result_df = pd.concat([df, missing_data.astype(int)], axis=0)
    result_df.index.name = "timestamp"  # Set the index name

    return result_df
