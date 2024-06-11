from abc import ABC, abstractmethod
from typing import List

from service import data_aux


class AsyncStorage(ABC):
    # @abstractmethod
    # async def connect(self):
    #     pass

    @abstractmethod
    async def store(self, job: data_aux.JobComplete) -> data_aux.JobComplete:
        pass

    @abstractmethod
    async def read(self, id: str) -> data_aux.JobComplete:
        pass

    @abstractmethod
    async def delete(self, id: str) -> data_aux.JobComplete:
        pass

    @abstractmethod
    async def all_ids(self) -> List[str]:
        pass
