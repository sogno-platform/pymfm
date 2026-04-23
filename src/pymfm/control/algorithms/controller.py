import asyncio
import datetime

import pandas as pd

from measurement.router.query import get_data
from service.storage.base import AsyncStorage
from service.models import JobComplete, Status

from pymfm.control.exceptions import InfeasibleError
from pymfm.control.schemas.input import BatterySpecs, OperationMode
from pymfm.control.utils.data_prep import build_algorithm, prep_data, run_algorithm


# XXX doing this one soc at a time is very inefficient
async def update_soc_internal(job: JobComplete, battery_id: str, soc: float):
    if isinstance(job.input.battery_specs, BatterySpecs):
        job.input.battery_specs.initial_SoC = soc
        return job
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
    df = df_gen_load.copy()
    # 1. Add correction to generation/net access if any is expected
    has_gen = df.P_available_kW != 0
    df.loc[has_gen, "P_available_kW"] += correction
    # 2. Else subtract it to required power
    df.loc[~has_gen, "P_required_kW"] -= correction
    # 3. generation can not be negative shift both by the access amount
    neg_gen = df.P_available_kW < 0
    df.loc[neg_gen, "P_required_kW"] -= df.loc[neg_gen, "P_available_kW"]
    df.loc[neg_gen, "P_available_kW"] = 0.0
    return df


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

        algorithm = build_algorithm(job.input.control_logic)
        result, (status, details) = run_algorithm(
            algorithm=algorithm,
            timeseries=trunc_df_adjusted,
            df_battery_specs=df_battery_specs,
            delta_T_h=delta_T_h,
            day_end=day_end,
            bulk=bulk,
            pv_curtailment=use_pv_curtailment,
            job_id=id,
        )

        if status == "ok":
            job.status = Status.SUCCESS
            job.result = result
            job.details = details

            # XXX this will result in major errors if schedule and execution timesteps are different
            if job.input.operation_mode == OperationMode.NEAR_REAL_TIME:
                for bat_id, soc in result.schedule[1].soc_bat.items():  # index 0 is initial, index 1 is "next step"
                    job = await update_soc_internal(job, bat_id, soc)
        else:
            job.status = Status.FAILED
            job.details = details
    except InfeasibleError:
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
        delay = (job.input.job_start - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
        await asyncio.sleep(max(0.0, delay))
        while job.input.job_end > datetime.datetime.now(datetime.timezone.utc):
            try:
                await storage.read(job.id)
            except Exception:
                break
            job.input.control_start = datetime.datetime.now(datetime.timezone.utc)
            await do_balancing(job, storage)
            await asyncio.sleep(job.input.repeat_seconds or 0)
    else:
        await do_balancing(job, storage)


def run_sync(job: JobComplete, storage: AsyncStorage):
    asyncio.run(scheduling_or_real_time(job=job, storage=storage))
