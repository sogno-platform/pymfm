# In-memory storage backend — useful for testing and local development.

from typing import Dict, List, Optional

from service import models
from service.storage.base import AsyncStorage


class MemoryStorage(AsyncStorage):
    """Stores jobs in a plain Python dict (not persistent across restarts)."""

    def __init__(self):
        self._data: Dict[str, models.JobComplete] = {}

    async def all_ids(self) -> List[str]:
        return list(self._data.keys())

    async def store(self, job: models.JobComplete) -> models.JobComplete:
        self._data[job.id] = job
        return job

    async def read(self, id: str) -> Optional[models.JobComplete]:
        return self._data.get(id)

    async def delete(self, id: str) -> Optional[models.JobComplete]:
        return self._data.pop(id, None)
