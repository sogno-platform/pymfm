# The pymfm framework — shared utilities used across control and schema modules.

from enum import Enum
from typing import List, Optional

import pandas as pd
from pydantic import BaseModel as PydBaseModel, ConfigDict

# Canonical name for the time index column used throughout the codebase.
INDEX_COLUMN = "timestamp"


# ---------------------------------------------------------------------------
# Pydantic base classes
# ---------------------------------------------------------------------------

class StrEnum(str, Enum):
    """
    An enumeration class for representing string-based enums.
    """
    pass


class BaseModel(PydBaseModel):
    """
    Base Pydantic model with configuration settings to allow population by field name.
    """
    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# DataFrame helpers
# ---------------------------------------------------------------------------

def get_freq(*dfs: Optional[pd.DataFrame]) -> pd.DateOffset:
    """Return the shared frequency of all non-None DataFrames.

    Raises
    ------
    ValueError
        If two DataFrames have different inferred frequencies.
    """
    delta_t = None
    for df in dfs:
        if df is None or df.index.freq is None:
            continue
        if delta_t is None:
            delta_t = df.index.freq
        elif delta_t != df.index.freq:
            raise ValueError(
                f"All time series must share the same time step, "
                f"but found {delta_t} and {df.index.freq}."
            )
    return delta_t


def list_to_df(li: list, index_col: str = INDEX_COLUMN) -> pd.DataFrame:
    """Convert a list of record dicts to a DataFrame indexed by *index_col*."""
    if not isinstance(li, list):
        li = [li]
    df = pd.DataFrame.from_records(li).set_index(index_col)
    try:
        df.index.freq = pd.infer_freq(df.index)
    except (ValueError, TypeError):
        df.index.freq = None
    return df


def extract_df(
    obj: BaseModel,
    attr: str,
    index_col: str = INDEX_COLUMN,
) -> Optional[pd.DataFrame]:
    """Extract a list attribute from a Pydantic model and convert it to a DataFrame.

    Returns None if the attribute value is None.
    """
    value = obj.model_dump()[attr]
    if value is None:
        return None
    return list_to_df(value, index_col)
