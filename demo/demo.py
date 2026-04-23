# from urllib import request
import base64
import datetime
import json
import time
from os import getenv
from pathlib import Path
from typing import Literal
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from matplotlib import pyplot as plt
from sqlalchemy import literal


meas_file_name = "meas.json"
pymfm_url_base = f"http://{getenv('PYMFM_HOST','localhost')}:{int(getenv('PYMFM_PORT',8000))}"
base_path = Path(__file__).parent
auth = HTTPBasicAuth("admin", "admin")


def post_pymfm(job: dict) -> str:
    headers = {"accept": "application/json"}
    response = requests.post(url=pymfm_url_base + "/balancing", headers=headers, json=job, auth=auth)
    if not response.ok:
        print(response.text)
        return None
    return response.json()["id"]


def get_pymfm(job_id: str) -> dict:
    headers = {"accept": "application/json"}
    resp = {"status": "created"}
    while resp["status"] != "success":
        if resp["status"] == "failed":
            print(f"Job failed. {resp['details']}")
            return None
        response = requests.get(url=f"{pymfm_url_base}/balancing/{job_id}", headers=headers, auth=auth)
        if not response.ok:
            print(response.text)
            return None
        resp = response.json()
        print("result not ready ...")
        time.sleep(1)
    # print(result["content"])
    print("... result ready!")
    return resp["result"]  # subject to change of the nedpoint


def post_measurement(meas: dict):
    headers = {"accept": "application/json"}
    headers["Content-Type"] = "application/json"
    response = requests.put(
        url=f"{pymfm_url_base}/measurement/{meas['id']}", headers=headers, data=json.dumps(meas, default=str), auth=auth
    )
    return response.json()["id"]


def delete_measurement(id: str):
    headers = {"accept": "application/json"}
    response = requests.delete(url=f"{pymfm_url_base}/measurement/{id}", headers=headers, auth=auth)
    return response.json() == "ok"


def add_correction(df_schedule: pd.DataFrame, df_limit: pd.DataFrame, df_meas: pd.DataFrame):
    # p_correction = (df_meas.Real_iONS_kW - df_schedule.P_net_before_kW).dropna()
    # df_schedule["P_net_after_real"] = df_schedule["P_net_after_kW"] + p_correction
    df_schedule["P_net_before_real"] = df_meas.Real_iONS_kW.loc[df_schedule.index]
    df_schedule["P_net_after_real"] = df_meas.Real_iONS_kW.loc[df_schedule.index] + df_schedule.filter(
        ["P_bat_kW.bat_1", "P_bat_kW.bat_2", "P_bat_kW.bat_3"]
    ).sum(axis=1)
    # if "P_net_after_real" in df_schedule.columns:
    df_limit["P_net_after_real"] = df_schedule["P_net_after_real"]
    # else:
    df_limit["P_net_after_kW"] = df_schedule["P_net_after_kW"]
    return df_schedule, df_limit, df_meas


def plot_results(
    df_schedule: pd.DataFrame, df_limit: pd.DataFrame, plot_prefix: str = "", use_real: bool | Literal["both"] = True
):
    df_limit = df_limit.copy()
    df_schedule = df_schedule.copy()

    if use_real is True:
        df_balance = df_schedule.filter(["P_net_after_real", "P_net_before_real"])
        df_limit = df_limit.drop(columns=["P_net_after_kW"])
    elif use_real is False:
        df_balance = df_schedule.filter(["P_net_after_kW", "P_net_before_kW"])
        df_limit = df_limit.drop(columns=["P_net_after_real"])
    else:
        df_balance = df_schedule.filter(["P_net_after_real", "P_net_before_real", "P_net_after_kW", "P_net_before_kW"])
    # Restructure data for the plots
    # Battery SOC
    df_bat = df_schedule.filter(["SoC_bat.bat_1", "SoC_bat.bat_2", "SoC_bat.bat_3"])
    df_bat.apply(lambda x: 100 * x).plot(title="Battery SOC", ylabel="SOC [%]", legend=True, figsize=(10, 6))

    plt.savefig(base_path / "plot" / f"{plot_prefix}soc.png")

    df_limit.plot(title="Projected net Power and Input Limits", ylabel="P_net [kW]", legend=True, figsize=(10, 6))
    plt.savefig(base_path / "plot" / f"{plot_prefix}limit.png")

    # Power balance
    # Choose either predicted values or corrected with measumerments
    df_balance.loc[:, "P_bat_total_kW"] = df_schedule.filter(
        ["P_bat_kW.bat_1", "P_bat_kW.bat_2", "P_bat_kW.bat_3"]
    ).sum(axis=1)
    df_balance.plot(title="Power Balance", ylabel="P_net [kW]", legend=True, figsize=(10, 6))
    plt.savefig(base_path / "plot" / f"{plot_prefix}power_balance.png")
    plt.close("all")


