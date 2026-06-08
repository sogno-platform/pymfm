# The pymfm framework
#
# Copyright (C) 2023, Institute for Automation of Complex Power Systems (ACS),
# E.ON Energy Research Center (E.ON ERC), RWTH Aachen University
#
# Licensed under the Apache License, Version 2.0 (the "License").
#
# Pure Pydantic output models — no matplotlib, no file I/O here.

from datetime import datetime
from importlib.metadata import version
from typing import Dict, List, Optional

from pydantic import Field

from pymfm.control.utils.common import BaseModel


class ResultTimeseries(BaseModel):
    """Result values for a single timestep."""

    timestamp: datetime
    soc_bat: Dict[str, float] = Field(..., alias="SoC_bat")
    p_bat_kw: Dict[str, float] = Field(..., alias="P_bat_kW")
    p_pv_kw: Optional[float] = Field(None, alias="P_PV_kW")
    p_net_before_kw: float = Field(..., alias="P_net_before_kW")
    p_net_after_kw: float = Field(..., alias="P_net_after_kW")


class BalancerOutput(BaseModel):
    """Full result of a balancing run."""

    id: str
    version: str = Field(default_factory=lambda: version("pymfm"))
    peak_imp: Optional[float] = None
    peak_exp: Optional[float] = None
    schedule: List[ResultTimeseries]


class BalancerOutputWrapper(BaseModel):
    """Outer envelope kept for API response compatibility."""

    status: str = Field(default="success")
    details: str = Field(default="ok")
    balancer_output: BalancerOutput = Field(..., alias="Balancer_output")

def unstack_keys(d: dict) -> dict:
    """Recursively convert a flat dict with tuple keys into a nested dict.

    Pandas MultiIndex columns come out as tuples; this turns them into the
    nested structure expected by ResultTimeseries.
    """
    out: dict = {}
    for key, val in d.items():
        if isinstance(key, str):
            out[key] = val
            continue
        current = out
        last_valid: str = ""
        for k in key:
            if not k:
                continue
            last_valid = k
            if k not in current:
                current[k] = {}
            current = current[k]  # type: ignore[assignment]
        if last_valid:
            # Walk back one level to assign the leaf value
            node = out
            parts = [k for k in key if k]
            for k in parts[:-1]:
                node = node[k]
            node[parts[-1]] = val
    return out


def validate_timestep(d: dict) -> ResultTimeseries:
    """Build a ResultTimeseries from a flat/MultiIndex row dict."""
    return ResultTimeseries(**unstack_keys(d))
