from common.schema import Index
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel
from typing import Literal
import os, abc


# 추후 생명주기 관리 편의를 위해 BaseIndexCalculator를 둘 수 있지만, 현재는 불필요해 보임.
class BaseIndexCalculator(BaseModel):
    objective: Literal["rcr", "rqs", "ohs"]
    threshold = os.getinv(objective + "_THRESHOLD", 70)

    @abc.abstractmethod
    async def calculate(self) -> Index:
        pass