from datetime import datetime
from typing import Optional
from pymfm.control.utils.common import BaseModel
from pymfm.control.utils.data_input import InputData
from pymfm.control.utils.data_output import BalancerOutput
from pydantic import Field
from enum import Enum


class StrEnum(str, Enum):
    pass


# class BaseModel(PydBaseModel):
#     class Config:
#         allow_population_by_field_name = True
#         use_enum_values = True
#         json_encoders = {datetime: lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")}


class Status(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class JobBase(BaseModel):
    id: str  # TODO add default generator
    input: InputData


class JobComplete(JobBase):
    status: Status = Status.CREATED
    details: Optional[str] = None
    created: datetime = Field(default_factory=datetime.now)
    finished: Optional[datetime] = None
    result: Optional[BalancerOutput] = None
