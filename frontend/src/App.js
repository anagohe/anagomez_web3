import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
    const [numeros, setNumeros] = useState(['', '']);
    const [operacion, setOperacion] = useState('suma');
    const [resultado, setResultado] = useState(null);
    const [historial, setHistorial] = useState([]);
    const [error, setError] = useState('');

    // NUEVOS estados para filtros
    const [filtroTipo, setFiltroTipo] = useState('');
    const [ordenFecha, setOrdenFecha] = useState('');
    const [ordenResultado, setOrdenResultado] = useState('');

    const API_URL = 'http://localhost:8000';

    const handleNumeroChange = (index, value) => {
        const nuevosNumeros = [...numeros];
        nuevosNumeros[index] = value;
        setNumeros(nuevosNumeros);
    };

    const agregarNumero = () => {
        setNumeros([...numeros, '']);
    };

    const quitarNumero = (index) => {
        if (numeros.length > 2) {
            const nuevosNumeros = numeros.filter((_, i) => i !== index);
            setNumeros(nuevosNumeros);
        }
    };

    const borrarHistorial = async () => {
        const confirmado = window.confirm(
            "¿Estás seguro de que quieres borrar todo el historial? Esta acción no se puede deshacer."
        );
        if (confirmado) {
            try {
                const response = await fetch(`${API_URL}/historial`, {
                    method: 'DELETE',
                });
                if (!response.ok) {
                    throw new Error("No se pudo borrar el historial.");
                }
                setHistorial([]);
            } catch (err) {
                setError(err.message);
            }
        }
    };

    const calcular = async () => {
        setError('');
        setResultado(null);
        try {
            const numerosValidos = numeros.map(n => parseFloat(n)).filter(n => !isNaN(n));
            if (numerosValidos.length < 2) {
                setError('Se requieren al menos dos números válidos.');
                return;
            }
            const response = await fetch(`${API_URL}/${operacion}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ numeros: numerosValidos }),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail?.error || 'Ocurrió un error');
            }
            setResultado(data.resultado);
            // Después de calcular, recargar historial respetando filtros actuales
            fetchHistorial();
        } catch (err) {
            setError(err.message);
        }
    };

    const fetchHistorial = async () => {
        try {
            // Construimos los query params según los filtros seleccionados
            const params = new URLSearchParams();
            if (filtroTipo) params.append('tipo', filtroTipo);
            if (ordenFecha) params.append('orden_fecha', ordenFecha);
            if (ordenResultado) params.append('orden_resultado', ordenResultado);

            const url = `${API_URL}/historial${params.toString() ? `?${params.toString()}` : ''}`;

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error('Error al cargar el historial');
            }
            const data = await response.json();
            // YA NO hacemos reverse(); el orden lo decide el backend según los filtros
            setHistorial(data);
        } catch (err) {
            console.error("Error al cargar el historial:", err);
        }
    };

    useEffect(() => {
        fetchHistorial();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return (
        <div className="app-container">
            <h1>Calculadora</h1>

            {/* --- TARJETA DE CALCULADORA --- */}
            <div className="card calculator-card">
                <div className="input-group">
                    <label htmlFor="operation-select">Operación:</label>
                    <select
                        id="operation-select"
                        value={operacion}
                        onChange={e => setOperacion(e.target.value)}
                    >
                        <option value="suma">Suma (+)</option>
                        <option value="resta">Resta (-)</option>
                        <option value="multiplicacion">Multiplicación (*)</option>
                        <option value="division">División (/)</option>
                    </select>
                </div>

                {numeros.map((num, index) => (
                    <div key={index} className="input-row">
                        <input
                            type="number"
                            placeholder={`Número ${index + 1}`}
                            value={num}
                            onChange={e => handleNumeroChange(index, e.target.value)}
                        />
                        {numeros.length > 2 && (
                            <button
                                className="btn-remove"
                                onClick={() => quitarNumero(index)}
                            >
                                ×
                            </button>
                        )}
                    </div>
                ))}

                <div className="button-group">
                    <button className="btn btn-secondary" onClick={agregarNumero}>
                        Añadir número
                    </button>
                    <button className="btn btn-primary" onClick={calcular}>
                        Calcular
                    </button>
                </div>
            </div>

            {error && (
                <div className="card error-card">
                    <p>Error: {error}</p>
                </div>
            )}

            {resultado !== null && (
                <div className="card result-card">
                    <h2>Resultado: {resultado}</h2>
                </div>
            )}

            {/* --- SECCIÓN DE HISTORIAL --- */}
            <div className="history-section">
                <div className="history-header">
                    <h2>Historial</h2>
                    <div className="history-header-buttons">
                        <button className="btn btn-secondary" onClick={fetchHistorial}>
                            Aplicar filtros
                        </button>
                        <button className="btn btn-danger" onClick={borrarHistorial}>
                            Borrar Historial
                        </button>
                    </div>
                </div>

                {/* FILTROS DE HISTORIAL */}
                <div className="history-filters">
                    <div className="filter-item">
                        <label>Filtrar por operación:</label>
                        <select
                            value={filtroTipo}
                            onChange={e => setFiltroTipo(e.target.value)}
                        >
                            <option value="">Todas</option>
                            <option value="suma">Suma</option>
                            <option value="resta">Resta</option>
                            <option value="multiplicacion">Multiplicación</option>
                            <option value="division">División</option>
                        </select>
                    </div>

                    <div className="filter-item">
                        <label>Ordenar por fecha:</label>
                        <select
                            value={ordenFecha}
                            onChange={e => setOrdenFecha(e.target.value)}
                        >
                            <option value="">Sin ordenar</option>
                            <option value="asc">Más antiguas primero</option>
                            <option value="desc">Más recientes primero</option>
                        </select>
                    </div>

                    <div className="filter-item">
                        <label>Ordenar por resultado:</label>
                        <select
                            value={ordenResultado}
                            onChange={e => setOrdenResultado(e.target.value)}
                        >
                            <option value="">Sin ordenar</option>
                            <option value="asc">Menor a mayor</option>
                            <option value="desc">Mayor a menor</option>
                        </select>
                    </div>
                </div>

                <ul className="history-list">
                    {historial.length > 0 ? (
                        historial.map(item => (
                            <li key={item._id} className="card history-item">
                                <span className="history-op">
                                    {item.operacion.charAt(0).toUpperCase() + item.operacion.slice(1)}
                                </span>
                                <span className="history-nums">
                                    {item.numeros.join(` ${getOperationSymbol(item.operacion)} `)} ={' '}
                                    <strong>{item.resultado}</strong>
                                </span>
                                <span className="history-date">
                                    {new Date(item.fecha).toLocaleString()}
                                </span>
                            </li>
                        ))
                    ) : (
                        <p>El historial está vacío.</p>
                    )}
                </ul>
            </div>
        </div>
    );
}

function getOperationSymbol(op) {
    const symbols = { suma: '+', resta: '-', multiplicacion: '×', division: '÷' };
    return symbols[op] || '?';
}

export default App;
