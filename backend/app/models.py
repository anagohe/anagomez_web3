from pydantic import BaseModel, Field, ConfigDict
from typing import List
from datetime import datetime
from bson import ObjectId

class Operacion(BaseModel):
    numeros: List[float] = Field(..., example=[10, 5, 2])

class OperacionBatch(BaseModel):
    op: str = Field(..., example="suma")
    nums: List[float] = Field(..., example=[10, 20])

class OperacionDB(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    operacion: str
    numeros: List[float]
    resultado: float
    fecha: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

