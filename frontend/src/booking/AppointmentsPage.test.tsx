import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AppointmentsPage } from './AppointmentsPage';
import { ApiError } from '../api/client';

const api = vi.hoisted(() => ({ request: vi.fn(), sessionRequest: vi.fn() }));
const session = vi.hoisted(() => ({ request: (...args: unknown[]) => api.sessionRequest(...args) }));
vi.mock('../api/client', async importOriginal => ({ ...await importOriginal<typeof import('../api/client')>(), request: api.request }));
vi.mock('../auth/provider', () => ({ useSession: () => ({ session, state: { profile: { rol: 'paciente' }, loading: false } }) }));

describe('mis turnos', () => {
  beforeEach(() => {
    api.request.mockReset(); api.sessionRequest.mockReset();
    api.request.mockImplementation((path: string) => path === '/publico/consultorio'
      ? Promise.resolve({ zona_horaria: 'America/Argentina/Buenos_Aires', telefono: '1234' })
      : Promise.resolve([{ id: 2, nombre: 'Ana Pérez' }]));
    api.sessionRequest.mockResolvedValue([{ id: 3, profesional_id: 2, prestacion_id: 1, prestacion_nombre: 'Consulta', inicio: '2026-11-12T12:30:00Z', fin: '2026-11-12T13:00:00Z', estado: 'pendiente', acciones_permitidas: ['confirmar', 'cancelar', 'reprogramar'] }]);
  });
  it('muestra el turno propio y solo las acciones autorizadas', async () => {
    render(<MemoryRouter><AppointmentsPage /></MemoryRouter>);
    expect(await screen.findByText('Consulta')).toBeInTheDocument();
    expect(screen.getByText(/Ana Pérez/)).toBeInTheDocument();
    expect(screen.getByText(/12\/11\/2026.*09:30/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Confirmar turno' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancelar turno' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reprogramar' })).toBeInTheDocument();
  });
  it('oculta acciones no autorizadas y usa una etiqueta neutral para profesionales inactivos', async () => {
    api.sessionRequest.mockResolvedValue([{ id: 4, profesional_id: 99, prestacion_id: 1, prestacion_nombre: 'Control', inicio: '2026-11-12T12:30:00Z', fin: '2026-11-12T13:00:00Z', estado: 'confirmado', acciones_permitidas: [] }]);
    render(<MemoryRouter><AppointmentsPage /></MemoryRouter>);
    expect(await screen.findByText('Profesional no disponible')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cancelar turno' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Reprogramar' })).not.toBeInTheDocument();
    expect(screen.getByText(/1234/)).toBeInTheDocument();
  });
  it('no sugiere modificar un turno finalizado y ofrece reservar uno liberado', async () => {
    api.sessionRequest.mockResolvedValue([{ id: 5, profesional_id: 99, prestacion_id: 1, prestacion_nombre: 'Control', inicio: '2026-11-12T12:30:00Z', fin: '2026-11-12T13:00:00Z', estado: 'liberado', acciones_permitidas: [] }]);
    render(<MemoryRouter><AppointmentsPage /></MemoryRouter>);
    expect(await screen.findByRole('link', { name: 'Reservar de nuevo' })).toHaveAttribute('href', '/reservar');
    expect(screen.queryByText(/para modificar este turno/i)).not.toBeInTheDocument();
  });
  it('confirma y vuelve a consultar el estado del turno', async () => {
    api.sessionRequest.mockImplementation((path: string) => path === '/turnos/3/confirmar'
      ? Promise.resolve({ estado: 'confirmado' })
      : Promise.resolve([{ id: 3, profesional_id: 2, prestacion_id: 1, prestacion_nombre: 'Consulta', inicio: '2026-11-12T12:30:00Z', fin: '2026-11-12T13:00:00Z', estado: 'pendiente', acciones_permitidas: ['confirmar'] }]));
    render(<MemoryRouter><AppointmentsPage /></MemoryRouter>);
    fireEvent.click(await screen.findByRole('button', { name: 'Confirmar turno' }));
    expect(await screen.findByText(/turno confirmado/i)).toBeInTheDocument();
    expect(api.sessionRequest).toHaveBeenCalledWith('/turnos/3/confirmar', { method: 'POST' });
    expect(api.sessionRequest.mock.calls.filter(([path]) => path === '/turnos')).toHaveLength(2);
  });
  it('pide confirmación antes de cancelar y permite volver sin enviar', async () => {
    render(<MemoryRouter><AppointmentsPage /></MemoryRouter>);
    fireEvent.click(await screen.findByRole('button', { name: 'Cancelar turno' }));
    expect(screen.getByText(/querés cancelar este turno/i)).toBeInTheDocument();
    expect(api.sessionRequest).not.toHaveBeenCalledWith('/turnos/3/cancelar', expect.anything());
    fireEvent.click(screen.getByRole('button', { name: 'Volver' }));
    expect(screen.queryByText(/querés cancelar este turno/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar turno' }));
    api.sessionRequest.mockResolvedValueOnce({ estado: 'cancelado' });
    fireEvent.click(screen.getByRole('button', { name: 'Sí, cancelar turno' }));
    expect(await screen.findByText(/turno cancelado/i)).toBeInTheDocument();
    expect(api.sessionRequest).toHaveBeenCalledWith('/turnos/3/cancelar', { method: 'POST' });
  });
  it('reprograma solo al confirmar el horario orientativo', async () => {
    api.sessionRequest.mockResolvedValue([{ id: 3, profesional_id: 2, prestacion_id: 1, prestacion_nombre: 'Consulta', inicio: '2026-11-12T12:30:00Z', fin: '2026-11-12T13:15:00Z', estado: 'pendiente', acciones_permitidas: ['reprogramar'] }]);
    api.request.mockImplementation((path: string) => path === '/publico/consultorio'
      ? Promise.resolve({ zona_horaria: 'America/Argentina/Buenos_Aires', telefono: '1234' })
      : path === '/publico/profesionales' ? Promise.resolve([{ id: 2, nombre: 'Ana Pérez' }])
      : Promise.resolve([{ inicio: '2026-11-13T13:00:00Z', fin: '2026-11-13T13:30:00Z' }]));
    render(<MemoryRouter><AppointmentsPage /></MemoryRouter>);
    fireEvent.click(await screen.findByRole('button', { name: 'Reprogramar' }));
    expect(screen.getByText(/horarios orientativos/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Nueva fecha'), { target: { value: '2026-11-13' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    fireEvent.click(await screen.findByRole('button', { name: /13\/11\/2026.*10:00/ }));
    expect(api.sessionRequest).not.toHaveBeenCalledWith('/turnos/3', expect.anything());
    api.sessionRequest.mockResolvedValueOnce({ estado: 'pendiente' });
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar nuevo horario' }));
    expect(await screen.findByText(/turno fue reprogramado/i)).toBeInTheDocument();
    expect(api.sessionRequest).toHaveBeenCalledWith('/turnos/3', { method: 'PATCH', body: { inicio: '2026-11-13T13:00:00Z' } });
  });
  it('muestra turnos pasados y futuros que devuelve la API', async () => {
    api.sessionRequest.mockResolvedValue([
      { id: 1, profesional_id: 2, prestacion_id: 1, prestacion_nombre: 'Control anterior', inicio: '2020-01-01T12:30:00Z', fin: '2020-01-01T13:00:00Z', estado: 'atendido', acciones_permitidas: [] },
      { id: 2, profesional_id: 2, prestacion_id: 1, prestacion_nombre: 'Próxima consulta', inicio: '2030-01-01T12:30:00Z', fin: '2030-01-01T13:00:00Z', estado: 'pendiente', acciones_permitidas: ['confirmar'] },
    ]);
    render(<MemoryRouter><AppointmentsPage /></MemoryRouter>);
    expect(await screen.findByText('Control anterior')).toBeInTheDocument();
    expect(screen.getByText('Próxima consulta')).toBeInTheDocument();
  });
  it('informa resultado incierto y consulta nuevamente sin repetir la operación', async () => {
    render(<MemoryRouter><AppointmentsPage /></MemoryRouter>);
    const button = await screen.findByRole('button', { name: 'Confirmar turno' });
    api.sessionRequest.mockRejectedValueOnce(new TypeError('red'));
    fireEvent.click(button);
    expect(await screen.findByRole('alert')).toHaveTextContent(/revisá tus turnos/i);
    expect(api.sessionRequest.mock.calls.filter(([path]) => path === '/turnos/3/confirmar')).toHaveLength(1);
    expect(api.sessionRequest.mock.calls.filter(([path]) => path === '/turnos')).toHaveLength(2);
  });
  it('mantiene el turno original y presenta alternativas después de un 409', async () => {
    api.request.mockImplementation((path: string) => path === '/publico/consultorio'
      ? Promise.resolve({ zona_horaria: 'America/Argentina/Buenos_Aires', telefono: '1234' })
      : path === '/publico/profesionales' ? Promise.resolve([{ id: 2, nombre: 'Ana Pérez' }])
      : Promise.resolve([{ inicio: '2026-11-13T13:00:00Z', fin: '2026-11-13T13:30:00Z' }]));
    render(<MemoryRouter><AppointmentsPage /></MemoryRouter>);
    fireEvent.click(await screen.findByRole('button', { name: 'Reprogramar' }));
    fireEvent.change(screen.getByLabelText('Nueva fecha'), { target: { value: '2026-11-13' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    fireEvent.click(await screen.findByRole('button', { name: /13\/11\/2026.*10:00/ }));
    api.sessionRequest.mockRejectedValueOnce(new ApiError(409, [], { kind: 'occupied', alternatives: [{ inicio: '2026-11-14T14:00:00Z', fin: '2026-11-14T14:30:00Z' }] }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar nuevo horario' }));
    expect(await screen.findByText(/horario ya no está disponible/i)).toBeInTheDocument();
    expect(screen.getByText(/12\/11\/2026.*09:30/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /14\/11\/2026.*11:00/ })).toBeInTheDocument();
    expect(api.sessionRequest.mock.calls.filter(([path]) => path === '/turnos/3')).toHaveLength(1);
  });
  it('muestra el teléfono cuando el servidor rechaza una acción fuera de plazo', async () => {
    render(<MemoryRouter><AppointmentsPage /></MemoryRouter>);
    fireEvent.click(await screen.findByRole('button', { name: 'Cancelar turno' }));
    api.sessionRequest.mockRejectedValueOnce(new ApiError(403, [], { kind: 'deadline' }));
    fireEvent.click(screen.getByRole('button', { name: 'Sí, cancelar turno' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/plazo.*1234/i);
    expect(api.sessionRequest.mock.calls.filter(([path]) => path === '/turnos/3/cancelar')).toHaveLength(1);
  });
  it('bloquea la selección mientras está pendiente una reprogramación', async () => {
    api.request.mockImplementation((path: string) => path === '/publico/consultorio'
      ? Promise.resolve({ zona_horaria: 'UTC', telefono: '1234' })
      : path === '/publico/profesionales' ? Promise.resolve([{ id: 2, nombre: 'Ana Pérez' }])
      : Promise.resolve([{ inicio: '2026-11-13T13:00:00Z', fin: '2026-11-13T13:30:00Z' }]));
    render(<MemoryRouter><AppointmentsPage /></MemoryRouter>);
    fireEvent.click(await screen.findByRole('button', { name: 'Reprogramar' }));
    fireEvent.change(screen.getByLabelText('Nueva fecha'), { target: { value: '2026-11-13' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    fireEvent.click(await screen.findByRole('button', { name: /13\/11\/2026.*13:00/ }));
    api.sessionRequest.mockImplementationOnce(() => new Promise(() => {}));
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar nuevo horario' }));
    expect(screen.getByLabelText('Nueva fecha')).toBeDisabled();
    expect(screen.getByRole('button', { name: /13\/11\/2026.*13:00/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Reprogramar' })).toBeDisabled();
  });
  it.each([new ApiError(422), new ApiError(409, [], { kind: 'occupied', alternatives: [] })])('conserva el turno original si falla el nuevo horario', async failure => {
    api.request.mockImplementation((path: string) => path === '/publico/consultorio'
      ? Promise.resolve({ zona_horaria: 'UTC', telefono: '1234' })
      : path === '/publico/profesionales' ? Promise.resolve([{ id: 2, nombre: 'Ana Pérez' }])
      : Promise.resolve([{ inicio: '2026-11-13T13:00:00Z', fin: '2026-11-13T13:30:00Z' }]));
    render(<MemoryRouter><AppointmentsPage /></MemoryRouter>);
    fireEvent.click(await screen.findByRole('button', { name: 'Reprogramar' }));
    fireEvent.change(screen.getByLabelText('Nueva fecha'), { target: { value: '2026-11-13' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    fireEvent.click(await screen.findByRole('button', { name: /13\/11\/2026.*13:00/ }));
    api.sessionRequest.mockRejectedValueOnce(failure);
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar nuevo horario' }));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/12\/11\/2026.*12:30/)).toBeInTheDocument();
    expect(screen.queryByText(/turno fue reprogramado/i)).not.toBeInTheDocument();
    expect(api.sessionRequest.mock.calls.filter(([path]) => path === '/turnos/3')).toHaveLength(1);
  });
});
