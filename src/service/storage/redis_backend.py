# Redis storage backend.

import json
import logging
from typing import List, Optional

import redis.asyncio as redis
from fastapi import HTTPException

from pymfm.config import settings
from service import models
from service.storage.base import AsyncStorage

log = logging.getLogger(__name__)


class RedisStorage(AsyncStorage):
    """Stores jobs as JSON strings in Redis."""

    def __init__(self):
        self._client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            decode_responses=True,
        )

    async def ping(self) -> bool:
        return await self._client.ping()

    async def store(self, job: models.JobComplete) -> models.JobComplete:
        await self._client.set(job.id, job.model_dump_json(by_alias=True))
        return job

    async def read(self, id: str) -> Optional[models.JobComplete]:
        raw = await self._client.get(id)
        if raw is None:
            return None
        try:
            return models.JobComplete.model_validate_json(raw)
        except json.JSONDecodeError:
            log.error("Corrupt Redis entry for key '%s'", id)
            raise HTTPException(500, "Unable to decode job details; contact the server admin.")

    async def all_ids(self) -> List[str]:
        return await self._client.keys()

    async def delete(self, id: str) -> Optional[models.JobComplete]:
        job = await self.read(id)
        await self._client.delete(id)
        return job
