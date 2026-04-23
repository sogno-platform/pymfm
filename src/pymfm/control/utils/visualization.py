import itertools
import logging
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from pymfm.control.schemas.input import ControlLogic, OperationMode

log = logging.getLogger(__name__)

TIMESTAMP_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"


def _save_figure(fig, path: str) -> None:
    """Save a figure as SVG and always close it to free memory."""
    fig.savefig(path, format="svg")
    plt.close(fig)
    log.debug("Saved plot to %s", path)


def visualize_and_save_plots(
    control_logic: ControlLogic,
    operation_mode: OperationMode,
    job_id: str,
    dataframe: pd.DataFrame,
    output_directory: str,
) -> None:
    """Visualize control output data from a DataFrame and save plots as SVG files based on control logic and operation mode.

    Parameters
    ----------
    control_logic : ControlLogic
        containing control logic information.
    operation_mode : OperationMode
        containing operation mode information.
    job_id : str
        The job identifier, used as a prefix for output file names.
    dataframe : pd.DataFrame
        containing data to be visualized.
    output_directory : str
        Directory where the SVG plots will be saved.
    """
    os.makedirs(output_directory, exist_ok=True)

    if control_logic == ControlLogic.OPTIMIZATION_BASED:
        _plot_opt_net_power(job_id, dataframe, output_directory)
        _plot_opt_power_balance(job_id, dataframe, output_directory)
        _plot_opt_battery_soc(job_id, dataframe, output_directory)

    elif control_logic == ControlLogic.RULE_BASED and operation_mode == OperationMode.SCHEDULING:
        _plot_rb_scheduling(job_id, dataframe, output_directory)

    log.info("Plots saved to %s", os.path.abspath(output_directory))


# Optimisation-based plots

def _plot_opt_net_power(job_id: str, df: pd.DataFrame, directory: str) -> None:
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.plot(df.index, df["P_net_after_kW"], linestyle="--", label="P_net_after_kW", color="olivedrab", lw=2)
    ax.plot(df.index, df["upperb"], label="Upper bound", color="red", lw=2)
    ax.plot(df.index, df["lowerb"], label="Lower bound", color="red", lw=2)
    ax.set_title("Net power after control and its bounds")
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Power (kW)")
    ax.grid(True)
    ax.legend()
    _save_figure(fig, os.path.join(directory, f"{job_id}_p_net_after_bounds.svg"))


def _plot_opt_power_balance(job_id: str, df: pd.DataFrame, directory: str) -> None:
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.plot(df.index, df["P_net_before_kW"], label="P_net_before_kW", color="hotpink", lw=2)
    ax.plot(df.index, df["P_net_after_kW"], linestyle="--", label="P_net_after_kW", color="olivedrab", lw=2)
    ax.plot(df.index, df["P_bat_total_kW"], label="P_bat_total_kW", color="turquoise", lw=2)
    ax.set_title("Power balance")
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Power (kW)")
    ax.grid(True)
    ax.legend()
    _save_figure(fig, os.path.join(directory, f"{job_id}_power_balance.svg"))


def _plot_opt_battery_soc(job_id: str, df: pd.DataFrame, directory: str) -> None:
    soc_cols = [col for col in df.columns if "SoC_bat" in str(col)]
    if not soc_cols:
        return
    color_cycle = itertools.cycle(plt.cm.tab20.colors)
    fig, ax = plt.subplots(figsize=(12, 8))
    for col in soc_cols:
        ax.plot(df.index, df[col], label=str(col), color=next(color_cycle), lw=2)
    ax.set_title("Battery state of charge")
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("SoC")
    ax.grid(True)
    ax.legend()
    _save_figure(fig, os.path.join(directory, f"{job_id}_battery_soc.svg"))


# Rule-based scheduling plot

def _plot_rb_scheduling(job_id: str, df: pd.DataFrame, directory: str) -> None:
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.plot(df.index, df["P_net_before_kW"], label="P_net_before_kW", color="hotpink", lw=2)
    ax.plot(df.index, df["P_net_after_kW"], linestyle="--", label="P_net_after_kW", color="olivedrab", lw=2)
    if "P_bat_1_kW" in df.columns:
        ax.plot(df.index, df["P_bat_1_kW"], label="P_bat_1_kW", color="turquoise", lw=2)
    ax.set_xlabel("Timestamp")
    ax.grid(True)
    ax.legend()
    _save_figure(fig, os.path.join(directory, f"{job_id}_output.svg"))
