import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { StaffNuevoTurno, StaffTurnoDetalle } from './StaffTurno';
import { ApiError } from '../api/client';
import * as api from '../api/client';
import { MemoryRouter } from 'react-router-dom';

const mock = vi.hoisted(() => ({ request: vi.fn(), role: 'recepcion', id: 1 }));
vi.mock('../auth/provider', () => ({ useSession: () => ({ session: { request: mock.request }, state: { profile: { rol: mock.role, id: mock.id } } }) }));
beforeEach(() => { mock.request.mockReset(); mock.role = 'recepcion'; mock.id = 1; });

it('ofrece solo acciones autorizadas y recarga al confirmarlas', async () => {
  mock.request.mockImplementation((path: string) => path === '/turnos/4' ? Promise.resolve({ id: 4, estado: 'pendiente', paciente_nombre: 'Ana', paciente_apellido: 'Paz', acciones_permitidas: ['confirmar'], es_sobreturno: false }) : Promise.resolve({}));
  const saved = vi.fn(); render(<StaffTurnoDetalle turnoId={4} onClose={() => {}} onSaved={saved} />);
  fireEvent.click(await screen.findByRole('button', { name: 'Confirmar turno' }));
  await waitFor(() => expect(mock.request).toHaveBeenCalledWith('/turnos/4/confirmar', { method: 'POST', body: {} }));
  expect(saved).toHaveBeenCalled();
  expect(screen.queryByRole('button', { name: 'Marcar ausente' })).not.toBeInTheDocument();
});

it('exige motivo y autorización explícita antes de crear sobreturno', async () => {
  vi.spyOn(api, 'request').mockImplementation(async (path) => path.includes('consultorio') ? { zona_horaria: 'UTC' } : []);
  mock.request.mockResolvedValue({ items: [] });
  render(<StaffNuevoTurno onClose={() => {}} onSaved={() => {}} />);
  await waitFor(() => expect(mock.request).toHaveBeenCalled());
  fireEvent.click(screen.getByLabelText('Es sobreturno'));
  fireEvent.click(screen.getByRole('button', { name: 'Crear turno' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('motivo y autorización');
  expect(mock.request.mock.calls.filter(c => c[0] === '/sobreturnos')).toHaveLength(0);
});

it('crea turno con ficha seleccionada y horario consultado, sin repetir escritura incierta', async () => {
  vi.spyOn(api, 'request').mockImplementation(async (path) => path.includes('prestaciones') ? [{ id: 2, nombre: 'Control', duracion_min: 30 }] : path.includes('profesionales') ? [{ id: 3, nombre: 'Dra. Sol' }] : path.includes('disponibilidad') ? [{ inicio: '2027-01-02T12:00:00Z', fin: '2027-01-02T12:30:00Z' }] : { zona_horaria: 'UTC' });
  mock.request.mockImplementation((path: string) => path.startsWith('/pacientes?') ? Promise.resolve({ items: [{ id: 5, nombre: 'Ana', apellido: 'Paz', activo: true }] }) : Promise.reject(new Error('red')));
  render(<StaffNuevoTurno onClose={() => {}} onSaved={() => {}} />);
  fireEvent.change(await screen.findByLabelText('Paciente'), { target: { value: '5' } });
  fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '3' } });
  fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '2' } });
  fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2027-01-02' } });
  fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
  fireEvent.click(await screen.findByRole('button', { name: '12:00' }));
  fireEvent.click(screen.getByRole('button', { name: 'Crear turno' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Revisá la agenda antes de reintentar');
  expect(mock.request.mock.calls.filter(c => c[0] === '/turnos')).toHaveLength(1);
});

it('no permite enviar dos veces el turno tras un éxito confirmado', async () => {
  vi.spyOn(api, 'request').mockImplementation(async (path) => path.includes('prestaciones') ? [{ id: 2, nombre: 'Control' }] : path.includes('profesionales') ? [{ id: 3, nombre: 'Dra. Sol' }] : path.includes('disponibilidad') ? [{ inicio: '2027-01-02T12:00:00Z', fin: '2027-01-02T12:30:00Z' }] : { zona_horaria: 'UTC' });
  mock.request.mockImplementation((path: string) => path.startsWith('/pacientes?') ? Promise.resolve({ items: [{ id: 5, nombre: 'Ana', apellido: 'Paz', activo: true }] }) : Promise.resolve({ id: 9 }));
  render(<StaffNuevoTurno onClose={() => {}} onSaved={() => {}} />); fireEvent.change(await screen.findByLabelText('Paciente'), { target: { value: '5' } }); fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '3' } }); fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '2' } }); fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2027-01-02' } }); fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' })); fireEvent.click(await screen.findByRole('button', { name: '12:00' })); fireEvent.click(screen.getByRole('button', { name: 'Crear turno' }));
  await screen.findByText('Turno creado.'); expect(screen.getByRole('button', { name: 'Crear turno' })).toBeDisabled(); expect(mock.request.mock.calls.filter(c => c[0] === '/turnos')).toHaveLength(1);
});

