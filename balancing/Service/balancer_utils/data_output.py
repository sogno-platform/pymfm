from importlib.metadata import version
import pandas as pd
from datetime import datetime
from pydantic import BaseModel as PydBaseModel, Field
from pyomo.opt import SolverStatus, TerminationCondition
import matplotlib.pyplot as plt


class BaseModel(PydBaseModel):
    class Config:
        allow_population_by_field_name = True
        json_encoders = {datetime: lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")}


class TimeseriesData(BaseModel):
    time: datetime = Field(..., alias="timestamp")
    # XXX this alias should really be Value but it is probably to late to change api
    values: dict[str, float] = Field(..., alias="values")


class BalancerOutput(BaseModel):
    id: str
    version: str
    units: dict[str, str] = Field(default_factory=dict)
    output: list[TimeseriesData]


# XXX not sure why it is structured like this but this is needed to keep the response the same
class BalancerOutputWrapper(BaseModel):
    status: str = Field(default="success")
    details: str = Field(default="ok")
    balancer_output: BalancerOutput = Field(..., alias="balancer_output")


def prep_optimizer_output(
    import_profile: pd.Series,
    bat_profiles: pd.DataFrame,
    sof_profiles: pd.DataFrame,
    forecasts: pd.Series,
    df_battery_specs: pd.DataFrame,
):
    result_overview = pd.DataFrame(
        index=forecasts.index,
        columns=["P_tie_kW", "expected_P_tie_kW"],
    )
    result_overview["P_tie_kW"] = forecasts["P_net_kW"]

    result_overview["expected_P_tie_kW"] = import_profile
    for col in bat_profiles.columns:
        result_overview[f"P_{col}_kW"] = bat_profiles[col]
        result_overview[f"SoC_{col}_%"] = sof_profiles[col] * 100

    return result_overview


def values_mapper(col_name: str):
    if col_name.startswith("P_bat"):
        return col_name.removeprefix("P_bat")
    return col_name


def df_to_output(
    output: pd.DataFrame, id: str, status: tuple[SolverStatus, TerminationCondition]
) -> BalancerOutputWrapper:
    # Remove "kW" from column names
    output.columns = output.columns.str.replace("_kW", "")
    value_cols = output.columns[
        output.columns.map(lambda col: col == "time" or col.startswith("P_bat"))
    ]
    output = output[value_cols].to_dict(orient="index")
    output = [{"time": time, "values": d} for time, d in output.items()]
    out = BalancerOutput(
        id=id,
        version=version("platone-balancing-module"),
        units={"time": "ISO8601", "P": "kW"},
        output=output,
    )

    wrapped_output = BalancerOutputWrapper(
        status=status[0], details=status[1], balancer_output=out
    )
    return wrapped_output


def output_visualization(output_df):
    output_df.plot()
    plt.savefig("results/output.png")
