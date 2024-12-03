import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List

import uvicorn
from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# from pymfm.control.algorithms.controller import do_balancing, scheduling_or_real_time
from service.crud_fs import FileStorage
from service.crud_memory import MemoryStorage
from service.crud_redis import RedisStorage  # XXX relative imports?
from service.data_aux import JobComplete
from service.routers.single_job import router as balancing_router
from measurement.router.measurement import router as meas_router

# from crud_fs import save_result, delete_result, get_result , get_latest, clean_up
from starlette.responses import RedirectResponse
from werkzeug.security import check_password_hash, generate_password_hash

from pymfm.control.algorithms.controller import scheduling_or_real_time

# import data_aux
from pymfm.control.utils import data_input, data_output

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


# XXX handle this via settings in the future
storage = FileStorage(filepath=Path(__file__).parent / "store")  # MemoryStorage() # RedisStorage()
# storage = RedisStorage()


@app.get("/health")
def health() -> str:
    return "ok"


@app.get("/")
def redirect_to_docs():
    """Redirect users to the docs of the default API version (typically the latest)"""
    redirect_url = "/docs"  # replace with docs URL or use app.url_path_for()
    return RedirectResponse(url=redirect_url)


app.include_router(balancing_router, prefix="/balancing", dependencies=[Depends(get_current_username)])
app.include_router(meas_router, prefix="/measurement", dependencies=[Depends(get_current_username)])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
