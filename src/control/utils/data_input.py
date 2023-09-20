from typing import Optional, List
import pandas as pd
from pydantic import BaseModel as PydBaseModel, Field, ValidationError, validator
from datetime import datetime, timezone, timedelta
from enum import Enum
from astral.sun import sun
from astral.location import LocationInfo


class BaseModel(PydBaseModel):
    class Config:
        allow_population_by_field_name = True


class StrEnum(str, Enum):
    pass


class ControlLogic(StrEnum):
    RULE_BASED = "rule_based"
    OPTIMIZATION_BASED = "optimization_based"


class OperationMode(StrEnum):
    NEAR_REAL_TIME = "near_real_time"
    SCHEDULING = "scheduling"


class Bulk(BaseModel):
    bulk_start: datetime = Field(..., alias="bulk_start")
    bulk_end: datetime = Field(..., alias="bulk_end")
    bulk_energy_kWh: float = Field(..., alias="bulk_energy_kWh")


class P_net_after_kWLimitation(BaseModel):
    timestamp: datetime = Field(..., alias="timestamp")
    upper_bound: Optional[float] = Field(None, alias="upper_bound")
    lower_bound: Optional[float] = Field(None, alias="lower_bound")


class GenerationAndLoadValues(BaseModel):
    timestamp: datetime = Field(..., alias="timestamp")
    P_gen_kW: float = Field(..., alias="P_gen_kW")
    P_load_kW: float = Field(..., alias="P_load_kW")


class GenerationAndLoad(BaseModel):
    pv_curtailment: Optional[float] = Field(None, alias="bulk")
    values: List[GenerationAndLoadValues] = Field(..., alias="values")


class MeasurementsRequest(BaseModel):
    timestamp: datetime = Field(..., alias="timestamp")
    P_req_kW: Optional[float] = Field(..., alias="P_req_kW")
    delta_T_h: float = Field(..., alias="delta_T_h")
    P_net_meas_kW: float = Field(..., alias="P_net_meas_kW")


class BatterySpecs(BaseModel):
    id: Optional[str]
    bat_type: str = Field(
        ...,
        alias="bat_type",
        description="The type of the battery. cbes: comunity battery energy storage, hbes: household battery energy storage",
    )
    initial_SoC: float = Field(
        ...,
        alias="initial_SoC",
        description="initial state of charge of the battery (SoC) in percentage at uc_start",
    )
    final_SoC: Optional[float] = Field(
        None,
        alias="final_SoC",
        description="Final state of charge of the battery (SoC) in percentage at UC_en",
    )
    P_dis_max_kW: float = Field(
        ..., alias="P_dis_max_kW", description="Max dischargable power in kW"
    )
    P_ch_max_kW: float = Field(
        ..., alias="P_ch_max_kW", description="Max chargable power in kW"
    )
    min_SoC: float = Field(
        ...,
        alias="min_SoC",
        description="Minimum state of charge of the battery in percentage",
    )
    max_SoC: float = Field(
        ...,
        alias="max_SoC",
        description="Maximum state of charge of the battery in percentage",
    )
    bat_capacity_kWh: float = Field(
        ...,
        alias="bat_capacity_kWh",
        description="Full capacity of battery assets (100% SoC) in kWh",
    )
    ch_efficiency: float = Field(default=1.0, alias="ch_efficiency")
    dis_efficiency: float = Field(default=1.0, alias="dis_efficiency")
    bat_capacity_kWs: float = 0.0


class InputData(BaseModel):
    id: str
    application: str
    control_logic: ControlLogic = Field(..., alias="control_logic")
    operation_mode: OperationMode = Field(..., alias="operation_mode")
    uc_start: datetime = Field(..., alias="uc_start")
    uc_end: datetime = Field(..., alias="uc_end")
    generation_and_load: Optional[GenerationAndLoad] = Field(
        None, alias="generation_and_load"
    )
    day_end: Optional[datetime] = Field(None, alias="day_end")
    bulk: Optional[Bulk] = Field(None, alias="bulk")
    P_net_after_kW_limitation: Optional[List[P_net_after_kWLimitation]] = Field(
        None, alias="P_net_after_kW_limitation"
    )
    measurements_request: Optional[MeasurementsRequest] = Field(
        None, alias="measurements_request"
    )
    battery_specs: BatterySpecs | list[BatterySpecs]

    @validator("generation_and_load")
    def generation_and_load_start_before_timewindow(cls, meas, values):
        """
        Validator to ensure generation_and_load starts before or at uc_start.

        :param meas: The value of generation_and_load.
        :param values: The values dictionary.
        :return: The validated value.
        """
        uc_start = values["uc_start"]
        if uc_start < meas.values[0].timestamp:
            raise ValueError(
                f"generation_and_load have to start at or before uc_start. generation_and_load start at {meas.values[0].timestamp} uc_start was {uc_start}"
            )
        return meas

    @validator("generation_and_load")
    def generation_and_load_end_after_timewindow(cls, meas, values):
        """
        Validator to ensure generation_and_load ends after or at uc_end.

        :param meas: The value of generation_and_load.
        :param values: The values dictionary.
        :return: The validated value.
        """
        uc_end = values["uc_end"]
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
                nearest_timestamp = min(timestamps, key=lambda t: abs(t - sunset_time))
                return nearest_timestamp
            return v
        else:
            return v


