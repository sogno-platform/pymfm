import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from pymfm.control.algorithms.controller import (
    scheduling_or_real_time,
    update_soc_internal,
)
from pymfm.control.schemas.input import BatterySpecs, InputData
from service.models import JobComplete
from service.storage.base import AsyncStorage
from service.storage.filesystem import FileStorage

log = logging.getLogger("server")

router = APIRouter(tags=["balancing"])

# Default storage — overridden by server.py at startup.
storage: AsyncStorage = FileStorage(filepath=Path(__file__).parent.parent / "store")


@router.post("/", response_model=JobComplete)
async def create_balancing_task(
    input: InputData, background_tasks: BackgroundTasks
) -> JobComplete:
    log.info("Received input with id=%s", input.id)
    job = JobComplete(id=input.id, input=input)
    await storage.store(job)
    background_tasks.add_task(scheduling_or_real_time, job=job, storage=storage)
    return job


@router.get("/", description="get the ids of all jobs")
async def get_ids() -> List[str]:
    return await storage.all_ids()


@router.get("/{id}", response_model=JobComplete)
async def get_job(id: str) -> JobComplete:
    job = await storage.read(id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No job with id '{id}'.")
    return job


#### ENDPOINTS FOR BATTERIES ####
@router.post("/{job_id}/battery_specs", response_model=JobComplete)
async def replace_batteries(job_id: str, new_specs: List[BatterySpecs]) -> JobComplete:
    """Replace ALL battery specs from the job with new ones.
    None of the existing batteries will be kept.

    Parameters
    ----------
    new_specs : list[BatterySpecs]
        New list of Batteries

    Raises
    ------
    NotImplementedError
        Currently not implemented
    """
    job = await _get_job_or_404(job_id)
    job.input.battery_specs = new_specs
    return await storage.store(job)


@router.put("/{job_id}/battery_specs", response_model=JobComplete)
async def update_batteries(
    job_id: str, new_specs: List[BatterySpecs] | BatterySpecs
) -> JobComplete:
    job = await _get_job_or_404(job_id)
    if isinstance(new_specs, BatterySpecs):
        new_specs = [new_specs]
    # TODO handle battery.id is None, currently just ignored
    new_ids = {bat.id for bat in new_specs}
    # XXX not sure how liniting thinks bat might be a tuple
    combined = [bat for bat in job.input.battery_specs if bat.id not in new_ids] + new_specs
    job.input.battery_specs = combined
    return await storage.store(job)


@router.delete("/{job_id}/battery_specs", response_model=JobComplete)
async def delete_battery(job_id: str, battery_id: str) -> JobComplete:
    job = await _get_job_or_404(job_id)
    # XXX not sure how liniting thinks bat might be a tuple
    job.input.battery_specs = [
        bat for bat in job.input.battery_specs if bat.id != battery_id
    ]
    return await storage.store(job)


# TODO We probably need to make battery ids non optional
@router.put("/{job_id}/battery_specs/soc", response_model=JobComplete)
async def update_soc(job_id: str, battery_id: str, soc: float) -> JobComplete:
    job = await _get_job_or_404(job_id)
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


@router.delete("/{id}", response_model=JobComplete)
async def delete_job(id: str) -> JobComplete:
    try:
        return await storage.delete(id)
    except FileNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No job with id '{id}'.")


async def _get_job_or_404(job_id: str) -> JobComplete:
    job = await storage.read(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No job with id '{job_id}'.")
    return job
