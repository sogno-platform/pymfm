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
        job_id = post_pymfm(job)
    print(f"simulationID of the started simulation: {job_id}")
    result = get_pymfm(job_id)  # TODO format result and print
    # print(result)
    df_schedule = pd.json_normalize(result["schedule"])
    df_schedule["time"] = pd.to_datetime(df_schedule["time"])
    df_schedule.set_index("time", inplace=True)

    # Battery SOC 
    df_bat = df_schedule.filter(["SoC_bat.bat_1", "SoC_bat.bat_2", "SoC_bat.bat_3"])
    df_bat.apply(lambda x: 100*x).plot(title="Battery SOC", ylabel="SOC [%]", legend=True, figsize=(10, 6))

    plt.savefig(base_path / "SOC.png")
    print(df_schedule)


if __name__ == "__main__":
    main()
