import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import { BookingPage } from './BookingPage';

const api = vi.hoisted(() => ({ request: vi.fn() }));
const session = vi.hoisted(() => ({ state: { profile: null as null | { rol: string; email_verificado: boolean }, loading: false }, request: vi.fn() }));
vi.mock('../api/client', async importOriginal => ({ ...await importOriginal<typeof import('../api/client')>(), request: api.request }));
vi.mock('../auth/provider', () => ({ useSession: () => ({ state: session.state, session: { request: session.request } }) }));

describe('consulta pública de turnos', () => {
  afterEach(() => vi.useRealTimers());
  beforeEach(() => {
    api.request.mockReset();
    session.state.profile = null; session.request.mockReset();
    api.request.mockImplementation((path: string) => {
      if (path === '/publico/consultorio') return Promise.resolve({ nombre: 'Consultorio', telefono: '1234', zona_horaria: 'America/Argentina/Buenos_Aires' });
      if (path === '/publico/prestaciones') return Promise.resolve([{ id: 1, nombre: 'Consulta', duracion_min: 30 }]);
      if (path === '/publico/profesionales') return Promise.resolve([{ id: 2, nombre: 'Ana Pérez' }]);
      if (path.startsWith('/publico/disponibilidad')) return Promise.resolve([{ inicio: '2026-11-12T12:30:00Z', fin: '2026-11-12T13:00:00Z' }]);
      return Promise.reject(new Error('Ruta inesperada'));
    });
  });
  it('permite consultar un horario sin iniciar sesión', async () => {
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    expect(await screen.findByText(/Consultorio · 1234/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-12' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    expect(await screen.findByRole('button', { name: '09:30' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '09:30' }));
    expect(screen.getByRole('link', { name: 'Ingresar' })).toHaveAttribute('href', '/ingresar');
    expect(screen.getByRole('link', { name: 'Crear cuenta' })).toHaveAttribute('href', '/registro');
    expect(screen.getByText(/volvé a elegir el horario/)).toBeInTheDocument();
    await waitFor(() => expect(api.request).toHaveBeenCalledWith(expect.stringContaining('profesional_id=2'), expect.anything()));
  });
  it('anuncia la búsqueda pendiente y evita duplicarla', async () => {
    let finish!: (value: unknown) => void;
    const original = api.request.getMockImplementation()!;
    api.request.mockImplementation((path: string, options: unknown) => path.startsWith('/publico/disponibilidad')
      ? new Promise(resolve => { finish = resolve; }) : original(path, options));
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    await screen.findByText(/Consultorio · 1234/);
    fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-12' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    expect(screen.getByRole('status')).toHaveTextContent('Buscando horarios');
    expect(screen.getByRole('button', { name: 'Buscar horarios' })).toBeDisabled();
    await act(async () => finish([]));
    expect(screen.queryByText('Buscando horarios…')).not.toBeInTheDocument();
  });
  it('muestra una fecha sin horarios y un límite de consultas', async () => {
    api.request.mockImplementation((path: string) => {
      if (path === '/publico/consultorio') return Promise.resolve({ nombre: 'Consultorio', telefono: null, zona_horaria: 'UTC' });
      if (path === '/publico/prestaciones') return Promise.resolve([{ id: 1, nombre: 'Consulta', duracion_min: 30 }]);
      if (path === '/publico/profesionales') return Promise.resolve([{ id: 2, nombre: 'Ana' }]);
      if (path.startsWith('/publico/disponibilidad')) return Promise.resolve([]);
      throw new Error('Ruta inesperada');
    });
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    await screen.findByText('Consultorio');
    fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-12' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    expect(await screen.findByText('No encontramos horarios para esta fecha.')).toBeInTheDocument();
    api.request.mockRejectedValueOnce(new ApiError(429));
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Demasiadas consultas');
  });
  it('ignora la respuesta antigua después de cambiar de fecha', async () => {
    let resolveOld!: (value: unknown) => void;
    api.request.mockImplementation((path: string) => {
      if (path === '/publico/consultorio') return Promise.resolve({ nombre: 'Consultorio', telefono: null, zona_horaria: 'UTC' });
      if (path === '/publico/prestaciones') return Promise.resolve([{ id: 1, nombre: 'Consulta', duracion_min: 30 }]);
      if (path === '/publico/profesionales') return Promise.resolve([{ id: 2, nombre: 'Ana' }]);
      return new Promise(resolve => { resolveOld = resolve; });
    });
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    await screen.findByText('Consultorio');
    fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-12' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-13' } });
    await act(async () => resolveOld([{ inicio: '2026-11-12T12:30:00Z', fin: '2026-11-12T13:00:00Z' }]));
    expect(screen.queryByRole('button', { name: '12:30' })).not.toBeInTheDocument();
  });
  it('informa que está cargando los datos iniciales', () => {
    api.request.mockImplementation(() => new Promise(() => {}));
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    expect(screen.getByRole('status')).toHaveTextContent('Cargando');
  });
  it('informa límite al cargar los catálogos públicos', async () => {
    api.request.mockRejectedValue(new ApiError(429));
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    expect(await screen.findByRole('alert')).toHaveTextContent('Demasiadas consultas');
  });
  it('permite reintentar la carga inicial si falla', async () => {
    const original = api.request.getMockImplementation()!;
    let fallar = true;
    api.request.mockImplementation((path: string, options: unknown) => {
      if (fallar && path === '/publico/consultorio') return Promise.reject(new Error('sin conexión'));
      return original(path, options);
    });
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos cargar');
    expect(screen.queryByLabelText('Prestación')).not.toBeInTheDocument();
    fallar = false;
    fireEvent.click(screen.getByRole('button', { name: 'Volver a cargar' }));
    expect(await screen.findByText(/Consultorio · 1234/)).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
  it('espera Retry-After antes de permitir reintentar los catálogos', async () => {
    api.request.mockRejectedValue(new ApiError(429, [], undefined, undefined, 30));
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    await screen.findByRole('alert');
    expect(screen.getByRole('button', { name: 'Volver a cargar' })).toBeDisabled();
  });
  it('habilita nuevamente el reintento cuando termina Retry-After', async () => {
    vi.useFakeTimers();
    api.request.mockRejectedValue(new ApiError(429, [], undefined, undefined, 30));
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    await act(async () => {});
    expect(screen.getByRole('button', { name: 'Volver a cargar' })).toBeDisabled();
    await act(async () => vi.advanceTimersByTime(30_000));
    expect(screen.getByRole('button', { name: 'Volver a cargar' })).toBeEnabled();
  });
  it('no habilita antes de una espera mayor al máximo de un temporizador', async () => {
    vi.useFakeTimers();
    api.request.mockRejectedValue(new ApiError(429, [], undefined, undefined, 3_000_000));
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    await act(async () => {});
    await act(async () => vi.advanceTimersByTime(2_147_483_647));
    expect(screen.getByRole('button', { name: 'Volver a cargar' })).toBeDisabled();
  });
  it('muestra la espera durante una lectura demorada y luego los datos', async () => {
    let finish!: (value: unknown) => void;
    api.request.mockImplementation((path: string, options: { onWait?: () => void }) => {
      if (path === '/publico/consultorio') { options.onWait?.(); return new Promise(resolve => { finish = resolve; }); }
      return Promise.resolve([]);
    });
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    expect(await screen.findByRole('status')).toHaveTextContent('El servicio está iniciando');
    await act(async () => finish({ nombre: 'Consultorio', telefono: null, zona_horaria: 'UTC' }));
    expect(await screen.findByText('Consultorio')).toBeInTheDocument();
    expect(screen.queryByText(/servicio está iniciando/i)).not.toBeInTheDocument();
  });
  it('reserva solo después de confirmar y envía únicamente la selección', async () => {
    session.state.profile = { rol: 'paciente', email_verificado: true };
    session.request.mockResolvedValue({ estado: 'pendiente' });
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    await screen.findByText(/Consultorio · 1234/);
    fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-12' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    fireEvent.click(await screen.findByRole('button', { name: '09:30' }));
    expect(session.request).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar reserva' }));
    expect(await screen.findByText(/turno está reservado/i)).toBeInTheDocument();
    expect(session.request).toHaveBeenCalledWith('/turnos', { method: 'POST', body: { profesional_id: 2, prestacion_id: 1, inicio: '2026-11-12T12:30:00Z' } });
  });
  it('ofrece alternativas tras un conflicto sin repetir la reserva', async () => {
    session.state.profile = { rol: 'paciente', email_verificado: true };
    session.request.mockRejectedValue(new ApiError(409, [], { kind: 'occupied', alternatives: [{ inicio: '2026-11-13T13:30:00Z', fin: '2026-11-13T14:00:00Z' }] }));
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    await screen.findByText(/Consultorio · 1234/);
    fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-12' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    fireEvent.click(await screen.findByRole('button', { name: '09:30' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar reserva' }));
    expect(await screen.findByText(/horario ya no está disponible/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /13\/11\/2026.*10:30/ }));
    expect(screen.getByText(/13\/11\/2026/, { selector: 'p' })).toBeInTheDocument();
    expect(session.request).toHaveBeenCalledTimes(1);
  });
  it.each([
    [new ApiError(403), /comunicate con el consultorio/i],
    [new ApiError(409, [], { kind: 'limit', maximum: 2 }), /máximo de 2/i],
    [new TypeError('fallo de red'), /revisá tus turnos/i],
  ])('informa el fallo de reserva sin repetirla', async (failure, message) => {
    session.state.profile = { rol: 'paciente', email_verificado: true };
    session.request.mockRejectedValue(failure);
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    await screen.findByText(/Consultorio · 1234/);
    fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-12' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    fireEvent.click(await screen.findByRole('button', { name: '09:30' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar reserva' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(message);
    expect(session.request).toHaveBeenCalledTimes(1);
  });
  it('no reserva con correo sin verificar', async () => {
    session.state.profile = { rol: 'paciente', email_verificado: false };
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    await screen.findByText(/Consultorio · 1234/);
    fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-12' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    fireEvent.click(await screen.findByRole('button', { name: '09:30' }));
    expect(screen.getByRole('button', { name: 'Confirmar reserva' })).toBeDisabled();
    expect(screen.getByRole('link', { name: 'Reenviar enlace' })).toHaveAttribute('href', '/reenviar-verificacion');
    expect(session.request).not.toHaveBeenCalled();
  });
  it('descarta el horario seleccionado al buscar nuevamente', async () => {
    session.state.profile = { rol: 'paciente', email_verificado: true };
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    await screen.findByText(/Consultorio · 1234/);
    fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-12' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    fireEvent.click(await screen.findByRole('button', { name: '09:30' }));
    expect(screen.getByRole('button', { name: 'Confirmar reserva' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    expect(screen.queryByRole('button', { name: 'Confirmar reserva' })).not.toBeInTheDocument();
  });
  it('conserva las preferencias públicas al salir y volver, pero exige consultar y confirmar otra vez', async () => {
    const first = render(<MemoryRouter><BookingPage /></MemoryRouter>);
    await screen.findByText(/Consultorio · 1234/);
    fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-12' } });
    first.unmount();
    session.state.profile = { rol: 'paciente', email_verificado: true };
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    await screen.findByText(/Consultorio · 1234/);
    expect(screen.getByLabelText('Prestación')).toHaveValue('1');
    expect(screen.getByLabelText('Profesional')).toHaveValue('2');
    expect(screen.getByLabelText('Fecha')).toHaveValue('2026-11-12');
    expect(screen.queryByRole('button', { name: 'Confirmar reserva' })).not.toBeInTheDocument();
    expect(session.request).not.toHaveBeenCalled();
  });
  it('bloquea cambios y segundos envíos mientras la reserva está pendiente', async () => {
    session.state.profile = { rol: 'paciente', email_verificado: true };
    session.request.mockImplementation(() => new Promise(() => {}));
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    await screen.findByText(/Consultorio · 1234/);
    fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-12' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    fireEvent.click(await screen.findByRole('button', { name: '09:30' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar reserva' }));
    expect(screen.getByLabelText('Fecha')).toBeDisabled();
    expect(screen.getByRole('button', { name: '09:30' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Confirmar reserva' })).toBeDisabled();
    expect(session.request).toHaveBeenCalledTimes(1);
  });
  it('informa cuando el conflicto no trae alternativas', async () => {
    session.state.profile = { rol: 'paciente', email_verificado: true };
    session.request.mockRejectedValue(new ApiError(409, [], { kind: 'occupied', alternatives: [] }));
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    await screen.findByText(/Consultorio · 1234/);
    fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-12' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    fireEvent.click(await screen.findByRole('button', { name: '09:30' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar reserva' }));
    expect(await screen.findByText('No encontramos alternativas disponibles.')).toBeInTheDocument();
    expect(session.request).toHaveBeenCalledTimes(1);
  });
  it('permite revisar una nueva reserva después de completar otra', async () => {
    session.state.profile = { rol: 'paciente', email_verificado: true };
    session.request.mockResolvedValue({ estado: 'pendiente' });
    render(<MemoryRouter><BookingPage /></MemoryRouter>);
    await screen.findByText(/Consultorio · 1234/);
    fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-12' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    fireEvent.click(await screen.findByRole('button', { name: '09:30' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar reserva' }));
    await screen.findByText(/turno está reservado/i);
    expect(screen.queryByRole('button', { name: '09:30' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    fireEvent.click(await screen.findByRole('button', { name: '09:30' }));
    expect(screen.getByRole('button', { name: 'Confirmar reserva' })).toBeInTheDocument();
  });
});
