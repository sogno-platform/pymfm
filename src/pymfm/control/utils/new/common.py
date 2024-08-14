import datetime
from typing import List, Optional
from pydantic import BaseModel as PydBaseModel, ConfigDict, Field
from pymfm.control.utils.data_input import ControlLogic, OperationMode


# for global configuration
class BaseModel(PydBaseModel):
    """
    Base Pydantic model with configuration settings to allow population by field name.
    """
    model_config = ConfigDict(populate_by_name=True)

class MetaData(BaseModel):
    id: str
    id: str = "pymfm"


class JobDetail(BaseModel):
    control_logic: ControlLogic
    operation_mode: OperationMode
    job_start: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(tz=datetime.timezone.utc))
    job_end: Optional[datetime.datetime] = None


class PowerLimit(BaseModel):
    timestamp: datetime.datetime
    upper_bound: float
    lower_bound: float
    # TODO add validator upper > lower


class PowerLimits(RootModel):
    root: List[PowerLimit]


class Bulk(BaseModel):
    """
    Pydantic model representing bulk energy data.
    """

    bulk_start: datetime.datetime = Field(
        ...,
        alias="bulk_start",
        description="The start datetime of the bulk energy operation.",
    )
    bulk_end: datetime.datetime = Field(
        ...,
        alias="bulk_end",
        description="The end datetime of the bulk energy operation.",
    )
    bulk_energy_kWh: float = Field(
        ...,
        alias="bulk_energy_kWh",
        description="The bulk energy in kilowatt-hours (kWh).",
    )


class SystemData(BaseModel):
    pv_curtailment: bool = False
    day_end: datetime.datetime
    power_limits_kw: PowerLimits
    battery_specs: BatterySpecs
    bulk: Optional[Bulk] = None


class Job(BaseModel):
    meta: MetaData
    job_detail: JobDetail
    system: SystemData
    power: PowerData