it('autoriza sobreturno con motivo y hora en zona del consultorio', async () => {
  vi.spyOn(api, 'request').mockImplementation(async (path) => path.includes('prestaciones') ? [{ id: 2, nombre: 'Control' }] : path.includes('profesionales') ? [{ id: 3, nombre: 'Dra. Sol' }] : { zona_horaria: 'America/Argentina/Buenos_Aires' });
  mock.request.mockImplementation((path: string) => path.startsWith('/pacientes?') ? Promise.resolve({ items: [{ id: 5, nombre: 'Ana', apellido: 'Paz', activo: true }] }) : Promise.resolve({ id: 9 }));
  render(<StaffNuevoTurno onClose={() => {}} onSaved={() => {}} />); fireEvent.change(await screen.findByLabelText('Paciente'), { target: { value: '5' } }); fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '3' } }); fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '2' } }); fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2027-01-02' } }); fireEvent.click(screen.getByLabelText('Es sobreturno')); fireEvent.change(screen.getByLabelText('Hora del sobreturno'), { target: { value: '09:00' } }); fireEvent.change(screen.getByLabelText('Motivo'), { target: { value: 'Urgencia' } }); fireEvent.click(screen.getByLabelText('Autorizo el sobreturno')); fireEvent.click(screen.getByRole('button', { name: 'Crear turno' }));
  await waitFor(() => expect(mock.request).toHaveBeenCalledWith('/sobreturnos', { method: 'POST', body: { paciente_id: 5, profesional_id: 3, prestacion_id: 2, inicio: '2027-01-02T12:00:00.000Z', autorizado: true, motivo: 'Urgencia' } }));
});

it('permite alta regular con hora manual fuera del horizonte público', async () => {
  vi.spyOn(api, 'request').mockImplementation(async (path) => path.includes('prestaciones') ? [{ id: 2, nombre: 'Control' }] : path.includes('profesionales') ? [{ id: 3, nombre: 'Dra. Sol' }] : { zona_horaria: 'UTC' });
  mock.request.mockImplementation((path: string) => path.startsWith('/pacientes?') ? Promise.resolve({ items: [{ id: 5, nombre: 'Ana', apellido: 'Paz', activo: true }] }) : Promise.resolve({ id: 9 }));
  render(<StaffNuevoTurno onClose={() => {}} onSaved={() => {}} />); fireEvent.change(await screen.findByLabelText('Paciente'), { target: { value: '5' } }); fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '3' } }); fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '2' } }); fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2027-06-02' } }); fireEvent.change(screen.getByLabelText('Hora manual'), { target: { value: '09:00' } }); fireEvent.click(screen.getByRole('button', { name: 'Crear turno' }));
  await waitFor(() => expect(mock.request).toHaveBeenCalledWith('/turnos', { method: 'POST', body: { paciente_id: 5, profesional_id: 3, prestacion_id: 2, inicio: '2027-06-02T09:00:00.000Z' } }));
});

it('busca ficha por apellido para seleccionar pacientes fuera de la primera página', async () => {
  vi.spyOn(api, 'request').mockImplementation(async (path) => path.includes('consultorio') ? { zona_horaria: 'UTC' } : []);
  mock.request.mockImplementation((path: string) => Promise.resolve({ items: path.includes('apellido=Paz') ? [{ id: 8, nombre: 'Ana', apellido: 'Paz', activo: true }] : [] }));
  render(<StaffNuevoTurno onClose={() => {}} onSaved={() => {}} />);
  fireEvent.change(screen.getByLabelText('Buscar paciente por apellido'), { target: { value: 'Paz' } }); fireEvent.click(screen.getByRole('button', { name: 'Buscar paciente' }));
  expect(await screen.findByRole('option', { name: 'Ana Paz' })).toBeInTheDocument();
});

