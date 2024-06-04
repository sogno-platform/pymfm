# import asyncio
# import glob
import json
import logging
import os
from typing import List, Optional
import redis.asyncio as redis
from . import data_aux

# from balancer_utils import data_output
from fastapi import HTTPException, status

log = logging.getLogger("server.crud")

r_db = None


async def anext(ait):
    return await ait.__anext__()


async def get_db() -> redis.Redis:
    global r_db
    if r_db is None:
        r_db = await anext(connect_redis())
    return r_db


async def connect_redis():
    r_db = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True,
    )
    try:
        yield r_db
    finally:
        await r_db.close()


# r_db = next(connect_redis())


async def save_job(job: data_aux.JobComplete) -> data_aux.JobComplete:
    r_db = await get_db()
    await r_db.set(job.id, job.json(by_alias=True))
    return job


async def get_job(id: str) -> Optional[data_aux.JobComplete]:
    r_db = await get_db()
    res_json = await r_db.get(id)
    if res_json is None:
        return None
    try:
        ret = data_aux.JobComplete(**json.loads(res_json))
    except json.decoder.JSONDecodeError as err:
        raise HTTPException(
            500,
            "unable to decode job details, please try again or contact the server admin.",
        )
    return ret


async def get_job_ids() -> List[str]:
    r_db = await get_db()
    return await r_db.keys()


async def delete_job(id: str) -> data_aux.JobComplete:
    r_db = await get_db()
    await r_db.delete(id)
    
    


# def get_latest() -> data_output.BalancerOutputWrapper:
#     outpath = os.path.join(".","output","*")
#     list_of_files = glob.glob(outpath)
#     list_of_files.sort(key=os.path.getctime)
#     if len(list_of_files) == 0:
#         raise HTTPException(
#         status_code=status.HTTP_404_NOT_FOUND,
#         detail="No results available")
#     return get_result(list_of_files[0])

# def clean_up() -> List[str]:
#     outpath = os.path.join("output","*")
#     list_of_files = glob.glob(outpath)
#     list_of_files.sort(key=os.path.getctime)
#     to_delete = list_of_files[:-10]
#     for path in to_delete:
#         log.debug(f" delete {path}")
#         os.remove(path)
#     return to_delete
