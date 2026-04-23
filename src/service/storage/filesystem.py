# File-system storage backend — persists each job as a JSON file.

import glob
import json
import logging
import os
from pathlib import Path
from typing import List, Optional, Union

from fastapi import HTTPException, status

from service import models
from service.storage.base import AsyncStorage

log = logging.getLogger(__name__)


class FileStorage(AsyncStorage):
    """Stores jobs as JSON files under *filepath* directory."""

    def __init__(self, filepath: Union[Path, str]):
        self.filepath = Path(filepath)
        self.filepath.mkdir(parents=True, exist_ok=True)

    def _path(self, id: str) -> Path:
        return self.filepath / f"{id}.json"

    async def all_ids(self) -> List[str]:
        return [
            Path(f).stem
            for f in glob.glob(str(self.filepath / "*.json"))
        ]

    async def store(self, job: models.JobComplete) -> models.JobComplete:
        self._path(job.id).write_text(job.model_dump_json(by_alias=True))
        return job

    async def read(self, id: str) -> Optional[models.JobComplete]:
        path = self._path(id)
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No job with id '{id}'.",
            )
        try:
            return models.JobComplete.model_validate_json(path.read_text())
        except json.JSONDecodeError:
            log.error("Corrupt job file: %s", path)
            raise HTTPException(
                status_code=500,
                detail="Unable to decode job details; contact the server admin.",
            )

    async def delete(self, id: str) -> Optional[models.JobComplete]:
        job = await self.read(id)
        self._path(id).unlink(missing_ok=True)
        return job
