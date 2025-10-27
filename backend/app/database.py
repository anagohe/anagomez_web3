import pymongo
import os
from datetime import datetime

client = pymongo.MongoClient(os.getenv("DATABASE_URL"))
db = client.calculator_db

def save_operation(operation: str, result: float, operands: list):
    """Guarda una operación en la colección 'historial'."""
    db.historial.insert_one({
        "operation": operation,
        "operands": operands,
        "result": result,
        "created_at": datetime.utcnow()
    })