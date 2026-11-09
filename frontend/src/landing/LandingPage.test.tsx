import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import { LandingPage } from './LandingPage';

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock('../api/client', async importOriginal => ({ ...await importOriginal<typeof import('../api/client')>(), request: api.request }));
beforeEach(() => { api.request.mockReset(); });

it('muestra datos públicos, prestaciones y accesos', async () => {
  api.request.mockImplementation((path: string) => path.endsWith('consultorio') ? Promise.resolve({nombre: 'Consultorio Ejemplo', direccion: 'Calle 123', telefono: '0111234'}) : Promise.resolve([{id: 1, nombre: 'Consulta', duracion_min: 30}]));
  render(<MemoryRouter><LandingPage /></MemoryRouter>);
  expect((await screen.findAllByText('Consultorio Ejemplo')).length).toBeGreaterThan(0);
  expect(screen.getByText('Consulta')).toBeInTheDocument();
  expect(screen.getByText('30 min')).toBeInTheDocument();
  expect(screen.getByRole('link', {name: '0111234'})).toHaveAttribute('href', 'tel:0111234');
  expect(screen.getByRole('link', {name: /crear cuenta/i})).toHaveAttribute('href', '/registro');
});

it('conserva accesos al fallar y recupera con reintento', async () => {
  api.request.mockRejectedValueOnce(new Error('red')).mockResolvedValueOnce([]).mockResolvedValueOnce({nombre: 'Recuperado', telefono: null, direccion: null}).mockResolvedValueOnce([]);
  render(<MemoryRouter><LandingPage /></MemoryRouter>);
  expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos cargar');
  expect(screen.getAllByRole('link', {name: /ver turnos disponibles/i})[0]).toHaveAttribute('href', '/reservar');
  fireEvent.click(screen.getByRole('button', {name: /volver a cargar/i}));
  expect((await screen.findAllByText('Recuperado')).length).toBeGreaterThan(0);
  expect(screen.getByText('No hay prestaciones para mostrar por el momento.')).toBeInTheDocument();
  expect(screen.queryByText('null')).not.toBeInTheDocument();
});

it('respeta el plazo de reintento indicado por el servidor', async () => {
  api.request.mockRejectedValueOnce(new ApiError(429, [], undefined, undefined, 1)).mockResolvedValueOnce([]);
  render(<MemoryRouter><LandingPage /></MemoryRouter>);
  const button = await screen.findByRole('button', {name: /volver a cargar/i});
  expect(button).toBeDisabled();
  await waitFor(() => expect(button).toBeEnabled(), {timeout: 2500});
});
