import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useState } from 'react';
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom';
import { expect, it } from 'vitest';
import { RouteFocus } from './RouteFocus';

it('lleva el foco al título al cambiar de pantalla', () => {
  render(<MemoryRouter initialEntries={['/inicio']}><RouteFocus /><nav><Link to="/turnos">Mis turnos</Link></nav><Routes>
    <Route path="/inicio" element={<main><h1>Inicio</h1></main>} />
    <Route path="/turnos" element={<main><h1>Mis turnos</h1><input aria-label="Buscar" /></main>} />
  </Routes></MemoryRouter>);
  fireEvent.click(screen.getByRole('link', { name: 'Mis turnos' }));
  expect(screen.getByRole('heading', { name: 'Mis turnos' })).toHaveFocus();
});

it('no roba el foco cuando la pantalla vuelve a renderizarse', () => {
  function Pantalla() {
    const [count, setCount] = useState(0);
    return <main><h1>Cuenta</h1><input aria-label="Nombre" /><button onClick={() => setCount(count + 1)}>Actualizar {count}</button></main>;
  }
  render(<MemoryRouter><RouteFocus /><Pantalla /></MemoryRouter>);
  const field = screen.getByRole('textbox', { name: 'Nombre' });
  field.focus();
  fireEvent.click(screen.getByRole('button', { name: 'Actualizar 0' }));
  expect(field).toHaveFocus();
});

it('enfoca el título cuando la pantalla aparece después de una carga', async () => {
  function Pantalla() {
    const [ready, setReady] = useState(false);
    return ready ? <main><h1>Agenda</h1></main> : <button onClick={() => setReady(true)}>Completar carga</button>;
  }
  render(<MemoryRouter><RouteFocus /><Pantalla /></MemoryRouter>);
  fireEvent.click(screen.getByRole('button', { name: 'Completar carga' }));
  await waitFor(() => expect(screen.getByRole('heading', { name: 'Agenda' })).toHaveFocus());
});
