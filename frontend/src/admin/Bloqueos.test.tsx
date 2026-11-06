import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ApiError } from '../api/client';
import { Bloqueos } from './Bloqueos';
const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock('../auth/provider', () => ({ useSession: () => ({ session: api }) }));
beforeEach(() => api.request.mockReset());
it('distingue los bloqueos vigentes del formulario y oculta los vencidos', async () => {
  api.request.mockImplementation((path: string) => path === '/profesionales' ? Promise.resolve([]) : Promise.resolve([
    { id: 50, tipo: 'feriado', inicio: '2099-12-10T09:00', fin: '2099-12-10T10:00', profesional_id: null, motivo: null },
    { id: 51, tipo: 'ausencia', inicio: '2001-12-10T09:00', fin: '2001-12-10T10:00', profesional_id: null, motivo: null },
  ]));
  render(<MemoryRouter><Bloqueos /></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'Bloqueos vigentes' })).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'Nuevo bloqueo' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Eliminar bloqueo 50' })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Eliminar bloqueo 51' })).not.toBeInTheDocument();
});
it('muestra lista vacía si solo hay bloqueos vencidos', async () => {
  api.request.mockImplementation((path: string) => path === '/profesionales' ? Promise.resolve([]) : Promise.resolve([
    { id: 51, tipo: 'ausencia', inicio: '2001-12-10T09:00', fin: '2001-12-10T10:00', profesional_id: null, motivo: null },
  ]));
  render(<MemoryRouter><Bloqueos /></MemoryRouter>);
  expect(await screen.findByText('No hay bloqueos registrados.')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Eliminar bloqueo 51' })).not.toBeInTheDocument();
});
it('crea bloqueo global libre y actualiza la lista', async () => {
  api.request.mockImplementation((path: string, options?: { method?: string }) => path === '/profesionales' ? Promise.resolve([]) : options?.method === 'POST' ? Promise.resolve({ id: 5, tipo: 'bloqueo', inicio: '2026-12-10T09:00:00', fin: '2026-12-10T10:00:00', profesional_id: null, motivo: null }) : Promise.resolve([]));
  render(<MemoryRouter><Bloqueos /></MemoryRouter>); await screen.findByText('No hay bloqueos registrados.');
  fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-12-10T09:00' } });
  fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-12-10T10:00' } });
  fireEvent.click(screen.getByRole('button', { name: 'Crear bloqueo' }));
  await screen.findByText(/2026-12-10T09:00/);
  expect(api.request).toHaveBeenCalledWith('/bloqueos', { method: 'POST', body: { tipo: 'bloqueo', inicio: '2026-12-10T09:00', fin: '2026-12-10T10:00', motivo: null } });
});
it('presenta conflictos actualizados y permite reintento explícito sin modificar turnos', async () => {
  let writes = 0;
  api.request.mockImplementation((path: string, options?: { method?: string }) => {
    if (path === '/profesionales') return Promise.resolve([{ id: 1, nombre: 'Ana', apellido: 'Ríos', activo: true }]);
    if (options?.method === 'POST') { writes++; return writes < 3 ? Promise.reject(new ApiError(409, [], undefined, writes === 1 ? [12, 13] : [13])) : Promise.resolve({ id: 5, tipo: 'bloqueo', inicio: '2026-12-10T09:00', fin: '2026-12-10T10:00', profesional_id: 1, motivo: null }); }
    return Promise.resolve([]);
  });
  render(<MemoryRouter><Bloqueos /></MemoryRouter>); await screen.findByRole('option', { name: 'Ana Ríos' });
  fireEvent.change(screen.getByLabelText('Alcance'), { target: { value: '1' } });
  fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-12-10T09:00' } });
  fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-12-10T10:00' } });
  fireEvent.click(screen.getByRole('button', { name: 'Crear bloqueo' }));
  expect(await screen.findByRole('link', { name: 'Turno #12' })).toHaveAttribute('href', '/agenda?turno=12');
  fireEvent.click(screen.getByRole('button', { name: 'Volver a intentar' }));
  await screen.findByText('Turno #13'); expect(screen.queryByText('Turno #12')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Volver a intentar' }));
  await screen.findByText('Bloqueo creado.');
  expect(writes).toBe(3);
});
it('valida el intervalo y permite eliminar un bloqueo', async () => {
  api.request.mockImplementation((path: string, options?: { method?: string }) => path === '/profesionales' ? Promise.resolve([]) : options?.method === 'DELETE' ? Promise.resolve(undefined) : Promise.resolve([{ id: 5, tipo: 'bloqueo', inicio: '2026-12-10T09:00', fin: '2026-12-10T10:00', profesional_id: null, motivo: null }]));
  render(<MemoryRouter><Bloqueos /></MemoryRouter>); await screen.findByRole('button', { name: 'Eliminar bloqueo 5' });
  fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-12-10T11:00' } });
  fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-12-10T10:00' } });
  fireEvent.click(screen.getByRole('button', { name: 'Crear bloqueo' }));
  expect(screen.getByRole('alert')).toHaveTextContent(/inicio debe ser anterior/i);
  expect(api.request).not.toHaveBeenCalledWith(expect.anything(), expect.objectContaining({ method: 'POST' }));
  fireEvent.click(screen.getByRole('button', { name: 'Eliminar bloqueo 5' }));
  await screen.findByText('Bloqueo eliminado.');
  expect(screen.getByText('No hay bloqueos registrados.')).toBeInTheDocument();
});
it('conserva bloqueo profesional ante validación del servidor', async () => {
  api.request.mockImplementation((path: string, options?: { method?: string }) => path === '/profesionales' ? Promise.resolve([{ id: 1, nombre: 'Ana', apellido: 'Ríos', activo: true }]) : options?.method === 'POST' ? Promise.reject(new ApiError(422)) : Promise.resolve([]));
  render(<MemoryRouter><Bloqueos /></MemoryRouter>); await screen.findByRole('option', { name: 'Ana Ríos' });
  fireEvent.change(screen.getByLabelText('Alcance'), { target: { value: '1' } });
  fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-12-10T09:00' } });
  fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-12-10T10:00' } });
  fireEvent.click(screen.getByRole('button', { name: 'Crear bloqueo' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/revisá los datos/i);
  expect(screen.getByLabelText('Desde')).toHaveValue('2026-12-10T09:00');
  expect(api.request).toHaveBeenCalledWith('/profesionales/1/bloqueos', expect.objectContaining({ method: 'POST' }));
});
