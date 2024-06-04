import glob
import json
import logging
import os
from typing import List
from pymfm.control.utils import data_output
from fastapi import HTTPException, status
log = logging.getLogger("server.crud")

async def save_result(result: data_output.BalancerOutputWrapper, path: str) -> data_output.BalancerOutputWrapper:
    # print(result.json(by_alias=True))
    with open(path, "w") as outfile:
        outfile.write(result.json(by_alias=True))
    return result


async def get_result(path: str) -> data_output.BalancerOutputWrapper:
    # outpath = os.path.join("output", f"{id}.json")
    try:
        with open(path, "r") as outfile:
            return json.load(outfile)
    except FileNotFoundError:
        raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No result with this id")
    
async def delete_result(path: str) -> data_output.BalancerOutputWrapper:
    try:
        os.remove(path)
    except FileNotFoundError as exc:
        raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No result with this id")

async def get_latest() -> data_output.BalancerOutputWrapper:
    outpath = os.path.join(".","output","*")
    list_of_files = glob.glob(outpath)
    list_of_files.sort(key=os.path.getctime)
    if len(list_of_files) == 0:
        raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No results available")
    return await get_result(list_of_files[0])
    
async def clean_up() -> List[str]:
    outpath = os.path.join("output","*")
    list_of_files = glob.glob(outpath)
    list_of_files.sort(key=os.path.getctime)
    to_delete = list_of_files[:-10]
    for path in to_delete:
        log.debug(f" delete {path}")
        os.remove(path)
    return to_delete