def simulated_nrt_step(
    df_meas: pd.DataFrame,
    df_limit: pd.DataFrame,
    df_forecast: pd.DataFrame,
    job: dict,
    time: datetime.datetime | None = None,
):
    if time is None:
        delete_measurement(job["measurement"])
    else:
        meas_data = df_meas.loc[time]
        meas = {
            "id": job["measurement"],
            "data": [
                {
                    "timestamp": (time + pd.Timedelta(minutes=1)).isoformat(),
                    "value": meas_data.Real_iONS_kW,
                    "unit": "kW",
                }
            ],
        }

        post_measurement(meas)

    job_id = post_pymfm(job)
    result = get_pymfm(job_id)

    df_schedule = pd.json_normalize(result["schedule"])
    df_schedule["time"] = pd.to_datetime(df_schedule["time"])
    df_schedule.set_index("time", inplace=True)

    add_correction(df_schedule, df_limit, df_meas)
    plot_results(df_schedule, df_limit, "before_" if time is None else f"{time.isoformat()}_", use_real=False)
    return df_schedule


def simulated_nrt():
    job_file_name = "scheduling_optimization_based.json"
    (base_path / "plot").mkdir(parents=True, exist_ok=True)

    with open(base_path / job_file_name, "r") as fp:
        job = json.load(fp)
    # load measurement needed in first run for correction in plotting
    with open(base_path / meas_file_name, "r") as fp:
        meas_raw = json.load(fp)

    df_meas = pd.json_normalize(meas_raw["measurements"])
    df_meas["timestamp"] = pd.to_datetime(df_meas["Time"])
    df_meas.set_index("timestamp", inplace=True)

    # Put in timeseries input data into nice structure
    df_limit = pd.json_normalize(job["P_net_after_kW_limitation"])
    df_limit["timestamp"] = pd.to_datetime(df_limit["timestamp"])
    df_limit.set_index("timestamp", inplace=True)

    df_forecast = pd.json_normalize(job["generation_and_load"]["values"])
    df_forecast["timestamp"] = pd.to_datetime(df_forecast["timestamp"])
    df_forecast.set_index("timestamp", inplace=True)

    DEV_TIMESTAMPS = [t for t in df_forecast.index]
    DEV_TIMESTAMPS = [None] + DEV_TIMESTAMPS

    df_schedule = None
    ls_nrt = []
    for count, t in enumerate(DEV_TIMESTAMPS):
        # if t is not None:
        #     t = t + datetime.timedelta(seconds=1)
        if df_schedule is not None:
            ind = df_schedule.index.get_indexer([t + datetime.timedelta(seconds=1)], method="bfill")[-1]
            for bat in job["battery_specs"]:
                bat["initial_SoC"] = df_schedule.iloc[ind][f"SoC_bat.{bat['id']}"]
        try:
            if t:
                print(f"{t = }")
            df_schedule = simulated_nrt_step(df_meas, df_limit, df_forecast, job, t)
        except TypeError:
            break
        ls_nrt = ls_nrt + [df_schedule.loc[min(df_schedule.index)]]

    df_schedule = pd.DataFrame(ls_nrt)
    add_correction(df_schedule, df_limit, df_meas)
    plot_results(df_schedule, df_limit, "dynamic_")

    print("done")