def minutes_horizon(starttime: datetime, endtime: datetime) -> float:
    """
    Calculate the time horizon in minutes between two timestamps.

    :param starttime: The start timestamp.
    :param endtime: The end timestamp.
    :return: The time horizon in minutes.
    """
    time_delta = endtime - starttime
    total_seconds = time_delta.total_seconds()
    minutes = total_seconds / 60
    return minutes


def input_prep(battery_specs: BatterySpecs | list[BatterySpecs]):
    """
    Prepare battery specifications by transforming battery percentages to absolute values and saving battery capacity also in kWs.

    :param battery_specs: Battery specifications.
    :return: Updated battery specifications.
    """
    # Transform battery percent to abs
    if isinstance(battery_specs, list):
        for battery in battery_specs:
            # Transform battery percent to abs
            battery.min_SoC /= 100
            battery.max_SoC /= 100
            battery.initial_SoC /= 100
            if battery.final_SoC is not None:
                battery.final_SoC /= 100
            battery.bat_capacity_kWs = battery.bat_capacity_kWh * 3600

    else:
        # Transform battery percent to abs
        battery_specs.min_SoC /= 100
        battery_specs.max_SoC /= 100
        battery_specs.initial_SoC /= 100
        battery_specs.final_SoC /= 100
        battery_specs.bat_capacity_kWs = battery_specs.bat_capacity_kWh * 3600

    return battery_specs


def generation_and_load_to_df(
    meas: dict[GenerationAndLoad], start: datetime = None, end: datetime = None
) -> pd.DataFrame:
    """
    Convert generation and load data to a DataFrame within a specified time range.

    :param meas: Generation and load data.
    :param start: Start timestamp for filtering data.
    :param end: End timestamp for filtering data.
    :return: DataFrame containing filtered generation and load data.
    """
    df_forecasts = pd.json_normalize([mes.dict(by_alias=False) for mes in meas.values])
    df_forecasts.set_index("timestamp", inplace=True)
    df_forecasts.index.freq = pd.infer_freq(df_forecasts.index)
    df_forecasts = df_forecasts.loc[start:end]
    return df_forecasts


def battery_to_df(battery_specs: BatterySpecs | list[BatterySpecs]) -> pd.DataFrame:
    """
    Convert battery specifications to a DataFrame.

    :param battery_specs: Battery specifications.
    :return: DataFrame containing battery specifications.
    """
    if isinstance(battery_specs, list):
        df_battery = pd.json_normalize(
            [battery.dict(by_alias=False) for battery in battery_specs]
        )

    else:
        df_battery = pd.json_normalize(battery_specs.dict(by_alias=False))

    # Set index to ids if all battery nodes have an id, otherwise leave rangeindex
    if ~df_battery.id.isna().any():
        df_battery.set_index("id", inplace=True)
    return df_battery


def measurements_request_to_dict(measurements_request: MeasurementsRequest):
    """
    Convert measurements request to a dictionary.

    :param measurements_request: Measurements request.
    :return: Dictionary containing measurements request data.
    """
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
    """
    Convert P_net_after_kWLimitation data to a DataFrame.

    :param P_net_after_kW_limits: List of P_net_after_kWLimitation objects.
    :param gen_load_data: List of GenerationAndLoad objects.
    :return: DataFrame containing P_net_after_kWLimitation data.
    """
    # Check if upper_bounds, lower_bounds are None
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
            index=list(all_timestamps),  # Convert set to list
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


class Solver(StrEnum):
    GUROBI = "gurobi"
    IPOPT = "ipopt"


class OptimizationJob(BaseModel):
    created: datetime
    solver: Solver
    data: InputData
