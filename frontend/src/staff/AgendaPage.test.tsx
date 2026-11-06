import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { AgendaPage } from './AgendaPage';

const mock = vi.hoisted(() => ({ profile: { rol: 'profesional', nombre_usuario: 'Ana' }, session: { request: vi.fn() }, publicRequest: vi.fn() }));
vi.mock('../auth/provider', () => ({ useSession: () => ({ state: { profile: mock.profile }, session: mock.session }) }));
vi.mock('../api/client', () => ({ request: mock.publicRequest, ApiError: class extends Error { constructor(public status: number) { super(); } } }));
vi.mock('./StaffTurno', () => ({ StaffNuevoTurno: ({ onClose }: { onClose: () => void }) => <div>Alta de turno<button onClick={onClose}>Volver</button></div>, StaffTurnoDetalle: ({ turnoId, onClose }: { turnoId: number; onClose: () => void }) => <div>Detalle {turnoId}<button onClick={onClose}>Volver</button></div> }));

beforeEach(() => { mock.profile.rol = 'profesional'; mock.session.request.mockReset(); mock.publicRequest.mockReset(); });

it('abre el detalle indicado en el enlace y vuelve a la agenda', () => {
  mock.profile.rol = 'administrador';
  mock.publicRequest.mockResolvedValue({ zona_horaria: 'America/Argentina/Buenos_Aires' });
  mock.session.request.mockResolvedValue([]);
  render(<MemoryRouter initialEntries={['/agenda?turno=13']}><AgendaPage /></MemoryRouter>);
  expect(screen.getByText('Detalle 13')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Volver' }));
  expect(screen.queryByText('Detalle 13')).not.toBeInTheDocument();
});
it('ignora un identificador de turno inválido', () => {
  mock.publicRequest.mockResolvedValue({ zona_horaria: 'America/Argentina/Buenos_Aires' });
  mock.session.request.mockResolvedValue([]);
  render(<MemoryRouter initialEntries={['/agenda?turno=-2']}><AgendaPage /></MemoryRouter>);
  expect(screen.queryByText(/Detalle/)).not.toBeInTheDocument();
});

it('muestra la agenda propia del profesional sin selector de otro profesional', async () => {
  mock.publicRequest.mockResolvedValue({ zona_horaria: 'America/Argentina/Buenos_Aires' });
  mock.session.request.mockImplementation((path: string) => path === '/agenda/contexto' ? Promise.resolve({ profesional_id: 7 }) : Promise.resolve([]));
  render(<MemoryRouter><AgendaPage /></MemoryRouter>);
  expect(await screen.findByText('No hay turnos para esta fecha.', {}, { timeout: 5000 })).toBeInTheDocument();
  expect(screen.queryByLabelText('Profesional')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Dar turno' })).not.toBeInTheDocument();
  await waitFor(() => expect(mock.session.request).toHaveBeenCalledWith(expect.stringMatching(/^\/agenda\?profesional_id=7&fecha=/)));
});

it('permite a recepción seleccionar profesional y distinguir error de agenda vacía', async () => {
  mock.profile.rol = 'recepcion';
  mock.publicRequest.mockImplementation((path: string) => Promise.resolve(path === '/publico/profesionales' ? [{ id: 9, nombre: 'Dra. Lara' }] : { zona_horaria: 'America/Argentina/Buenos_Aires' }));
  mock.session.request.mockRejectedValue(new Error('red'));
  render(<MemoryRouter><AgendaPage /></MemoryRouter>);
  fireEvent.change(await screen.findByLabelText('Profesional'), { target: { value: '9' } });
  expect(await screen.findByText('No pudimos cargar la agenda.')).toBeInTheDocument();
  expect(screen.queryByText('No hay turnos para esta fecha.')).not.toBeInTheDocument();
  expect(mock.session.request).not.toHaveBeenCalledWith('/agenda/contexto');
});

it('ignora una respuesta anterior al cambiar la fecha', async () => {
  let resolveOld: (items: unknown[]) => void = () => {};
  mock.publicRequest.mockResolvedValue({ zona_horaria: 'America/Argentina/Buenos_Aires' });
  mock.session.request.mockImplementation((path: string) => path === '/agenda/contexto' ? Promise.resolve({ profesional_id: 7 }) : path.includes('2027-01-02') ? Promise.resolve([]) : new Promise(resolve => { resolveOld = resolve; }));
  render(<MemoryRouter><AgendaPage /></MemoryRouter>);
  const date = await screen.findByLabelText('Fecha');
  await waitFor(() => expect(mock.session.request).toHaveBeenCalledTimes(2));
  fireEvent.change(date, { target: { value: '2027-01-02' } });
  expect(await screen.findByText('No hay turnos para esta fecha.')).toBeInTheDocument();
  resolveOld([{ id: 1, inicio: '2027-01-01T10:00:00-03:00', paciente_nombre: 'Obsoleto', paciente_apellido: 'Prueba', estado: 'pendiente' }]);
  await waitFor(() => expect(screen.queryByText(/Obsoleto/)).not.toBeInTheDocument());
});

it('informa al profesional cuando no tiene agenda vinculada', async () => {
  mock.publicRequest.mockResolvedValue({ zona_horaria: 'America/Argentina/Buenos_Aires' });
  mock.session.request.mockResolvedValue({ profesional_id: null });
  render(<MemoryRouter><AgendaPage /></MemoryRouter>);
  expect(await screen.findByText('No tenés una agenda vinculada. Comunicate con el consultorio.')).toBeInTheDocument();
});

it('permite reintentar una consulta fallida', async () => {
  mock.publicRequest.mockResolvedValue({ zona_horaria: 'America/Argentina/Buenos_Aires' });
  let calls = 0;
  mock.session.request.mockImplementation((path: string) => path === '/agenda/contexto' ? Promise.resolve({ profesional_id: 7 }) : ++calls === 1 ? Promise.reject(new Error('red')) : Promise.resolve([]));
  render(<MemoryRouter><AgendaPage /></MemoryRouter>);
  expect(await screen.findByText('No pudimos cargar la agenda.')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Intentar de nuevo' }));
  expect(await screen.findByText('No hay turnos para esta fecha.')).toBeInTheDocument();
});

it('presenta horas en la zona del consultorio y la marca de sobreturno', async () => {
  mock.publicRequest.mockResolvedValue({ zona_horaria: 'America/Argentina/Buenos_Aires' });
  mock.session.request.mockImplementation((path: string) => path === '/agenda/contexto' ? Promise.resolve({ profesional_id: 7 }) : Promise.resolve([{ id: 1, inicio: '2027-01-01T12:00:00Z', paciente_nombre: 'Ana', paciente_apellido: 'Prueba', estado: 'pendiente', es_sobreturno: true, acciones_permitidas: [] }]));
  render(<MemoryRouter><AgendaPage /></MemoryRouter>);
  expect(await screen.findByText(/09:00 · Ana Prueba · pendiente · Sobreturno/)).toBeInTheDocument();
});

it('oculta resultados anteriores si se limpia el profesional seleccionado', async () => {
  mock.profile.rol = 'recepcion';
  mock.publicRequest.mockImplementation((path: string) => Promise.resolve(path === '/publico/profesionales' ? [{ id: 9, nombre: 'Dra. Lara' }] : { zona_horaria: 'America/Argentina/Buenos_Aires' }));
  mock.session.request.mockResolvedValue([{ id: 1, inicio: '2027-01-01T12:00:00Z', paciente_nombre: 'Ana', paciente_apellido: 'Prueba', estado: 'pendiente', es_sobreturno: false, acciones_permitidas: [] }]);
  render(<MemoryRouter><AgendaPage /></MemoryRouter>);
  const select = await screen.findByLabelText('Profesional');
  fireEvent.change(select, { target: { value: '9' } });
  expect(await screen.findByText(/Ana Prueba/)).toBeInTheDocument();
  fireEvent.change(select, { target: { value: '' } });
  expect(screen.queryByText(/Ana Prueba/)).not.toBeInTheDocument();
});

it('selecciona la agenda propia del administrador y ofrece el catálogo completo', async () => {
  mock.profile.rol = 'administrador';
  mock.publicRequest.mockResolvedValue({ zona_horaria: 'America/Argentina/Buenos_Aires' });
  mock.session.request.mockImplementation((path: string) => path === '/agenda/contexto' ? Promise.resolve({ profesional_id: 7 }) : path === '/profesionales' ? Promise.resolve([{ id: 7, nombre: 'Ana', apellido: 'Dental', activo: false }, { id: 8, nombre: 'Luis', apellido: 'García', activo: true }]) : Promise.resolve([]));
  render(<MemoryRouter><AgendaPage /></MemoryRouter>);
  const select = await screen.findByLabelText('Profesional');
  await waitFor(() => expect(select).toHaveValue('7'));
  expect(screen.getByRole('option', { name: /Ana Dental/ })).toBeInTheDocument();
  expect(screen.getByRole('option', { name: /Luis García/ })).toBeInTheDocument();
});

it('abre el detalle y solo ofrece dar turno al personal habilitado', async () => {
  mock.profile.rol = 'recepcion';
  mock.publicRequest.mockImplementation((path: string) => Promise.resolve(path === '/publico/profesionales' ? [{ id: 9, nombre: 'Dra. Lara' }] : { zona_horaria: 'America/Argentina/Buenos_Aires' }));
  mock.session.request.mockResolvedValue([{ id: 4, inicio: '2027-01-01T12:00:00Z', paciente_nombre: 'Ana', paciente_apellido: 'Prueba', estado: 'pendiente', es_sobreturno: false, acciones_permitidas: [] }]);
  render(<MemoryRouter><AgendaPage /></MemoryRouter>);
  fireEvent.click(screen.getByRole('button', { name: 'Dar turno' }));
  expect(screen.getByText('Alta de turno')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Volver' }));
  fireEvent.change(await screen.findByLabelText('Profesional'), { target: { value: '9' } });
  fireEvent.click(await screen.findByRole('button', { name: /Ver turno de Ana Prueba/ }));
  expect(screen.getByText('Detalle 4')).toBeInTheDocument();
});
