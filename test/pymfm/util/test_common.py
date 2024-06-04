from datetime import datetime
from typing import List
from pydantic import validator
import pytest
from pymfm.control.utils.common import (
    TimeseriesData,
    BaseModel,
    from_df_validator,
    list_to_df,
)


@pytest.fixture
def intseries():
    return [
        {"time": 1, "col1": 0, "col2": 0},
        {"time": 3, "col1": 1, "col2": 1},
        {"time": 5, "col1": 2, "col2": 2},
        {"time": 7, "col1": 3, "col2": 3},
        {"time": 9, "col1": 4, "col2": 4},
    ]


@pytest.fixture
def timeseries():
    return [
        {"time": "2024-05-28T00:00:00", "col1": 0, "col2": 0},
        {"time": "2024-05-28T00:15:00", "col1": 1, "col2": 1},
        {"time": "2024-05-28T00:30:00", "col1": 2, "col2": 2},
        {"time": "2024-05-28T00:45:00", "col1": 3, "col2": 3},
        {"time": "2024-05-28T01:00:00", "col1": 4, "col2": 4},
    ]


@pytest.fixture
def intseries_model(intseries):
    return Model(vals=intseries)


@pytest.fixture
def timeseries_model(timeseries):
    return Model(vals=timeseries)


class Row(BaseModel):
    time: datetime
    col1: int
    col2: int


class Model(BaseModel):
    vals: List[Row]

    @validator("vals", pre=True)
    def vals_as_df(cls, li):
        return from_df_validator(cls, li)


def test_timeseries_parse_from_dict(timeseries):
    Model(vals=timeseries)
    return True


def test_intseries_parse_from_dict(intseries):
    Model(vals=intseries)
    return True


def test_timeseries_model_to_df(timeseries_model):
    df = list_to_df(timeseries_model.dict()["vals"])


def test_intseries_model_to_df(intseries_model):
    df = list_to_df(intseries_model.dict()["vals"])


def test_timeseries_model_roundtrip(timeseries_model):
    df = list_to_df(timeseries_model.dict()["vals"])
    new_obj = Model(vals=df)
    assert new_obj == timeseries_model


def test_intseries_model_roundtrip(intseries_model):
    df = list_to_df(intseries_model.dict()["vals"])
    new_obj = Model(vals=df)
    assert new_obj == intseries_model
