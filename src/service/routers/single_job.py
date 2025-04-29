import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException
from service.crud_fs import FileStorage
from service.crud_redis import RedisStorage
from service.data_aux import JobComplete

from pymfm.control.algorithms.controller import (do_balancing,

                                                 scheduling_or_real_time,
                                                 update_soc_internal)
from pymfm.control.utils.data_input import BatterySpecs, InputData


log = logging.getLogger("server")

router = APIRouter(
    tags=["balancing"],
)

# XXX handle this via settings in the future
storage = FileStorage(filepath=Path(__file__).parent.parent / "store")  # MemoryStorage() # RedisStorage()
# storage = RedisStorage()


@router.post("/")

async def create_balancing_task(input: InputData, background_tasks: BackgroundTasks) -> JobComplete:

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



#### ENDPOINTS FOR BATTERIES ####
@router.post("/{job_id}/battery_specs")
async def update_batteries(job_id: str, new_battery_specs: list[BatterySpecs]):
    """Replace ALL battery specs from the job with new ones.
    None of the existing batteries will be kept.

    Parameters
    ----------
    new_battery_specs : list[BatterySpecs]
        New list of Batteries

    Raises
    ------
    NotImplementedError
        Currently not implemented
    """
    job = await storage.read(job_id)
    assert job is not None, f"No Job with id {job_id}"
    assert job.input is not None, "This should never happen"
    job.input.battery_specs = new_battery_specs
    return await storage.store(job)


@router.put("/{job_id}/battery_specs")
async def update_battery_by_id(job_id: str, new_battery_specs: list[BatterySpecs] | BatterySpecs):
    job = await storage.read(job_id)
    assert job is not None, f"No Job with id {job_id}"
    assert job.input is not None, "This should never happen"
    # TODO handle battery.id is None, currently just ignored
    if isinstance(new_battery_specs, BatterySpecs):
        new_ids = [new_battery_specs.id]
    else:
        new_ids = [bat.id for bat in new_battery_specs]
    # XXX not sure how liniting thinks bat might be a tuple
    combined_specs = [bat for bat in job.input.battery_specs if bat.id not in new_ids] + new_battery_specs
    job.input.battery_specs = combined_specs
    return await storage.store(job)


@router.delete("/{job_id}/battery_specs")
async def update_battery_by_id(job_id: str, battery_id: str):
    job = await storage.read(job_id)
    assert job is not None, f"No Job with id {job_id}"
    assert job.input is not None, "This should never happen"
    # XXX not sure how liniting thinks bat might be a tuple
    combined_specs = [bat for bat in job.input.battery_specs if bat.id != battery_id]
    job.input.battery_specs = combined_specs
    return await storage.store(job)


# TODO We probably need to make battery ids non optional
@router.put("/{job_id}/battery_specs/soc")
async def update_soc(job_id: str, battery_id: str, soc: float):
    job = await storage.read(job_id)
    assert job is not None, f"No Job with id {job_id}"
    assert job.input is not None, "This should never happen"

    job = await update_soc_internal(job, battery_id, soc)
    return await storage.store(job)



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
