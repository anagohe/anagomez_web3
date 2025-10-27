
import pytest
from fastapi.testclient import TestClient
from mongomock import MongoClient
from app.main import app

# --- CONFIGURACIÓN DE PRUEBAS ---

client = TestClient(app)

mock_client = MongoClient()
mock_db = mock_client.calculadora_db
mock_historial_collection = mock_db.historial


@pytest.fixture(autouse=True)
def override_db_with_monkeypatch(monkeypatch):
    """
    Usa monkeypatch para reemplazar la variable `historial_collection`
    dentro del módulo `app.main` con nuestra colección mock.
    Esto garantiza que la app use la base de datos simulada.
    """
    monkeypatch.setattr('app.main.historial_collection', mock_historial_collection)
    
    yield
    
    mock_historial_collection.delete_many({})


# --- OPERACIONES BÁSICAS ---

class TestOperations:
    def test_suma_exitosa(self):
        response = client.post("/suma", json={"numeros": [10, 5, 3]})
        assert response.status_code == 200
        assert response.json() == {"resultado": 18}
        assert mock_historial_collection.count_documents({"operacion": "suma"}) == 1

    def test_resta_exitosa(self):
        response = client.post("/resta", json={"numeros": [20, 5, 5]})
        assert response.status_code == 200
        assert response.json() == {"resultado": 10}
        assert mock_historial_collection.count_documents({"operacion": "resta"}) == 1

    def test_multiplicacion_exitosa(self):
        response = client.post("/multiplicacion", json={"numeros": [2, 3, 4]})
        assert response.status_code == 200
        assert response.json() == {"resultado": 24}
        assert mock_historial_collection.count_documents({"operacion": "multiplicacion"}) == 1
        
    def test_division_exitosa(self):
        response = client.post("/division", json={"numeros": [100, 10, 2]})
        assert response.status_code == 200
        assert response.json() == {"resultado": 5.0}
        assert mock_historial_collection.count_documents({"operacion": "division"}) == 1

    def test_error_division_por_cero(self):
        response = client.post("/division", json={"numeros": [10, 0]})
        assert response.status_code == 403
        assert "La división por cero no está permitida" in response.json()["detail"]["error"]
        assert mock_historial_collection.count_documents({}) == 0

    def test_error_numeros_negativos(self):
        response = client.post("/suma", json={"numeros": [10, -5]})
        assert response.status_code == 400
        assert "Los números negativos no son permitidos" in response.json()["detail"]["error"]
        assert response.json()["detail"]["operandos"] == [10, -5]
        assert mock_historial_collection.count_documents({}) == 0

    def test_error_lista_vacia_resta(self):
        response = client.post("/resta", json={"numeros": []})
        assert response.status_code == 400
        assert "Se requiere al menos un número" in response.json()["detail"]["error"]


# --- HISTORIAL ---

@pytest.fixture
def setup_history_data():
    """Inserta datos de prueba en la BD mock para las pruebas de historial."""
    mock_historial_collection.insert_many([
        {"operacion": "suma", "numeros": [1, 2], "resultado": 3, "fecha": "2025-01-01T10:00:00Z"},
        {"operacion": "resta", "numeros": [10, 5], "resultado": 5, "fecha": "2025-01-01T12:00:00Z"},
        {"operacion": "suma", "numeros": [10, 20], "resultado": 30, "fecha": "2025-01-01T11:00:00Z"}
    ])

class TestHistory:
    def test_get_historial_completo(self, setup_history_data):
        response = client.get("/historial")
        assert response.status_code == 200
        assert len(response.json()) == 3

    def test_filtrar_historial_por_tipo(self, setup_history_data):
        response = client.get("/historial?tipo=suma")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(item["operacion"] == "suma" for item in data)

    def test_ordenar_historial_por_resultado_asc(self, setup_history_data):
        response = client.get("/historial?orden_resultado=asc")
        assert response.status_code == 200
        results = [item["resultado"] for item in response.json()]
        assert results == [3, 5, 30]

    def test_ordenar_historial_por_fecha_desc(self, setup_history_data):
        response = client.get("/historial?orden_fecha=desc")
        assert response.status_code == 200
        fechas = [item["fecha"] for item in response.json()]
        assert fechas == ["2025-01-01T12:00:00Z", "2025-01-01T11:00:00Z", "2025-01-01T10:00:00Z"]


# --- PROCESAMIENTO EN LOTE  ---

class TestBatch:
    def test_batch_exitoso(self):
        operaciones = [
            {"op": "suma", "nums": [1, 2, 3]},
            {"op": "multiplicacion", "nums": [5, 5]}
        ]
        response = client.post("/batch", json=operaciones)
        assert response.status_code == 200
        data = response.json()
        assert data == [
            {"op": "suma", "result": 6},
            {"op": "multiplicacion", "result": 25}
        ]
        assert mock_historial_collection.count_documents({}) == 2

    def test_batch_con_errores(self):
        operaciones = [
            {"op": "suma", "nums": [10, 20]},
            {"op": "division", "nums": [10, 0]},
            {"op": "resta", "nums": [5, -2]}
        ]
        response = client.post("/batch", json=operaciones)
        assert response.status_code == 200
        data = response.json()
        
        assert data[0] == {"op": "suma", "result": 30}
        assert "La división por cero no está permitida" in data[1]["error"]["error"]
        assert "Los números negativos no son permitidos" in data[2]["error"]["error"]
        assert mock_historial_collection.count_documents({}) == 1
        assert mock_historial_collection.find_one({})["resultado"] == 30

    def test_batch_operacion_invalida(self):
        operaciones = [{"op": "potencia", "nums": [2, 3]}]
        response = client.post("/batch", json=operaciones)
        assert response.status_code == 200
        data = response.json()
        assert "Operación no válida: potencia" in data[0]["error"]