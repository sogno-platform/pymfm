# The pymfm framework
#
# Copyright (C) 2023, Institute for Automation of Complex Power Systems (ACS),
# E.ON Energy Research Center (E.ON ERC), RWTH Aachen University
#
# Licensed under the Apache License, Version 2.0 (the "License").

from datetime import datetime, timezone
from typing import List, Optional, Union

from astral import LocationInfo
from astral.sun import sun
from pydantic import Field, field_validator

from pymfm.control.utils.common import BaseModel, StrEnum
from pymfm.config import settings


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


class BatteryType(StrEnum):
    """Community battery energy storage vs. household battery energy storage."""
    CBES = "cbes"
    HBES = "hbes"


class Bulk(BaseModel):
    """
    Pydantic model representing bulk energy data.
    """

    bulk_start: datetime = Field(..., description="Start of the bulk energy operation.")
    bulk_end: datetime = Field(..., description="End of the bulk energy operation.")
    bulk_energy_kWh: float = Field(..., description="Bulk energy in kilowatt-hours (kWh).")


class PowerBoundEntry(BaseModel):
    """
    Pydantic model representing P_net_after limitations.
    """

    timestamp: datetime = Field(..., description="Timestamp at which the bound applies.")
    upper_bound: Optional[float] = Field(None, description="Upper bound for P_net_after (kW).")
    lower_bound: Optional[float] = Field(None, description="Lower bound for P_net_after (kW).")


class GenerationAndLoadValues(BaseModel):
    """
    Pydantic model representing generation and load forecast data at a specific timestamp.
    """

    timestamp: datetime = Field(..., description="Timestamp of the data point.")
    P_available_kW: float = Field(..., description="Available generation power (kW).")
    P_required_kW: float = Field(..., description="Required load power (kW).")


class GenerationAndLoad(BaseModel):
    """
    Pydantic model representing a collection of generation and load data.
    """

    pv_curtailment: bool = Field(False, description="Allow PV curtailment.")
    values: List[GenerationAndLoadValues] = Field(..., description="Forecast time series.")
    delta_T_h: Optional[float] = Field(None, description="Time step in hours.")


class BatterySpecs(BaseModel):
    """
    Pydantic model representing battery specifications consisting of:
    String values of battery "type" and "id" and Float values of initital SoC in %,
    maximum charging and discharging powers in kW, min and max SoC in %, battery capacity in kWh,
    and (dis)charging efficiency (0<efficiency<=1)
    """

    id: Optional[str] = Field(None, description="Unique identifier (optional).")
    bat_type: BatteryType = Field(..., description="'cbes' or 'hbes'.")
    initial_SoC: float = Field(..., ge=0.0, le=1.0, description="Initial state of charge [0–1].")
    final_SoC: Optional[float] = Field(None, ge=0.0, le=1.0, description="Desired final SoC [0–1] (optional).")
    P_dis_max_kW: float = Field(..., description="Maximum discharging power (kW).")
    P_ch_max_kW: float = Field(..., description="Maximum charging power (kW).")
    min_SoC: float = Field(..., ge=0.0, le=1.0, description="Minimum allowable SoC [0–1].")
    max_SoC: float = Field(..., ge=0.0, le=1.0, description="Maximum allowable SoC [0–1].")
    bat_capacity_kWh: float = Field(..., description="Full capacity at 100 % SoC (kWh).")
    ch_efficiency: float = Field(default=1.0, ge=0.0, le=1.0, description="Charging efficiency.")
    dis_efficiency: float = Field(default=1.0, ge=0.0, le=1.0, description="Discharging efficiency.")


class InputData(BaseModel):
    """
    Pydantic model representing input data for each use case including control logic,
    operation mode, use case start and end time, load and generation forecast, day end time,
    bulk window, power boundaries, measurement and requested powers, and battery specifications.
    """

    id: str
    application: str
    control_logic: ControlLogic = Field(..., description="Rule-based or optimisation-based.")
    operation_mode: OperationMode = Field(..., description="Scheduling or near-real-time.")
    control_start: Optional[datetime] = Field(None, description="Start of the control horizon.")
    control_end: Optional[datetime] = Field(None, description="End of the control horizon.")
    job_start: Optional[datetime] = Field(None, description="When the job first executes.")
    job_end: Optional[datetime] = Field(None, description="After this time no further updates are made.")
    repeat_seconds: Optional[float] = Field(None, description="NRT repeat interval (seconds).")
    generation_and_load: GenerationAndLoad = Field(..., description="Forecast time series.")
    day_end: Optional[datetime] = Field(
        None,
        description="End of daylight; used as HBES target SoC deadline. "
                    "Defaults to sunset at the configured location.",
    )
    measurement: Optional[str] = Field(None, description="ID of a stored measurement to blend with the forecast.")
    bulk: Optional[Bulk] = Field(None, description="Bulk energy window (optional).")
    P_net_after_kW_limitation: Optional[List[PowerBoundEntry]] = Field(
        None, description="Per-timestamp power bounds (optional)."
    )
    battery_specs: Union[BatterySpecs, List[BatterySpecs]] = Field(
        ..., description="Battery asset specifications."
    )

    @field_validator("day_end", mode="before")
    @classmethod
    def set_day_end(cls, v, info):
        """
        Validator to set day_end if not provided, based on sunset time at the configured location.

        :param v: The value of day_end.
        :param info: The validation info object.
        :return: The validated value.
        """
        if v is not None:
            return v
        values = info.data
        control_start: Optional[datetime] = values.get("control_start")
        if control_start is None:
            return v

        location = LocationInfo(
            name=settings.location_name,
            region=settings.location_region,
            timezone=settings.location_timezone,
            latitude=settings.location_lat,
            longitude=settings.location_lon,
        )
        s = sun(location.observer, date=control_start.date())
        sunset_time = s["sunset"].astimezone(timezone.utc)

        generation_and_load: Optional[GenerationAndLoad] = values.get("generation_and_load")
        if generation_and_load and isinstance(generation_and_load, GenerationAndLoad):
            timestamps = [point.timestamp for point in generation_and_load.values]
            return min(timestamps, key=lambda t: abs(t - sunset_time))

        return sunset_time