def scheduled():
    job_file_name = "scheduling_optimization_based.json"
    (base_path / "plot").mkdir(parents=True, exist_ok=True)

    with open(base_path / job_file_name, "r") as fp:
        job = json.load(fp)
    # load measurement needed in first run for correction in plotting
    with open(base_path / meas_file_name, "r") as fp:
        meas_raw = json.load(fp)

    df_meas = pd.json_normalize(meas_raw["measurements"])
    df_meas["timestamp"] = pd.to_datetime(df_meas["Time"])
    df_meas.set_index("timestamp", inplace=True)

    # Put in timeseries input data into nice structure
    df_limit = pd.json_normalize(job["P_net_after_kW_limitation"])
    df_limit["timestamp"] = pd.to_datetime(df_limit["timestamp"])
    df_limit.set_index("timestamp", inplace=True)

    df_forecast = pd.json_normalize(job["generation_and_load"]["values"])
    df_forecast["timestamp"] = pd.to_datetime(df_forecast["timestamp"])
    df_forecast.set_index("timestamp", inplace=True)

    DEV_TIMESTAMPS = [t for t in df_forecast.index]
    DEV_TIMESTAMPS = [None]  # + DEV_TIMESTAMPS

    df_schedule = None
    for count, t in enumerate(DEV_TIMESTAMPS):
        # if t is not None:
        #     t = t + datetime.timedelta(seconds=1)
        if df_schedule is not None:
            ind = df_schedule.index.get_indexer([t + datetime.timedelta(seconds=1)], method="bfill")[-1]
            for bat in job["battery_specs"]:
                bat["initial_SoC"] = df_schedule.iloc[ind][f"SoC_bat.{bat['id']}"]
        try:
            if t:
                print(f"{t = }")
            df_schedule = simulated_nrt_step(df_meas, df_limit, df_forecast, job, t)
        except TypeError:
            break

    print("done")


def measurements_analysis():
    job_file_name = "scheduling_optimization_based.json"
    (base_path / "plot").mkdir(parents=True, exist_ok=True)

    with open(base_path / job_file_name, "r") as fp:
        job = json.load(fp)
    # load measurement needed in first run for correction in plotting
    with open(base_path / meas_file_name, "r") as fp:
        meas_raw = json.load(fp)

    df_meas = pd.json_normalize(meas_raw["measurements"])
    df_meas["timestamp"] = pd.to_datetime(df_meas["Time"])
    df_meas.set_index("timestamp", inplace=True)
    df_compare = df_meas.filter(["Real_iONS_kW"]).rename({"Real_iONS_kW": "P_net_before_real"}, axis=1)
    # Put in timeseries input data into nice structure
    df_limit = pd.json_normalize(job["P_net_after_kW_limitation"])
    df_limit["timestamp"] = pd.to_datetime(df_limit["timestamp"])
    df_limit.set_index("timestamp", inplace=True)

    df_forecast = pd.json_normalize(job["generation_and_load"]["values"])
    df_forecast["timestamp"] = pd.to_datetime(df_forecast["timestamp"])
    df_forecast.set_index("timestamp", inplace=True)
    df_compare["P_net_before_forecast"] = df_forecast["P_required_kW"] - df_forecast["P_available_kW"]
    df_compare.dropna().plot(title="Mesurement vs Forecast", ylabel="P_net [kW]", legend=True, figsize=(10, 6))
    plt.savefig(base_path / "plot" / f"meas_vs_forecast.png")

    df_compare["Residual"] = df_compare["P_net_before_real"] - df_compare["P_net_before_forecast"]
    ax = (
        df_compare.dropna()
        .filter(["Residual"])
        .plot.bar(title="Residuals", xlabel="hour", ylabel="Forecast Error [kW]", legend=True, figsize=(10, 6))
    )

    all_ticks = ax.get_xticks()
    selected_ticks = all_ticks[::4]
    ax.set_xticks(selected_ticks)
    ax.set_xticklabels([df_compare.index[int(tick)].hour for tick in selected_ticks])
    plt.savefig(base_path / "plot" / f"residuals.png")
    print("done")


def correction_explaination():
    df = pd.DataFrame(
        {"measurement": [None, 2.5, None, None], "forecast": [1, 2, 2.5, 4.5], "corrected": [1.5, 2.5, 3, 5]}
    )
    ax = df.plot(title="Correction Example", legend=True, figsize=(10, 6), style=["o", "o-", "o-"])
    ax.get_lines()[0].set_zorder(3)

    plt.savefig(base_path / "plot" / f"correction.png")


if __name__ == "__main__":
    # simulated_nrt()
    scheduled()
    # measurements_analysis()
    # correction_explaination()
    plt.close("all")
