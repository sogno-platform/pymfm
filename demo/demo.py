# from urllib import request
import base64
import json
import time
from io import StringIO
from os import getenv
from pathlib import Path
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from matplotlib import pyplot as plt

input_file_name = "scheduling_optimization_based.json"
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



def main():
    with open(base_path / input_file_name, "r") as fp:
        job = json.load(fp)
    
    # Put in timeseries input data into nice structure
    df_limit = pd.json_normalize(job["P_net_after_kW_limitation"])
    df_limit["timestamp"] = pd.to_datetime(df_limit["timestamp"])
    df_limit.set_index("timestamp", inplace=True)
    
    df_forecast = pd.json_normalize(job["generation_and_load"]["values"])
    df_forecast["timestamp"] = pd.to_datetime(df_forecast["timestamp"])
    df_forecast.set_index("timestamp", inplace=True)

    df_correct = df_forecast.copy() # TODO this should be the real values for comparison

    # Post the job and get results
    job_id = post_pymfm(job)
    print(f"ID of the started started job: {job_id}")
    result = get_pymfm(job_id)  # TODO format result and print
    
    # Put results into dataframe
    df_schedule = pd.json_normalize(result["schedule"])
    df_schedule["time"] = pd.to_datetime(df_schedule["time"])
    df_schedule.set_index("time", inplace=True)

    # Restructure data for the plots
    # Battery SOC 
    df_bat = df_schedule.filter(["SoC_bat.bat_1", "SoC_bat.bat_2", "SoC_bat.bat_3"])
    df_bat.apply(lambda x: 100*x).plot(title="Battery SOC", ylabel="SOC [%]", legend=True, figsize=(10, 6))

    plt.savefig(base_path / "soc.png")
    
    # Limits
    df_limit["P_net_after"] = df_schedule["P_net_after_kW"]
    df_limit.plot(title="Projected net Power and Input Limits", ylabel="P_net [kW]", legend=True, figsize=(10, 6))
    plt.savefig(base_path / "limit.png")

    # Power balance
    df_balance = df_schedule.filter(["P_net_after_kW", "P_net_before_kW"])
    df_balance.loc[:,"P_bat_total_kW"] = df_schedule.filter(["P_bat_kW.bat_1","P_bat_kW.bat_2","P_bat_kW.bat_3"]).sum(axis=1)
    df_balance.plot(title="Power Balance", ylabel="P_net [kW]", legend=True, figsize=(10, 6))
    plt.savefig(base_path / "power_balance.png")
    print(df_limit)


if __name__ == "__main__":
    main()
