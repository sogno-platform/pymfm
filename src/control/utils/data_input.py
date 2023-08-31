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


class ControlMethod(StrEnum):
    RULE_BASED = "rule_based_scheduling"
    OPTIMIZER = "optimizer"
    REAL_TIME = "near-real-time"


class Bulk(BaseModel):
    bulk_start: datetime = Field(..., alias="bulk_start")
    bulk_end: datetime = Field(..., alias="bulk_end")
    bulk_energy_kwh: float = Field(..., alias="bulk_energy_kWh")


class ImportExportLimitation(BaseModel):
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


# TODO add constraints
# - initial_SoC and final_SoC should always be in the acceptable range, i.e., between min_SoC and max_SoC
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
    final_SoC: float = Field(
        ...,
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
    bat_capacity: float = Field(
        ...,
        alias="bat_capacity",
        description="Full capacity of battery assets (100% SoC) in kWh",
    )
    ch_efficiency: float = Field(default=1.0, alias="ch_efficiency")
    dis_efficiency: float = Field(default=1.0, alias="dis_efficiency")


class InputData(BaseModel):
    application: str
    uc_name: ControlMethod = Field(..., alias="uc_name")
    uc_start: datetime = Field(..., alias="uc_start")
    uc_end: datetime = Field(..., alias="uc_end")
    generation_and_load: GenerationAndLoad = Field(..., alias="generation_and_load")
    #day_end: datetime = Field(..., alias="day_end")
    day_end: Optional[datetime] = Field(None, alias="day_end")
    bulk: Optional[Bulk] = Field(None, alias="bulk")
    import_export_limitation: Optional[List[ImportExportLimitation]] = Field(
        None, alias="import_export_limitation"
    )
    battery_specs: BatterySpecs | list[BatterySpecs]

    @validator("uc_name", pre=True)
    def uc_name_to_enum(cls, value: str) -> str:
        if value.lower() == "optimiser":
            return "optimizer"
        return value

    @validator("generation_and_load")
    def generation_and_load_start_before_timewindow(cls, meas, values):
        uc_start = values["uc_start"]
        if uc_start < meas.values[0].timestamp:
            raise ValueError(
                f"generation_and_load have to start at or before uc_start. generation_and_load start at {meas.values[0].timestamp} uc_start was {uc_start}"
            )
        return meas

    @validator("generation_and_load")
    def generation_and_load_end_after_timewindow(cls, meas, values):
        uc_end = values["uc_end"]
        if uc_end > meas.values[-1].timestamp:
            raise ValueError(
                f"generation_and_load have to end at or after uc_end. generation_and_load end at {meas.values[-1].timestamp} uc_end was {uc_end}"
            )
        return meas

    @validator("day_end", always=True)
    def set_day_end(cls, v, values):
        generation_and_load = values.get("generation_and_load")
        if v is None:
            # Calculate the sunset time for uc_start date and location (Berlin)
            berlin_location = LocationInfo("Berlin", "Germany", "Europe/Berlin", 52.52, 13.40)
            s = sun(berlin_location.observer, date=values["uc_start"].date())
            # Set day_end to the sunset time
            sunset_time = s["sunset"].astimezone(timezone.utc)
            if generation_and_load and isinstance(generation_and_load, GenerationAndLoad):
                timestamps = [data_point.timestamp for data_point in generation_and_load.values]
                nearest_timestamp = min(timestamps, key=lambda t: abs(t - sunset_time))
                return nearest_timestamp
            return v

def minutes_horizon(starttime: datetime, endtime: datetime) -> float:
    time_delta = endtime - starttime
    total_seconds = time_delta.total_seconds()
    minutes = total_seconds / 60
    return minutes


def input_prep(battery_specs: BatterySpecs | list[BatterySpecs]):
    # Transform battery percent to abs
    if isinstance(battery_specs, list):
        for battery in battery_specs:
            # Transform battery percent to abs
            battery.min_SoC /= 100
            battery.max_SoC /= 100
            battery.initial_SoC /= 100
            battery.final_SoC /= 100
            battery.bat_capacity *= 3600

    else:
        # Transform battery percent to abs
        battery_specs.min_SoC /= 100
        battery_specs.max_SoC /= 100
        battery_specs.initial_SoC /= 100
        battery_specs.final_SoC /= 100
        battery_specs.bat_capacity *= 3600
        
    return battery_specs


def generation_and_load_to_df(
    meas: dict[GenerationAndLoad], start: datetime = None, end: datetime = None
) -> pd.DataFrame:
    df_forecasts = pd.json_normalize([mes.dict(by_alias=False) for mes in meas.values])
    df_forecasts.set_index("timestamp", inplace=True)
    df_forecasts.index.freq = pd.infer_freq(df_forecasts.index)
    df_forecasts = df_forecasts.loc[start:end]
    return df_forecasts


def battery_to_df(battery_specs: BatterySpecs | list[BatterySpecs]) -> pd.DataFrame:
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


def imp_exp_to_df(
    meas: list[ImportExportLimitation], start: datetime = None, end: datetime = None
) -> pd.DataFrame:
    df_imp_exp = pd.json_normalize([mes.dict(by_alias=False) for mes in meas])
    df_imp_exp.set_index("timestamp", inplace=True)
    df_imp_exp.index.freq = pd.infer_freq(df_imp_exp.index)
    df_imp_exp = df_imp_exp.loc[start:end]
    return df_imp_exp


def imp_exp_lim_to_df(
    import_export_limits: List[ImportExportLimitation],
    gen_load_data: List[GenerationAndLoad],
) -> pd.DataFrame:
    # Check if upper_bounds, lower_bounds are None
    if import_export_limits is None:
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

    # Convert the list of ImportExportLimitation objects to a DataFrame
    df = pd.DataFrame([item.dict() for item in import_export_limits])
    df.set_index("timestamp", inplace=True)

    # Adding new columns and filling default values
    df["with_upper_bound"] = df["upper_bound"].notnull()
    df["with_lower_bound"] = df["lower_bound"].notnull()
    df.fillna(0, inplace=True)

    # Handle timestamps not present in ImportExportLimitation but in generation_and_load
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
