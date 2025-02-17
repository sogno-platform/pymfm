# from urllib import request
import base64
import datetime
import json
import time
from os import getenv
from pathlib import Path
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from matplotlib import pyplot as plt

input_file_name = "scheduling_optimization_based.json"
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
    response = requests.put(
        url=f"{pymfm_url_base}/measurement/{meas['id']}", headers=headers, data=json.dumps(meas, default=str), auth=auth
    )
    return response.json()["id"]


def delete_measurement(id: str):
    headers = {"accept": "application/json"}
    response = requests.delete(url=f"{pymfm_url_base}/measurement/{id}", headers=headers, auth=auth)
    return response.json() == "ok"


def plot_results(
    df_schedule: pd.DataFrame, df_limit: pd.DataFrame, df_meas: pd.DataFrame | None = None, plot_prefix: str = ""
):
    df_limit = df_limit.copy()
    df_schedule = df_schedule.copy()
    if df_meas is not None:
        df_meas = df_meas.copy()

    # Restructure data for the plots
    # Battery SOC
    df_bat = df_schedule.filter(["SoC_bat.bat_1", "SoC_bat.bat_2", "SoC_bat.bat_3"])
    df_bat.apply(lambda x: 100 * x).plot(title="Battery SOC", ylabel="SOC [%]", legend=True, figsize=(10, 6))

    plt.savefig(base_path / f"{plot_prefix}soc.png")

    # Limits
    if "P_net_after_corrected" in df_schedule.columns:
        df_limit["P_net_after"] = df_schedule["P_net_after_corrected"]
    else:
        df_limit["P_net_after"] = df_schedule["P_net_after_kW"]  # TODO Correct this by using the real measuremnts
    df_limit.plot(title="Projected net Power and Input Limits", ylabel="P_net [kW]", legend=True, figsize=(10, 6))
    plt.savefig(base_path / f"{plot_prefix}limit.png")

    # Power balance
    df_balance = df_schedule.filter(["P_net_after_kW", "P_net_before_kW"])
    df_balance.loc[:, "P_bat_total_kW"] = df_schedule.filter(
        ["P_bat_kW.bat_1", "P_bat_kW.bat_2", "P_bat_kW.bat_3"]
    ).sum(axis=1)
    df_balance.plot(title="Power Balance", ylabel="P_net [kW]", legend=True, figsize=(10, 6))
    plt.savefig(base_path / f"{plot_prefix}power_balance.png")


def main():
    DEV_TIMESTAMP = datetime.datetime(year=2021, month=4, day=1, hour=1, tzinfo=datetime.timezone.utc)
    with open(base_path / input_file_name, "r") as fp:
        job = json.load(fp)
    with open(base_path / meas_file_name, "r") as fp:
        meas_raw = json.load(fp)

    print(meas_raw)
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

    # df_correct = df_forecast.copy()  # TODO this should be the real values for comparison
    meas_data = df_meas.loc[DEV_TIMESTAMP]
    meas = {
        "id": job["measurement"],
        "data": [
            {
                "timestamp": (DEV_TIMESTAMP + pd.Timedelta(minutes=1)).isoformat(),
                "value": meas_data.Real_iONS_kW,
                "unit": "kW",
            }
        ],
    }
    # clean up measurement
    delete_measurement(job["measurement"])

    job_id = post_pymfm(job)
    result_before = get_pymfm(job_id)

    df_schedule_before = pd.json_normalize(result_before["schedule"])
    df_schedule_before["time"] = pd.to_datetime(df_schedule_before["time"])
    df_schedule_before.set_index("time", inplace=True)

    p_correction = (df_meas.Real_iONS_kW - df_schedule_before.P_net_before_kW).dropna()
    df_schedule_before["P_net_after_corrected"] = df_schedule_before["P_net_after_kW"] + p_correction
    plot_results(df_schedule_before, df_limit, df_meas, "before_")
    post_measurement(meas)

    # Post the job and get results
    job_id = post_pymfm(job)
    print(f"ID of the started job: {job_id}")
    result_after = get_pymfm(job_id)
    df_schedule_after = pd.json_normalize(result_after["schedule"])
    df_schedule_after["time"] = pd.to_datetime(df_schedule_after["time"])
    df_schedule_after.set_index("time", inplace=True)

    p_correction = (df_meas.Real_iONS_kW - df_schedule_after.P_net_before_kW).dropna()
    df_schedule_after["P_net_after_corrected"] = df_schedule_after["P_net_after_kW"] + p_correction
    plot_results(df_schedule_after, df_limit, df_meas, "after_")

    print(df_limit)


if __name__ == "__main__":
    main()
