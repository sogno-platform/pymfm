import glob
import json
import logging
import os
from pathlib import Path
from typing import List, Optional, Union
from pymfm.control.utils import data_output
from fastapi import HTTPException, status
from service import data_aux
from service.crud import AsyncStorage

log = logging.getLogger("server.crud")


class FileStorage(AsyncStorage):
    def __init__(self, filepath: Union[Path, str]):
        self.filepath = Path(filepath)

    async def all_ids(self):
        list_of_files = glob.glob(f"{self.filepath}/*")
        return [file.rsplit("/",1)[1].removesuffix(".json") for file in list_of_files]

    async def store(self, job: data_aux.JobComplete) -> data_aux.JobComplete:
        with open(self.filepath / f"{job.id}.json", "w") as fp:
            fp.write(job.model_dump_json(by_alias=True))
        return job

    async def read(self, id: str) -> Optional[data_aux.JobComplete]:
        try:
            with open(self.filepath / f"{id}.json", "r") as fp:
                return json.load(fp)
        except FileNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No result with this id")
        except (
            json.decoder.JSONDecodeError
        ) as err:  # XXX should this be caught outside of method, so this can be used in a non-server context
            raise HTTPException(
                500,
                "unable to decode job details, please try again or contact the server admin.",
            )

    async def delete(self, id: str) -> Optional[data_aux.JobComplete]:
        ret = await self.read(id)
        try:
            os.remove(self.filepath / id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No result with this id")
        return ret


# async def save_result(result: data_output.BalancerOutputWrapper, path: str) -> data_output.BalancerOutputWrapper:
#     # print(result.json(by_alias=True))
#     with open(path, "w") as outfile:
#         outfile.write(result.json(by_alias=True))
#     return result


async def get_result(path: str) -> data_output.BalancerOutputWrapper:
    # outpath = os.path.join("output", f"{id}.json")
    try:
        with open(path, "r") as outfile:
            return json.load(outfile)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No result with this id")


async def delete_result(path: str) -> data_output.BalancerOutputWrapper:
    try:
        os.remove(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No result with this id")


async def get_latest() -> data_output.BalancerOutputWrapper:
    outpath = os.path.join(".", "output", "*")
    list_of_files = glob.glob(outpath)
    list_of_files.sort(key=os.path.getctime)
    if len(list_of_files) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No results available")
    return await get_result(list_of_files[0])


async def clean_up() -> List[str]:
    outpath = os.path.join("output", "*")
    list_of_files = glob.glob(outpath)
    list_of_files.sort(key=os.path.getctime)
    to_delete = list_of_files[:-10]
    for path in to_delete:
        log.debug(f" delete {path}")
        os.remove(path)
    return to_delete
