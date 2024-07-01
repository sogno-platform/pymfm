import asyncio

import datetime

import pandas as pd
from pymfm.control.utils.data_input import GenerationAndLoad, OperationMode
from pymfm.control.utils.mode_logic_handler import mode_logic_handler, prep_data
from service.crud import AsyncStorage
from service.data_aux import JobComplete, Status

JOB_FREQ = 5 * 60


def combine_prediction_measurement(raw_input: GenerationAndLoad, meas: GenerationAndLoad = None):
    if meas is None:
        return raw_input
    raise NotImplementedError(
        "combining measurements and predicitons has not been implemented."
    )


async def do_balancing(job: JobComplete, storage: AsyncStorage):
    try:
        job.status = Status.RUNNING
        await storage.store(job)
        job.input = combine_prediction_measurement(job.input, None)
        result, (status, details) = mode_logic_handler(job.input)
        # out, status, details = data_output.df_to_output(result, job.id, status)
        if status == "ok":
            job.status = Status.SUCCESS
            job.result = result
            job.details = details
        else:
            job.status = Status.FAILED
            job.details = details
    except Exception as exc:
        job.status = Status.FAILED
        job.details = "Job was parsed but could not be executed."
    job.finished = datetime.datetime.now(datetime.timezone.utc)
    await storage.store(job)
    return job


async def scheduling_or_real_time(
    job: JobComplete, storage: AsyncStorage, meas: pd.DataFrame = None
):
    if job.input.operation_mode == OperationMode.NEAR_REAL_TIME:
        await asyncio.sleep(
            (
                job.input.job_start - datetime.datetime.now(datetime.timezone.utc)
            ).total_seconds()
        )
        while job.input.job_end > datetime.datetime.now(datetime.timezone.utc):
            await do_balancing(job, storage)
            await asyncio.sleep(job.input.repeat_seconds)
    else:
        await do_balancing(job, storage)


def run_sync(job: JobComplete, storage: AsyncStorage):
    return asyncio.run(scheduling_or_real_time, job=job, storage=storage)
