
import React from 'react'; 
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from './App';


beforeEach(() => {
    global.fetch = jest.fn();
});

// Prueba 1: El componente se renderiza correctamente
test('renderiza el título de la calculadora', async () => {
    fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
    });
    
    render(<App />);
        const titulo = await screen.findByText(/Calculadora Web Moderna/i);
    expect(titulo).toBeInTheDocument();
});

// Prueba 2: Realiza una suma exitosa al hacer clic en Calcular
test('realiza una suma y muestra el resultado correcto', async () => {
    fetch.mockResolvedValueOnce({ ok: true, json: async () => [] });
    render(<App />);
    await screen.findByText('Calcular'); 
    const input1 = screen.getByPlaceholderText('Número 1');
    const input2 = screen.getByPlaceholderText('Número 2');
    const calcularBoton = screen.getByText('Calcular');

    // Mock para la operación de suma y la actualización del historial
    fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ resultado: 30 }) });
    fetch.mockResolvedValueOnce({ ok: true, json: async () => [] });

    fireEvent.change(input1, { target: { value: '10' } });
    fireEvent.change(input2, { target: { value: '20' } });
    fireEvent.click(calcularBoton);

    await waitFor(() => {
        expect(screen.getByText(/Resultado: 30/i)).toBeInTheDocument();
    });
});

// Prueba 3: Muestra un mensaje de error si la API falla
test('muestra un mensaje de error cuando la API devuelve un error', async () => {
    fetch.mockResolvedValueOnce({ ok: true, json: async () => [] });
    render(<App />);
    await screen.findByText('Calcular'); 

    const input1 = screen.getByPlaceholderText('Número 1');
    const input2 = screen.getByPlaceholderText('Número 2');
    fireEvent.change(input1, { target: { value: '10' } });
    fireEvent.change(input2, { target: { value: '0' } });

    fetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: { error: 'División por cero' } }),
    });

    const calcularBoton = screen.getByText('Calcular');
    
    fireEvent.click(calcularBoton);

    await waitFor(() => {
        const errorTexto = screen.getByText(/Error: División por cero/i);
        expect(errorTexto).toBeInTheDocument();
    });
});