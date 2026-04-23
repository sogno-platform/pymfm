# The pymfm framework
#
# Abstract base class for control algorithms.
# Both RuleBasedAlgorithm and OptimisationAlgorithm implement this interface,
# letting the controller stay agnostic about which algorithm is active.

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd
from pyomo.opt import SolverStatus, TerminationCondition

from pymfm.control.schemas.input import Bulk


@dataclass
class AlgorithmResult:
    """Unified result type returned by every algorithm."""

    output_df: pd.DataFrame
    """Per-timestep results as a (possibly MultiIndex-column) DataFrame."""

    peak_imp: Optional[float] = None
    """Peak import power observed/optimised (kW)."""

    peak_exp: Optional[float] = None
    """Peak export power observed/optimised (kW)."""

    solver_status: tuple = (SolverStatus.ok, TerminationCondition.optimal)
    """(SolverStatus, TerminationCondition) from the solver; default = ok/optimal."""


class Algorithm(ABC):
    """Interface that all control algorithms must satisfy."""

    @abstractmethod
    def run(
        self,
        timeseries: pd.DataFrame,
        df_battery: pd.DataFrame,
        delta_T_h: float,
        day_end: Optional[datetime] = None,
        bulk_data: Optional[Bulk] = None,
        pv_curtailment: bool = False,
    ) -> AlgorithmResult:
        """Execute the algorithm and return a unified AlgorithmResult.

        Parameters
        ----------
        timeseries:
            Forecast DataFrame indexed by timestamp.
        df_battery:
            Battery spec DataFrame indexed by battery id.
        delta_T_h:
            Time step in hours.
        day_end:
            HBES target SoC deadline (optimisation only).
        bulk_data:
            Optional bulk energy window (optimisation only).
        pv_curtailment:
            Allow PV curtailment (optimisation only).
        """
        ...
