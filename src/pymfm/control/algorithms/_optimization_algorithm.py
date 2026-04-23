# Internal bridge — wraps the optimisation scheduler in the Algorithm interface.
# Not part of the public API; import OptimisationAlgorithm only via data_prep.

from typing import Optional

import pandas as pd

from pymfm.control.algorithms.base import Algorithm, AlgorithmResult
from pymfm.control.algorithms.optimization import run_scheduling
from pymfm.control.schemas.input import Bulk


class OptimisationAlgorithm(Algorithm):
    """Optimisation-based (MILP) battery scheduling algorithm."""

    def run(
        self,
        timeseries: pd.DataFrame,
        df_battery: pd.DataFrame,
        delta_T_h: float,
        day_end=None,
        bulk_data: Optional[Bulk] = None,
        pv_curtailment: bool = False,
    ) -> AlgorithmResult:
        output_batteries, output_system, output_static, solver_status = run_scheduling(
            timeseries=timeseries,
            df_battery=df_battery,
            day_end=day_end,
            bulk_data=bulk_data,
            pv_curtailment=pv_curtailment,
        )

        # Post-process: compute net battery power column
        tmp = output_batteries.P_ch_bat_kW - output_batteries.P_dis_bat_kW
        tmp.columns = pd.MultiIndex.from_product([["P_bat_kW"], tmp.columns])
        output_df = output_batteries.join(tmp)
        output_df.drop(
            ["is_ch", "is_dis", "P_ch_bat_kW", "P_dis_bat_kW"],
            axis="columns",
            level=0,
            inplace=True,
        )

        output_system["P_net_after_kW"] = output_system.P_imp_kW - output_system.P_exp_kW
        output_system.drop(["is_imp", "is_exp", "P_exp_kW", "P_imp_kW"], axis="columns", inplace=True)
        output_system.columns = pd.MultiIndex.from_product([output_system.columns, [""]])
        output_df = output_df.join(output_system)

        return AlgorithmResult(
            output_df=output_df,
            peak_imp=float(output_static.get("peak_imp", 0.0)),
            peak_exp=float(output_static.get("peak_exp", 0.0)),
            solver_status=solver_status,
        )
