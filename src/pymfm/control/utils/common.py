from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel as PydBaseModel, Field
import pandas as pd


INDEX_COLUMN = "time"


def get_freq(*dfs):
    delta_t = None
    for df in dfs:
        if df is None:
            continue
        if df.index.freq is None:
            continue
        if delta_t is None:
            delta_t = df.index.freq
            continue
        if delta_t != df.index.freq:
            raise AttributeError("All deltaT of the specified timeseries have to be the same")
    return delta_t


# for global configuration
class BaseModel(PydBaseModel):
    """
    Base Pydantic model with configuration settings to allow population by field name.
    """

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True


# Assumes List of objects with an index attribute
def from_df_validator(cls, df: pd.DataFrame):
    if not isinstance(df, pd.DataFrame):
        return df
    df = df.reset_index()
    return df.to_dict(orient="records")


def list_to_df(li: list, index_col: str = INDEX_COLUMN) -> pd.DataFrame:
    if not isinstance(li, list):
        li = [li]
    df = pd.DataFrame.from_records(li).set_index(index_col)
    try:
        df.index.freq = pd.infer_freq(df.index)
    except (ValueError, TypeError):
        df.index.freq = None
    return df


def extract_df(obj: BaseModel, attr: str, index_col: str = INDEX_COLUMN) -> Optional[pd.DataFrame]:
    # try:
    li = obj.dict()[attr]
    # except KeyError: # XXX should we let this throw?
    #     return None
    if li is None:
        return None
    return list_to_df(li, index_col)


def df_to_list(df: pd.DataFrame) -> List[Dict]:
    df = df.reset_index()
    num_levels = df.columns.nlevels
    if num_levels > 1:
        {col: df_to_list(df[col]) for col in df.columns.levels[0]}  # TODO unfinished, still needed?


class TimeseriesData(BaseModel):
    time: Optional[List[datetime]] = Field(None, alias="Timestamp")
    # XXX this alias should really be Value but it is probably to late to change api
    values: Dict[str, List[Any]] = Field(..., alias="Values")

    def to_df(self) -> pd.DataFrame:
        df = pd.DataFrame.from_records(self.values, index=self.time)
        if INDEX_COLUMN in df.columns:
            df.set_index(INDEX_COLUMN)
        else:
            df.index.name = INDEX_COLUMN
        return df

    @classmethod
    def from_df(cls, df: pd.DataFrame):
        return cls(time=df.index.to_list(), values=df.to_dict(orient="list"))
