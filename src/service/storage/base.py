# Abstract storage interface — all backends must implement this.

from abc import ABC, abstractmethod
from typing import List, Optional

from service import models


class AsyncStorage(ABC):
    """Async key-value store for JobComplete objects."""

    @abstractmethod
    async def store(self, job: models.JobComplete) -> models.JobComplete:
        """Persist *job*, overwriting any existing entry with the same id."""
        ...

    @abstractmethod
    async def read(self, id: str) -> Optional[models.JobComplete]:
        """Return the job for *id*, or None if not found."""
        ...

    @abstractmethod
    async def delete(self, id: str) -> Optional[models.JobComplete]:
        """Delete and return the job for *id*, or None if not found."""
        ...

    @abstractmethod
    async def all_ids(self) -> List[str]:
        """Return all stored job ids."""
        ...
