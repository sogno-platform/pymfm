import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException
from service.crud_fs import FileStorage
from service.crud_redis import RedisStorage
from service.data_aux import JobComplete

from pymfm.control.algorithms.controller import (do_balancing,
                                                 scheduling_or_real_time)
from pymfm.control.utils import data_input

log = logging.getLogger("server")

router = APIRouter(
    tags=["balancing"],
)

# XXX handle this via settings in the future
storage = FileStorage(filepath=Path(__file__).parent.parent / "store")  # MemoryStorage() # RedisStorage()
# storage = RedisStorage()


@router.post("/")
async def create_balancing_task(input: data_input.InputData, background_tasks: BackgroundTasks) -> JobComplete:
    log.info(f"received input data with id=<{input.id}>. Starting algorithm...")
    job = JobComplete(id=input.id, input=input)
    await storage.store(job)
    background_tasks.add_task(scheduling_or_real_time, job=job, storage=storage)
    return job


@router.get("/", description="get the ids of all jobs")
async def get_ids_endpoint() -> List[str]:
    return await storage.all_ids()


@router.get("/{id}")
async def get_result_endpoint(id: str) -> JobComplete:
    output = await storage.read(id)
    if output is None:
        raise HTTPException(404, f"No job with id {id}")
    return output


# XXX is Updating of a task usefull? Does the job need to be finished? Does a data update replace the data or append it? etc
# @balancing_router.put("/{id}")
# async def put_input_endpoint(input: data_input.InputData):
#     start = timer()
#     result_valid = False
#     result = balancer_control(input)
#     output = data_output.df_to_output(result, input.id)
#     log.info(f"received input data with id=<{input.id}>. Starting algorithm...")
#     return {"success": True}


@router.delete("/{id}")
async def delete_result_endpoint(id: str) -> JobComplete:
    try:
        result = await storage.delete(id)
    except HTTPException as exc:
        raise exc
    return result
