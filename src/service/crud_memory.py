import glob
import json
import logging
import os
from pathlib import Path
from typing import List, Optional, Union
from service import data_aux
from service.crud import AsyncStorage

log = logging.getLogger("server.crud")


class MemoryStorage(AsyncStorage):
    def __init__(self):
        self.data = dict()

    async def all_ids(self):
        return list(self.data.keys())

    async def store(self, job: data_aux.JobComplete) -> data_aux.JobComplete:
        self.data[job.id] = job
        return job

    async def read(self, id: str) -> Optional[data_aux.JobComplete]:
       return self.data.get(id)

    async def delete(self, id: str) -> Optional[data_aux.JobComplete]:
        return self.data.pop(id)
