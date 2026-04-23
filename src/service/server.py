# The pymfm framework — FastAPI application entry point.

import logging
import os
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.responses import RedirectResponse
from werkzeug.security import check_password_hash, generate_password_hash

from pymfm.config import settings
from measurement.router.measurement import router as meas_router
from service.routers.balancing import router as balancing_router
from service.storage import FileStorage, MemoryStorage
from service.storage.redis_backend import RedisStorage

log = logging.getLogger("server")
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
logging.getLogger("werkzeug").setLevel(logging.WARNING)

# Auth

security = HTTPBasic()

_users = {
    settings.auth_username: generate_password_hash(settings.auth_password)
}


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    hashed = _users.get(credentials.username)
    if hashed and check_password_hash(hashed, credentials.password):
        return credentials.username
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Basic"},
    )


# ---------------------------------------------------------------------------
# Storage — override STORAGE_BACKEND env var to switch implementations:
#   "redis"   → RedisStorage
#   "memory"  → MemoryStorage
#   anything else (default) → FileStorage
# ---------------------------------------------------------------------------

_backend = os.environ.get("STORAGE_BACKEND", "file").lower()
if _backend == "redis":
    storage = RedisStorage()
elif _backend == "memory":
    storage = MemoryStorage()
else:
    storage = FileStorage(filepath=Path(__file__).parent / "store")

# Make storage accessible to routers
import service.routers.balancing as _balancing_module
_balancing_module.storage = storage

# App

app = FastAPI(title="pymfm balancing service")


@app.get("/health", tags=["meta"])
def health() -> str:
    return "ok"


@app.get("/", include_in_schema=False)
def redirect_to_docs():
    return RedirectResponse(url="/docs")


auth_dep = [Depends(get_current_username)]
app.include_router(balancing_router, prefix="/balancing", dependencies=auth_dep)
app.include_router(meas_router, prefix="/measurement", dependencies=auth_dep)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
