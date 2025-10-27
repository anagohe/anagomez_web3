import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
    const [numeros, setNumeros] = useState(['', '']);
    const [operacion, setOperacion] = useState('suma');
    const [resultado, setResultado] = useState(null);
    const [historial, setHistorial] = useState([]);
    const [error, setError] = useState('');

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
            fetchHistorial();
        } catch (err) {
            setError(err.message);
        }
    };
    
    const fetchHistorial = async () => {
        try {
            const response = await fetch(`${API_URL}/historial`);
            const data = await response.json();
            setHistorial(data.reverse()); // Muestra los más nuevos primero
        } catch (err) {
            console.error("Error al cargar el historial:", err);
        }
    };
    
    useEffect(() => {
        fetchHistorial();
    }, []);

    return (
        <div className="app-container">
            <h1>Calculadora</h1>
            <div className="card calculator-card">
                <div className="input-group">
                    <label htmlFor="operation-select">Operación:</label>
                    <select id="operation-select" value={operacion} onChange={e => setOperacion(e.target.value)}>
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
                        {numeros.length > 2 && <button className="btn-remove" onClick={() => quitarNumero(index)}>×</button>}
                    </div>
                ))}
                <div className="button-group">
                    <button className="btn btn-secondary" onClick={agregarNumero}>Añadir número</button>
                    <button className="btn btn-primary" onClick={calcular}>Calcular</button>
                </div>
            </div>

            {error && <div className="card error-card"><p>Error: {error}</p></div>}
            {resultado !== null && <div className="card result-card"><h2>Resultado: {resultado}</h2></div>}

            <div className="history-section">
                <div className="history-header">
                    <h2>Historial</h2>
                    <div>
                        <button className="btn btn-secondary" onClick={fetchHistorial}>Actualizar</button>
                        <button className="btn btn-danger" onClick={borrarHistorial}>Borrar Historial</button>
                    </div>
                </div>
                <ul className="history-list">
                    {historial.length > 0 ? historial.map(item => (
                        <li key={item._id} className="card history-item">
                            <span className="history-op">{item.operacion.charAt(0).toUpperCase() + item.operacion.slice(1)}</span>
                            <span className="history-nums">{item.numeros.join(` ${getOperationSymbol(item.operacion)} `)} = <strong>{item.resultado}</strong></span>
                            <span className="history-date">{new Date(item.fecha).toLocaleString()}</span>
                        </li>
                    )) : <p>El historial está vacío.</p>}
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