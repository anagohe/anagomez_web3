import os
from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.errors import PyMongoError
from typing import List, Optional
from datetime import datetime
import operator
from functools import reduce
import logging
from time import perf_counter
from prometheus_client import Counter, Histogram

from app.models import Operacion, OperacionBatch, OperacionDB
from prometheus_fastapi_instrumentator import Instrumentator

# --- APP ---
app = FastAPI(
    title="API de Calculadora",
    description="Una API para realizar operaciones matemáticas y guardar un historial.",
    version="1.0.0"
)

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("calculator_app")

# --- MÉTRICAS CUSTOM ---
OPERATIONS_TOTAL = Counter(
    "calculator_operations_total",
    "Total de operaciones aritméticas procesadas",
    ["operation", "status"],  # status = success / error
)

OPERATION_DURATION = Histogram(
    "calculator_operation_duration_seconds",
    "Duración de las operaciones aritméticas en segundos",
    ["operation"],
)

# --- METRICS (Instrumentator general) ---
Instrumentator().instrument(app).expose(app)

# --- CORS ---
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

# --- LÓGICA DE OPERACIONES ---
def procesar_operacion(op_nombre: str, numeros: List[float], calculo_func):
    """
    Procesa una operación, la guarda en la BD, genera logs y métricas de éxito/error.
    """
    start_time = perf_counter()

    # Validación de negocio: números negativos
    if any(n < 0 for n in numeros):
        duration = perf_counter() - start_time
        # Métricas
        OPERATIONS_TOTAL.labels(operation=op_nombre, status="error").inc()
        OPERATION_DURATION.labels(operation=op_nombre).observe(duration)

        logger.error(
            "operation_error | Números negativos no permitidos",
            extra={
                "operation": op_nombre,
                "operands": numeros,
                "error_type": "NEGATIVE_NUMBER",
            },
        )
        raise HTTPException(
            status_code=400,
            detail={"error": "Los números negativos no son permitidos.", "operandos": numeros},
        )

    try:
        resultado = calculo_func(numeros)

        operacion_log = {
            "operacion": op_nombre,
            "numeros": numeros,
            "resultado": resultado,
            "fecha": datetime.utcnow(),
        }

        historial_collection.insert_one(operacion_log)

        duration = perf_counter() - start_time
        # Métricas
        OPERATIONS_TOTAL.labels(operation=op_nombre, status="success").inc()
        OPERATION_DURATION.labels(operation=op_nombre).observe(duration)

        logger.info(
            "operation_success",
            extra={
                "operation": op_nombre,
                "operands": numeros,
                "result": resultado,
            },
        )

        return {"resultado": resultado}

    except PyMongoError as e:
        duration = perf_counter() - start_time
        OPERATIONS_TOTAL.labels(operation=op_nombre, status="error").inc()
        OPERATION_DURATION.labels(operation=op_nombre).observe(duration)

        logger.error(
            "db_error | Error al guardar operación en MongoDB",
            extra={
                "operation": op_nombre,
                "operands": numeros,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "Error al guardar la operación en la base de datos."},
        ) from e

    except Exception as e:
        duration = perf_counter() - start_time
        OPERATIONS_TOTAL.labels(operation=op_nombre, status="error").inc()
        OPERATION_DURATION.labels(operation=op_nombre).observe(duration)

        logger.exception(
            "unexpected_error | Error inesperado al procesar operación",
            extra={
                "operation": op_nombre,
                "operands": numeros,
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "Ocurrió un error inesperado al procesar la operación."},
        ) from e


@app.post("/suma")
def sumar(operacion: Operacion = Body(...)):
    return procesar_operacion("suma", operacion.numeros, lambda nums: sum(nums))


@app.post("/resta")
def restar(operacion: Operacion = Body(...)):
    if not operacion.numeros:
        raise HTTPException(
            status_code=400,
            detail={"error": "Se requiere al menos un número."},
        )
    return procesar_operacion("resta", operacion.numeros, lambda nums: nums[0] - sum(nums[1:]))


@app.post("/multiplicacion")
def multiplicar(operacion: Operacion = Body(...)):
    return procesar_operacion("multiplicacion", operacion.numeros, lambda nums: reduce(operator.mul, nums, 1))


@app.post("/division")
def dividir(operacion: Operacion = Body(...)):
    numeros = operacion.numeros

    if not numeros:
        # Métrica de error
        OPERATIONS_TOTAL.labels(operation="division", status="error").inc()

        logger.error(
            "operation_error | Lista vacía en división",
            extra={
                "operation": "division",
                "operands": numeros,
                "error_type": "EMPTY_LIST",
            },
        )
        raise HTTPException(
            status_code=400,
            detail={"error": "Se requiere al menos un número."},
        )

    if any(n == 0 for n in numeros[1:]):
        # Métrica de error
        OPERATIONS_TOTAL.labels(operation="division", status="error").inc()

        logger.error(
            "operation_error | División por cero",
            extra={
                "operation": "division",
                "operands": numeros,
                "error_type": "DIVISION_BY_ZERO",
            },
        )
        raise HTTPException(
            status_code=403,
            detail={"error": "La división por cero no está permitida.", "operandos": numeros},
        )

    # Si pasa las validaciones, el resto (duración, success/error) lo lleva procesar_operacion
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

    try:
        cursor = historial_collection.find(query)
        if sort_params:
            cursor = cursor.sort(sort_params)

        resultados = list(cursor)

        logger.info(
            "history_success",
            extra={
                "filter_operation": tipo or "ALL",
                "order_date": orden_fecha or "NONE",
                "order_result": orden_resultado or "NONE",
                "items_count": len(resultados),
            },
        )

        return resultados

    except PyMongoError as e:
        logger.error(
            "history_db_error | Error al consultar historial en MongoDB",
            extra={
                "filter_operation": tipo or "ALL",
                "order_date": orden_fecha or "NONE",
                "order_result": orden_resultado or "NONE",
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "Error al consultar el historial en la base de datos."},
        ) from e


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
    logger.info("history_cleared")
    return {"mensaje": "Historial borrado"}
