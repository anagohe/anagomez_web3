
import os
from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient, DESCENDING, ASCENDING
from typing import List, Optional
from datetime import datetime
import operator
from functools import reduce

from app.models import Operacion, OperacionBatch, OperacionDB
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(
    title="API de Calculadora",
    description="Una API para realizar operaciones matemáticas y guardar un historial.",
    version="1.0.0"
)

Instrumentator().instrument(app).expose(app)

origins = ["http://localhost", "http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONEXIÓN A LA BASE DE DATOS ---
MONGO_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
client = MongoClient(MONGO_URL)
db = client.calculadora_db
historial_collection = db.historial

# --- LÓGICA DE OPERACIONES (sin cambios) ---
def procesar_operacion(op_nombre: str, numeros: List[float], calculo_func):
    if any(n < 0 for n in numeros):
        raise HTTPException(status_code=400, detail={"error": "Los números negativos no son permitidos.", "operandos": numeros})
    resultado = calculo_func(numeros)
    operacion_log = {"operacion": op_nombre, "numeros": numeros, "resultado": resultado, "fecha": datetime.utcnow()}
    historial_collection.insert_one(operacion_log)
    return {"resultado": resultado}

@app.post("/suma")
def sumar(operacion: Operacion = Body(...)):
    return procesar_operacion("suma", operacion.numeros, lambda nums: sum(nums))

@app.post("/resta")
def restar(operacion: Operacion = Body(...)):
    if not operacion.numeros:
        raise HTTPException(status_code=400, detail={"error": "Se requiere al menos un número."})
    return procesar_operacion("resta", operacion.numeros, lambda nums: nums[0] - sum(nums[1:]))

@app.post("/multiplicacion")
def multiplicar(operacion: Operacion = Body(...)):
    return procesar_operacion("multiplicacion", operacion.numeros, lambda nums: reduce(operator.mul, nums, 1))

@app.post("/division")
def dividir(operacion: Operacion = Body(...)):
    numeros = operacion.numeros
    if not numeros:
        raise HTTPException(status_code=400, detail={"error": "Se requiere al menos un número."})
    if any(n == 0 for n in numeros[1:]):
        raise HTTPException(status_code=403, detail={"error": "La división por cero no está permitida.", "operandos": numeros})
    return procesar_operacion("division", numeros, lambda nums: reduce(operator.truediv, nums))


# --- HISTORIAL ---
@app.get("/historial", response_model=List[OperacionDB], summary="Obtiene el historial de operaciones")
def get_historial(
    tipo: Optional[str] = Query(None, description="Filtrar por tipo de operación (suma, resta, etc.)"),
    orden_fecha: Optional[str] = Query(None, description="Ordenar por fecha ('asc' o 'desc')"),
    orden_resultado: Optional[str] = Query(None, description="Ordenar por resultado ('asc' o 'desc')")
):
    query = {}
    if tipo:
        query["operacion"] = tipo
    
    sort_params = []
    if orden_fecha:
        sort_params.append(("fecha", ASCENDING if orden_fecha == "asc" else DESCENDING))
    if orden_resultado:
        sort_params.append(("resultado", ASCENDING if orden_resultado == "asc" else DESCENDING))
        
    cursor = historial_collection.find(query)
    if sort_params:
        cursor = cursor.sort(sort_params)
        
    return list(cursor)

# --- /batch ---
@app.post("/batch", summary="Procesa una lista de operaciones en lote")
def procesar_lote(operaciones: List[OperacionBatch] = Body(...)):
    resultados = []
    for op in operaciones:
        try:
            if op.op == "suma":
                res = sumar(Operacion(numeros=op.nums))
            elif op.op == "resta":
                res = restar(Operacion(numeros=op.nums))
            elif op.op == "multiplicacion":
                res = multiplicar(Operacion(numeros=op.nums))
            elif op.op == "division":
                res = dividir(Operacion(numeros=op.nums))
            else:
                raise HTTPException(status_code=400, detail=f"Operación no válida: {op.op}")
            
            resultados.append({"op": op.op, "result": res["resultado"]})

        except HTTPException as e:
            resultados.append({"op": op.op, "error": e.detail, "numeros": op.nums})
            
    return resultados

@app.delete("/historial")
def borrar_historial():
    historial_collection.delete_many({})
    return {"mensaje": "Historial borrado"}

