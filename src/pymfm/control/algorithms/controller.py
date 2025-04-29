import asyncio

import datetime

import pandas as pd
from measurement.router.query import get_data
from service.crud import AsyncStorage
from service.data_aux import JobComplete, Status

from pymfm.control.algorithms.exc import InfeasableError
from pymfm.control.utils.data_input import GenerationAndLoad, OperationMode
from pymfm.control.utils.mode_logic_handler import mode_logic_handler, prep_data


JOB_FREQ = 5 * 60



# XXX doing this one soc at a time is very inefficient
async def update_soc_internal(job: JobComplete, battery_id: str, soc: float):
    # XXX not sure how liniting thinks bat might be a tuple
    for bat in job.input.battery_specs:
        if bat.id == battery_id:
            bat.initial_SoC = soc
    return job


def combine_prediction_measurement(df_gen_load: pd.DataFrame, meas: pd.DataFrame | None = None):
    if meas is None:
        return df_gen_load
    last_meas = max(meas.index)
    ind = df_gen_load.index.get_indexer([last_meas], method="pad")[-1]
    # XXX does this need to check for ind + 1 >= len(df)?
    rel_position = (last_meas - df_gen_load.index[ind]) / (df_gen_load.index[ind + 1] - df_gen_load.index[ind])
    interpolation = (1 - rel_position) * (
        df_gen_load.P_required_kW.iloc[ind] - df_gen_load.P_available_kW.iloc[ind]
    ) + rel_position * (df_gen_load.P_required_kW.iloc[ind + 1] - df_gen_load.P_available_kW.iloc[ind + 1])
    correction = interpolation - meas.value[last_meas]
    # XXX should we copy the df?
    df_gen_load.P_required_kW = df_gen_load.P_required_kW.copy()
    df_gen_load.P_available_kW = df_gen_load.P_available_kW.copy()
    # 1. Add correction to generation/net access if any is expected
    df_gen_load.P_available_kW[df_gen_load.P_available_kW != 0] += correction
    # 2. Else subtract it to required power
    df_gen_load.P_required_kW[df_gen_load.P_available_kW == 0] = (
        df_gen_load.P_required_kW[df_gen_load.P_available_kW == 0] - correction
    )
    # 3. generation can not be negative shift both by the access amount
    df_gen_load.P_required_kW[df_gen_load.P_available_kW < 0] -= df_gen_load.P_available_kW[
        df_gen_load.P_available_kW < 0
    ]
    df_gen_load.P_available_kW[df_gen_load.P_available_kW < 0] = 0.0

    return df_gen_load



async def do_balancing(job: JobComplete, storage: AsyncStorage):
    try:
        job.status = Status.RUNNING
        await storage.store(job)

        day_end = job.input.day_end
        bulk = job.input.bulk
        id = job.input.id
        use_pv_curtailment = job.input.generation_and_load.pv_curtailment
        meas = get_data(job.input.measurement) if job.input.measurement else None
        df_gen_load, df_battery_specs, delta_T_h = prep_data(job.input)
        if meas is None:
            # XXX technically we are adjusting the user input here, this should be a priviledge only of the user
            t_start = job.input.control_start
        else:
            t_start = max(meas.index[-1], job.input.control_start)
        trunc_df = df_gen_load[: job.input.control_end][t_start:]
        trunc_df_adjusted = combine_prediction_measurement(trunc_df, meas)
        result, (status, details) = mode_logic_handler(
            trunc_df_adjusted, df_battery_specs, delta_T_h, day_end, bulk, use_pv_curtailment, id
        )


        if status == "ok":
            job.status = Status.SUCCESS
            job.result = result
            job.details = details

            # XXX this will result in major errors if schedule and execution timesteps are different
            for bat_id, soc in result.schedule[1].soc_bat.items():  # index 0 is initial, index 1 is "next step"
                job = await update_soc_internal(job, bat_id, soc)
        else:
            job.status = Status.FAILED
            job.details = details
    except InfeasableError:
        job.status = Status.FAILED
        job.details = "There were no feasable solutions to the stated conditions."

    except Exception as exc:
        job.status = Status.FAILED
        job.details = "Job was parsed but could not be executed."
    job.finished = datetime.datetime.now(datetime.timezone.utc)
    await storage.store(job)
    return job


async def scheduling_or_real_time(job: JobComplete, storage: AsyncStorage, meas: pd.DataFrame = None):
    if job.input.operation_mode == OperationMode.NEAR_REAL_TIME:
        await asyncio.sleep((job.input.job_start - datetime.datetime.now(datetime.timezone.utc)).total_seconds())
        while job.input.job_end > datetime.datetime.now(datetime.timezone.utc):
            job.input.control_start = datetime.datetime.now(datetime.timezone.utc)
            await do_balancing(job, storage)
            await asyncio.sleep(job.input.repeat_seconds)
    else:
        await do_balancing(job, storage)


def run_sync(job: JobComplete, storage: AsyncStorage):
    return asyncio.run(scheduling_or_real_time, job=job, storage=storage)