it('busca paciente por DNI sin interpretar el dato como apellido', async () => {
  vi.spyOn(api, 'request').mockImplementation(async (path) => path.includes('consultorio') ? { zona_horaria: 'UTC' } : []);
  mock.request.mockImplementation((path: string) => Promise.resolve({ items: path.includes('dni=12345678') ? [{ id: 8, nombre: 'Ana', apellido: 'Paz', activo: true }] : [] }));
  render(<StaffNuevoTurno onClose={() => {}} onSaved={() => {}} />);
  fireEvent.change(screen.getByLabelText('Buscar por'), { target: { value: 'dni' } }); fireEvent.change(screen.getByLabelText('Buscar paciente por DNI'), { target: { value: '12345678' } }); fireEvent.click(screen.getByRole('button', { name: 'Buscar paciente' }));
  expect(await screen.findByRole('option', { name: 'Ana Paz' })).toBeInTheDocument();
});

it('permite recorrer páginas de pacientes con el filtro aplicado', async () => {
  vi.spyOn(api, 'request').mockImplementation(async (path) => path.includes('consultorio') ? { zona_horaria: 'UTC' } : []);
  mock.request.mockImplementation((path: string) => Promise.resolve({ total: 101, items: path.includes('offset=100') ? [{ id: 101, nombre: 'Ana', apellido: 'Paz', activo: true }] : [] }));
  render(<StaffNuevoTurno onClose={() => {}} onSaved={() => {}} />);
  await waitFor(() => expect(screen.getByRole('button', { name: 'Siguientes pacientes' })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: 'Siguientes pacientes' }));
  expect(await screen.findByRole('option', { name: 'Ana Paz' })).toBeInTheDocument();
});

it('crea ficha de forma independiente y conserva el resultado parcial si falla el turno', async () => {
  vi.spyOn(api, 'request').mockImplementation(async (path) => path.includes('prestaciones') ? [{ id: 2, nombre: 'Control' }] : path.includes('profesionales') ? [{ id: 3, nombre: 'Dra. Sol' }] : path.includes('disponibilidad') ? [{ inicio: '2027-01-02T12:00:00Z', fin: '2027-01-02T12:30:00Z' }] : { zona_horaria: 'UTC' });
  mock.request.mockImplementation((path: string) => path.startsWith('/pacientes?') ? Promise.resolve({ items: [] }) : path === '/pacientes' ? Promise.resolve({ id: 5, nombre: 'Ana', apellido: 'Paz' }) : Promise.reject(new ApiError(409)));
  render(<StaffNuevoTurno onClose={() => {}} onSaved={() => {}} />);
  fireEvent.click(screen.getByRole('button', { name: 'Crear ficha nueva' }));
  for (const [name, value] of [['Nombre', 'Ana'], ['Apellido', 'Paz'], ['DNI', '12345678'], ['Teléfono', '1123456789'], ['Correo', 'ana@example.com']]) fireEvent.change(screen.getByLabelText(name), { target: { value } });
  fireEvent.click(screen.getByRole('button', { name: 'Guardar ficha' }));
  expect(await screen.findByText(/La ficha ya fue creada/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '3' } }); fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '2' } }); fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2027-01-02' } });
  fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' })); fireEvent.click(await screen.findByRole('button', { name: '12:00' })); fireEvent.click(screen.getByRole('button', { name: 'Crear turno' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('horario');
  expect(screen.getByText(/La ficha ya fue creada/)).toBeInTheDocument();
  expect(mock.request.mock.calls.filter(c => c[0] === '/pacientes')).toHaveLength(1);
});

