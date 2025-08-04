import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException

from pydantic import BaseModel, RootModel
import pandas as pd
from measurement.router.query import ENGINE, delete_table, get_data, insert_data, list_all_tables

router = APIRouter(tags=["measurements"])


class BaseRecord(BaseModel):
    timestamp: datetime.datetime


class PowerMeasurementRecord(BaseRecord):
    value: float
    unit: Optional[str] = None


class TimeSeries(BaseModel):
    id: str
    data: List[PowerMeasurementRecord]


class TableInfo(BaseModel):
    id: str
    columns: List[str]
    n_entries: int
    start_time: datetime.datetime
    end_time: datetime.datetime


@router.get("/")
def get_all_measurements():
    """Get all measurement IDs

    Raises
    ------
    NotImplemented
        _description_
    """
    ret = list_all_tables()
    return ret


@router.post("/")
def create_new_measurement(input: TimeSeries):
    """Create new table"""
    # ts_table_setup(input.id)
    df = pd.DataFrame.from_records(input.model_dump()["data"]).set_index("timestamp")
    with ENGINE.connect() as conn:
        df.to_sql(input.id, conn, if_exists="fail")
        conn.commit()
    return "ok"


@router.put("/{ts_id}")
def add_measurements(
    ts_id: str, input: TimeSeries, exists: Literal["fail"] | Literal["update"] | Literal["append"] = "update"
):
    """Add measurements to an existing table"""
    df = pd.DataFrame.from_records(input.model_dump()["data"]).set_index("timestamp")
    insert_data(ts_id, df, exists)

    return input



@router.get("/{ts_id}")
def get_measurements(ts_id: str, start: Optional[datetime.datetime] = None, end: Optional[datetime.datetime] = None):

    meas =  get_data(ts_id, start, end).reset_index().to_dict("records")
    if meas is None:
        raise HTTPException(404, "Measurement does not exist")
    return meas


@router.delete("/{ts_id}")
def remove_measurement(ts_id: str):
    """remove measurement from db"""
    # XXX Should this remove the table or just measurements? Maybe query param
    delete_table(ts_id)
    return "ok"
