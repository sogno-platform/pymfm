# The pymfm framework — service-layer data models.

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from pymfm.control.utils.common import BaseModel
from pymfm.control.schemas.input import InputData
from pymfm.control.schemas.output import BalancerOutput


class Status(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class JobBase(BaseModel):
    id: str
    input: InputData


class JobComplete(JobBase):
    status: Status = Status.CREATED
    details: Optional[str] = None
    created: datetime = Field(default_factory=datetime.now)
    finished: Optional[datetime] = None
    result: Optional[BalancerOutput] = None