it('ante conflicto recarga el turno y explica que cambió', async () => {
  mock.request.mockImplementation((path: string) => path === '/turnos/4' ? Promise.resolve({ id: 4, estado: 'pendiente', paciente_nombre: 'Ana', paciente_apellido: 'Paz', acciones_permitidas: ['confirmar'], es_sobreturno: false }) : Promise.reject(new ApiError(409)));
  const saved = vi.fn(); render(<StaffTurnoDetalle turnoId={4} onClose={() => {}} onSaved={saved} />);
  fireEvent.click(await screen.findByRole('button', { name: 'Confirmar turno' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('cambió');
  expect(saved).toHaveBeenCalled();
  expect(mock.request.mock.calls.filter(c => c[0] === '/turnos/4')).toHaveLength(2);
});

it('permite rechazar aviso solo si el servidor autoriza y explica que el turno sigue vigente', async () => {
  mock.request.mockImplementation((path: string) => path === '/turnos/4' ? Promise.resolve({ id: 4, estado: 'pendiente', paciente_nombre: 'Ana', paciente_apellido: 'Paz', acciones_permitidas: ['responder_sobreturno'], es_sobreturno: true, autorizacion_sobreturno: { motivo: 'Urgencia', respuesta: null } }) : Promise.resolve({}));
  render(<StaffTurnoDetalle turnoId={4} onClose={() => {}} onSaved={() => {}} />);
  fireEvent.click(await screen.findByRole('button', { name: 'Rechazar aviso' }));
  await waitFor(() => expect(mock.request).toHaveBeenCalledWith('/sobreturnos/4/respuesta-profesional', { method: 'POST', body: { respuesta: 'rechazado', comentario: null } }));
  expect(await screen.findByText(/sigue vigente/)).toBeInTheDocument();
});

it('informa validación 422 y permite corregir sin duplicar escrituras automáticas', async () => {
  mock.request.mockImplementation((path: string) => path === '/turnos/4' ? Promise.resolve({ id: 4, estado: 'pendiente', paciente_nombre: 'Ana', paciente_apellido: 'Paz', acciones_permitidas: ['cancelar'], es_sobreturno: false }) : Promise.reject(new ApiError(422)));
  render(<StaffTurnoDetalle turnoId={4} onClose={() => {}} onSaved={() => {}} />);
  fireEvent.click(await screen.findByRole('button', { name: 'Cancelar turno' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Revisá los datos');
  expect(mock.request.mock.calls.filter(c => c[0] === '/turnos/4/cancelar')).toHaveLength(1);
});

it('deshabilita acciones mientras se procesa el envío y evita doble pulsación', async () => {
  let finish: (value: unknown) => void = () => {};
  mock.request.mockImplementation((path: string) => path === '/turnos/4' ? Promise.resolve({ id: 4, estado: 'pendiente', paciente_nombre: 'Ana', paciente_apellido: 'Paz', acciones_permitidas: ['confirmar'], es_sobreturno: false }) : new Promise(resolve => { finish = resolve; }));
  render(<StaffTurnoDetalle turnoId={4} onClose={() => {}} onSaved={() => {}} />);
  const button = await screen.findByRole('button', { name: 'Confirmar turno' }); fireEvent.click(button); expect(button).toBeDisabled(); fireEvent.click(button);
  expect(mock.request.mock.calls.filter(c => c[0] === '/turnos/4/confirmar')).toHaveLength(1); finish({});
});

it('reprograma al seleccionar un horario orientativo y actualiza la agenda', async () => {
  vi.spyOn(api, 'request').mockImplementation(async (path) => path.includes('disponibilidad') ? [{ inicio: '2027-01-02T12:00:00Z', fin: '2027-01-02T12:30:00Z' }] : { zona_horaria: 'UTC' });
  mock.request.mockImplementation((path: string, options: { method?: string } = {}) => path === '/turnos/4' && !options.method ? Promise.resolve({ id: 4, estado: 'confirmado', paciente_nombre: 'Ana', paciente_apellido: 'Paz', profesional_id: 3, prestacion_id: 2, acciones_permitidas: ['reprogramar'], es_sobreturno: false }) : Promise.resolve({}));
  const saved = vi.fn(); render(<StaffTurnoDetalle turnoId={4} onClose={() => {}} onSaved={saved} />);
  fireEvent.click(await screen.findByRole('button', { name: 'Mover turno' })); fireEvent.change(screen.getByLabelText('Nueva fecha'), { target: { value: '2027-01-02' } }); fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' })); fireEvent.click(await screen.findByRole('button', { name: '12:00' }));
  await waitFor(() => expect(mock.request).toHaveBeenCalledWith('/turnos/4', { method: 'PATCH', body: { inicio: '2027-01-02T12:00:00Z' } }));
  expect(saved).toHaveBeenCalled();
});

it('permite mover por hora manual cuando no hay disponibilidad pública', async () => {
  vi.spyOn(api, 'request').mockImplementation(async (path) => path.includes('disponibilidad') ? [] : { zona_horaria: 'UTC' });
  mock.request.mockImplementation((path: string, options: { method?: string } = {}) => path === '/turnos/4' && !options.method ? Promise.resolve({ id: 4, estado: 'confirmado', paciente_nombre: 'Ana', paciente_apellido: 'Paz', profesional_id: 3, prestacion_id: 2, acciones_permitidas: ['reprogramar'], es_sobreturno: false }) : Promise.resolve({}));
  render(<StaffTurnoDetalle turnoId={4} onClose={() => {}} onSaved={() => {}} />);
  fireEvent.click(await screen.findByRole('button', { name: 'Mover turno' })); fireEvent.change(screen.getByLabelText('Nueva fecha'), { target: { value: '2027-01-02' } }); fireEvent.change(screen.getByLabelText('Nueva hora'), { target: { value: '12:00' } }); fireEvent.click(screen.getByRole('button', { name: 'Confirmar movimiento' }));
  await waitFor(() => expect(mock.request).toHaveBeenCalledWith('/turnos/4', { method: 'PATCH', body: { inicio: '2027-01-02T12:00:00.000Z' } }));
});

it('no convierte hora manual cuando no se pudo cargar la zona del consultorio', async () => {
  vi.spyOn(api, 'request').mockRejectedValue(new Error('red'));
  mock.request.mockResolvedValue({ id: 4, estado: 'confirmado', paciente_nombre: 'Ana', paciente_apellido: 'Paz', profesional_id: 3, prestacion_id: 2, acciones_permitidas: ['reprogramar'], es_sobreturno: false });
  render(<StaffTurnoDetalle turnoId={4} onClose={() => {}} onSaved={() => {}} />);
  fireEvent.click(await screen.findByRole('button', { name: 'Mover turno' })); fireEvent.change(screen.getByLabelText('Nueva fecha'), { target: { value: '2027-01-02' } }); fireEvent.change(screen.getByLabelText('Nueva hora'), { target: { value: '12:00' } }); fireEvent.click(screen.getByRole('button', { name: 'Confirmar movimiento' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('zona horaria');
  expect(mock.request.mock.calls.filter(c => c[1]?.method === 'PATCH')).toHaveLength(0);
});

it('permite reintentar la carga de zona sin cerrar el detalle', async () => {
  vi.spyOn(api, 'request').mockRejectedValueOnce(new Error('red')).mockResolvedValue({ zona_horaria: 'UTC' });
  mock.request.mockImplementation((path: string, options: { method?: string } = {}) => path === '/turnos/4' && !options.method ? Promise.resolve({ id: 4, estado: 'confirmado', paciente_nombre: 'Ana', paciente_apellido: 'Paz', profesional_id: 3, prestacion_id: 2, acciones_permitidas: ['reprogramar'], es_sobreturno: false }) : Promise.resolve({}));
  render(<StaffTurnoDetalle turnoId={4} onClose={() => {}} onSaved={() => {}} />); fireEvent.click(await screen.findByRole('button', { name: 'Mover turno' })); fireEvent.change(screen.getByLabelText('Nueva fecha'), { target: { value: '2027-01-02' } }); fireEvent.change(screen.getByLabelText('Nueva hora'), { target: { value: '12:00' } }); fireEvent.click(screen.getByRole('button', { name: 'Confirmar movimiento' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('zona horaria'); fireEvent.click(screen.getByRole('button', { name: 'Reintentar zona horaria' }));
  await waitFor(() => expect(api.request).toHaveBeenCalledTimes(2)); fireEvent.click(screen.getByRole('button', { name: 'Confirmar movimiento' }));
  await waitFor(() => expect(mock.request).toHaveBeenCalledWith('/turnos/4', { method: 'PATCH', body: { inicio: '2027-01-02T12:00:00.000Z' } }));
});

it('ofrece abrir la ficha vinculada desde el detalle', async () => {
  mock.request.mockResolvedValue({ id: 4, paciente_id: 8, estado: 'pendiente', paciente_nombre: 'Ana', paciente_apellido: 'Paz', acciones_permitidas: [], es_sobreturno: false });
  render(<MemoryRouter><StaffTurnoDetalle turnoId={4} onClose={() => {}} onSaved={() => {}} /></MemoryRouter>);
  expect(await screen.findByRole('link', { name: 'Ver ficha' })).toHaveAttribute('href', '/pacientes?ficha=8');
});

it('descarta detalle anterior cuando cambia la sesión', async () => {
  let first: (value: unknown) => void = () => {}; let calls = 0;
  mock.request.mockImplementation(() => ++calls === 1 ? new Promise(resolve => { first = resolve; }) : Promise.resolve({ id: 4, estado: 'pendiente', paciente_nombre: 'Nuevo', paciente_apellido: 'Perfil', acciones_permitidas: [], es_sobreturno: false }));
  const ui = render(<StaffTurnoDetalle turnoId={4} onClose={() => {}} onSaved={() => {}} />);
  mock.id = 2; ui.rerender(<StaffTurnoDetalle turnoId={4} onClose={() => {}} onSaved={() => {}} />);
  expect(await screen.findByText('Nuevo Perfil')).toBeInTheDocument();
  first({ id: 4, estado: 'pendiente', paciente_nombre: 'Anterior', paciente_apellido: 'Privado', acciones_permitidas: [], es_sobreturno: false });
  await waitFor(() => expect(screen.queryByText('Anterior Privado')).not.toBeInTheDocument());
});
