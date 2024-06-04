import logging
import os
from typing import List
import uvicorn

# import data_aux
from pymfm.control.utils import data_input, data_output
from pymfm.control.utils.mode_logic_handler import mode_logic_handler
from .crud_redis import delete_job, get_job, get_job_ids, save_job  # XXX relative imports?
from .data_aux import JobComplete, Status
from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# from crud_fs import save_result, delete_result, get_result , get_latest, clean_up
from starlette.responses import RedirectResponse
from werkzeug.security import check_password_hash, generate_password_hash


log = logging.getLogger("server")
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
logging.getLogger("werkzeug").setLevel(logging.WARNING)

security = HTTPBasic()


users = {
    os.environ.get("BALANCING_USERNAME", "admin"): generate_password_hash(os.environ.get("BALANCING_PASSWORD", "admin"))
}


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username in users:
        if check_password_hash(users.get(credentials.username), credentials.password):
            return credentials.username

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Basic"},
    )


app = FastAPI()

balancing_router = APIRouter(tags=["balancing"], dependencies=[Depends(get_current_username)])

# XXX handle this via settings in the future


async def do_balancing(job: JobComplete):
    try:
        job.status = Status.RUNNING
        await save_job(job)
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
    await save_job(job)


@balancing_router.post("/")
async def create_balancing_task(input: data_input.InputData, background_tasks: BackgroundTasks) -> JobComplete:
    log.info(f"received input data with id=<{input.id}>. Starting algorithm...")
    job = JobComplete(id=input.id, input=input)
    await save_job(job)
    background_tasks.add_task(do_balancing, job=job)
    return job


@balancing_router.get("/", description="get the ids of all jobs")
async def get_ids_endpoint() -> List[str]:
    return await get_job_ids()


@balancing_router.get("/{id}")
async def get_result_endpoint(id: str) -> JobComplete:
    output = await get_job(id)
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


@balancing_router.delete("/{id}")
async def delete_result_endpoint(id: str) -> JobComplete:
    try:
        result = await get_job(id)
        await delete_job(id)
    except HTTPException as exc:
        raise exc
    return result


@app.get("/health")
def health() -> str:
    return "ok"


@app.get("/")
def redirect_to_docs():
    """Redirect users to the docs of the default API version (typically the latest)"""
    redirect_url = "/docs"  # replace with docs URL or use app.url_path_for()
    return RedirectResponse(url=redirect_url)


app.include_router(balancing_router, prefix="/balancing")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)