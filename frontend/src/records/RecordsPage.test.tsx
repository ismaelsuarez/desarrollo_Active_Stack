import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { RecordsPage } from './RecordsPage';
import { ApiError } from '../api/client';
import { MemoryRouter } from 'react-router-dom';
import { act } from '@testing-library/react';

const mock = vi.hoisted(() => ({ request: vi.fn(), role: 'recepcion', id: 1 }));
vi.mock('../auth/provider', () => ({ useSession: () => ({ session: mock, state: { profile: { id: mock.id, rol: mock.role } } }) }));
beforeEach(() => { mock.request.mockReset(); mock.role = 'recepcion'; mock.id = 1; });

it('pagina el historial sin abandonar la ficha', async () => {
  mock.request.mockImplementation((path: string) => {
    if (path.startsWith('/pacientes?')) return Promise.resolve({ items: [{ id: 2, nombre: 'Ana', apellido: 'Pérez', activo: true }], total: 1 });
    if (path === '/pacientes/2') return Promise.resolve({ id: 2, nombre: 'Ana', apellido: 'Pérez', dni: '123', telefono: '456', email: 'a@example.com', activo: true });
    if (path === '/pacientes/2/turnos?limit=21&offset=0') return Promise.resolve(Array.from({length: 21}, (_, i) => ({id: i, inicio: `turno ${i}`, estado: 'atendido'})));
    if (path === '/pacientes/2/turnos?limit=21&offset=20') return Promise.resolve([{id: 20, inicio: 'último turno', estado: 'atendido'}]);
    throw Error(path);
  });
  render(<MemoryRouter><RecordsPage /></MemoryRouter>);
  fireEvent.click(await screen.findByRole('button', {name: 'Ana Pérez'}));
  expect(await screen.findByText(/turno 0/)).toBeInTheDocument();
  expect(screen.queryByText(/turno 20/)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', {name: 'Siguiente historial'}));
  expect(await screen.findByText(/último turno/)).toBeInTheDocument();
  expect(screen.getByRole('heading', {name: 'Ana Pérez'})).toBeInTheDocument();
  expect(screen.getByRole('button', {name: 'Siguiente historial'})).toBeDisabled();
});

it('conserva la página anterior ante un error y permite reintentar', async () => {
  let attempts = 0;
  mock.request.mockImplementation((path: string) => {
    if (path.startsWith('/pacientes?')) return Promise.resolve({items: [{id: 2, nombre: 'Ana', apellido: 'Pérez', activo: true}], total: 1});
    if (path === '/pacientes/2') return Promise.resolve({id: 2, nombre: 'Ana', apellido: 'Pérez', dni: '123', telefono: '456', email: 'a@example.com', activo: true});
    if (path.endsWith('offset=0')) return Promise.resolve(Array.from({length: 21}, (_, i) => ({id: i, inicio: `primero ${i}`, estado: 'atendido'})));
    if (path.endsWith('offset=20')) return ++attempts === 1 ? Promise.reject(Error('red')) : Promise.resolve([{id: 20, inicio: 'segundo', estado: 'atendido'}]);
    throw Error(path);
  });
  render(<MemoryRouter><RecordsPage /></MemoryRouter>);
  fireEvent.click(await screen.findByRole('button', {name: 'Ana Pérez'}));
  await screen.findByText(/primero 0/);
  fireEvent.click(screen.getByRole('button', {name: 'Siguiente historial'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos cargar');
  expect(screen.getByText(/primero 0/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', {name: 'Reintentar historial'}));
  expect(await screen.findByText(/segundo/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', {name: 'Anterior historial'}));
  expect(await screen.findByText(/primero 0/)).toBeInTheDocument();
});

it('descarta una página tardía al abrir otra ficha', async () => {
  let finish!: (value: unknown) => void;
  mock.request.mockImplementation((path: string) => {
    if (path.startsWith('/pacientes?')) return Promise.resolve({items: [{id: 2, nombre: 'Ana', apellido: 'Pérez', activo: true}, {id: 3, nombre: 'Luis', apellido: 'Sol', activo: true}], total: 2});
    if (path === '/pacientes/2' || path === '/pacientes/3') return Promise.resolve({id: path.endsWith('2') ? 2 : 3, nombre: path.endsWith('2') ? 'Ana' : 'Luis', apellido: path.endsWith('2') ? 'Pérez' : 'Sol', activo: true});
    if (path === '/pacientes/2/turnos?limit=21&offset=0') return Promise.resolve(Array.from({length: 21}, (_, i) => ({id: i, inicio: `ana ${i}`, estado: 'atendido'})));
    if (path === '/pacientes/2/turnos?limit=21&offset=20') return new Promise(resolve => {finish = resolve;});
    if (path === '/pacientes/3/turnos?limit=21&offset=0') return Promise.resolve([{id: 50, inicio: 'luis', estado: 'atendido'}]);
    throw Error(path);
  });
  render(<MemoryRouter><RecordsPage /></MemoryRouter>);
  fireEvent.click(await screen.findByRole('button', {name: 'Ana Pérez'}));
  await screen.findByText(/ana 0/); fireEvent.click(screen.getByRole('button', {name: 'Siguiente historial'}));
  fireEvent.click(screen.getByRole('button', {name: 'Luis Sol'}));
  await screen.findByText(/luis ·/);
  await act(async () => finish([{id: 99, inicio: 'privado anterior', estado: 'atendido'}]));
  expect(screen.queryByText(/privado anterior/)).not.toBeInTheDocument();
  expect(screen.getByRole('heading', {name: 'Luis Sol'})).toBeInTheDocument();
});

it('conserva la ficha si falla la primera carga del historial y permite reintentar', async () => {
  let attempts = 0;
  mock.request.mockImplementation((path: string) => {
    if (path.startsWith('/pacientes?')) return Promise.resolve({items: [{id: 2, nombre: 'Ana', apellido: 'Pérez', activo: true}], total: 1});
    if (path === '/pacientes/2') return Promise.resolve({id: 2, nombre: 'Ana', apellido: 'Pérez', activo: true});
    if (path.includes('/turnos?')) return ++attempts === 1 ? Promise.reject(Error('red')) : Promise.resolve([{id: 1, inicio: 'recuperado', estado: 'atendido'}]);
    throw Error(path);
  });
  render(<MemoryRouter><RecordsPage /></MemoryRouter>);
  fireEvent.click(await screen.findByRole('button', {name: 'Ana Pérez'}));
  expect(await screen.findByRole('heading', {name: 'Ana Pérez'})).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', {name: 'Reintentar historial'}));
  expect(await screen.findByText(/recuperado/)).toBeInTheDocument();
});

it('descarta fichas de la sesión anterior si llegan tarde', async () => {
  let finish!: (value: unknown) => void;
  mock.request.mockImplementation(() => mock.id === 1 ? new Promise(resolve => { finish = resolve; }) : Promise.resolve({ items: [], total: 0 }));
  const view = render(<MemoryRouter><RecordsPage /></MemoryRouter>);
  mock.id = 2; view.rerender(<MemoryRouter><RecordsPage /></MemoryRouter>);
  expect(await screen.findByText('No hay fichas para mostrar.')).toBeInTheDocument();
  expect(screen.getByRole('region', {name: 'Resultados de pacientes'})).toHaveTextContent('No hay fichas para mostrar.');
  await act(async () => finish({ items: [{ id: 2, nombre: 'Privado', apellido: 'Anterior', activo: true }], total: 1 }));
  expect(screen.queryByText('Privado Anterior')).not.toBeInTheDocument();
});

it('abre la ficha autorizada desde el enlace de agenda', async () => {
  mock.role = 'profesional';
  mock.request.mockImplementation((path: string) => {
    if (path.startsWith('/pacientes?')) return Promise.resolve({ items: [], total: 0 });
    if (path === '/pacientes/17') return Promise.resolve({ id: 17, nombre: 'Ana', apellido: 'Pérez', dni: '123', telefono: '456', email: 'a@example.com', activo: true, cuenta: { email: 'privado@example.com' } });
    if (path.includes('/turnos?')) return Promise.resolve([]);
    throw Error(path);
  });
  render(<MemoryRouter initialEntries={['/pacientes?ficha=17']}><RecordsPage /></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'Ana Pérez' })).toBeInTheDocument();
  expect(screen.queryByText('privado@example.com')).not.toBeInTheDocument();
});

it('busca fichas y abre el detalle e historial', async () => {
  mock.request.mockImplementation((path: string) => {
    if (path.startsWith('/pacientes?')) return Promise.resolve({ items: [{ id: 2, nombre: 'Ana', apellido: 'Pérez', activo: true }], total: 1, limit: 20, offset: 0 });
    if (path === '/pacientes/2') return Promise.resolve({ id: 2, nombre: 'Ana', apellido: 'Pérez', dni: '123', telefono: '456', email: 'a@example.com', activo: true, cuenta: null });
    if (path.includes('/turnos?')) return Promise.resolve([{ id: 9, inicio: '2026-11-06T12:00:00Z', estado: 'atendido' }]);
    throw Error(path);
  });
  render(<MemoryRouter><RecordsPage /></MemoryRouter>);
  fireEvent.click(await screen.findByRole('button', { name: /Ana Pérez/ }));
  expect(await screen.findByText('Sin cuenta vinculada')).toBeInTheDocument();
  expect(await screen.findByText(/atendido/)).toBeInTheDocument();
});

it('permite buscar y paginar sin mostrar datos de cuenta ni edición al profesional', async () => {
  mock.role = 'profesional';
  mock.request.mockImplementation((path: string) => {
    if (path.startsWith('/pacientes?')) return Promise.resolve({ items: [{ id: 2, nombre: 'Ana', apellido: 'Pérez', activo: true }], total: 21, limit: 20, offset: path.includes('offset=20') ? 20 : 0 });
    if (path === '/pacientes/2') return Promise.resolve({ id: 2, nombre: 'Ana', apellido: 'Pérez', dni: '123', telefono: '456', email: 'a@example.com', activo: true, cuenta: { email: 'secreto@example.com' } });
    if (path.includes('/turnos?')) return Promise.resolve([]);
    throw Error(path);
  });
  render(<MemoryRouter><RecordsPage /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('Apellido'), { target: { value: 'Pérez' } });
  fireEvent.click(screen.getByRole('button', { name: 'Buscar' }));
  expect(await screen.findByRole('button', { name: /Ana Pérez/ })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /Ana Pérez/ }));
  await screen.findByText('Historial de turnos');
  expect(screen.queryByText('secreto@example.com')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Editar' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Desvincular cuenta' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Reactivar ficha' })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }));
  expect(mock.request).toHaveBeenCalledWith(expect.stringContaining('offset=20'));
});

it('edita una ficha y la vuelve a consultar', async () => {
  mock.request.mockImplementation((path: string, options?: { method?: string }) => {
    if (path.startsWith('/pacientes?')) return Promise.resolve({ items: [{ id: 2, nombre: 'Ana', apellido: 'Pérez', activo: true }], total: 1, limit: 20, offset: 0 });
    if (path.includes('/turnos?')) return Promise.resolve([]);
    if (path === '/pacientes/2' && options?.method === 'PATCH') return Promise.resolve({ id: 2 });
    if (path === '/pacientes/2') return Promise.resolve({ id: 2, nombre: 'Ana', apellido: 'Pérez', dni: '123', telefono: '456', email: 'a@example.com', activo: true, cuenta: null });
    throw Error(path);
  });
  render(<MemoryRouter><RecordsPage /></MemoryRouter>);
  fireEvent.click(await screen.findByRole('button', { name: /Ana Pérez/ }));
  fireEvent.click(await screen.findByRole('button', { name: 'Editar' }));
  fireEvent.change(screen.getByLabelText('Teléfono'), { target: { value: '999' } });
  fireEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
  expect(await screen.findByText('Ficha actualizada.')).toBeInTheDocument();
  expect(mock.request).toHaveBeenCalledWith('/pacientes/2', expect.objectContaining({ method: 'PATCH', body: expect.objectContaining({ telefono: '999' }) }));
});

it('exige motivo antes de desvincular y permite reactivar', async () => {
  mock.request.mockImplementation((path: string, options?: { method?: string }) => {
    if (path.startsWith('/pacientes?')) return Promise.resolve({ items: [{ id: 2, nombre: 'Ana', apellido: 'Pérez', activo: false }], total: 1, limit: 20, offset: 0 });
    if (path.includes('/turnos?')) return Promise.resolve([]);
    if (path === '/pacientes/2') return Promise.resolve({ id: 2, nombre: 'Ana', apellido: 'Pérez', dni: '123', telefono: '456', email: 'a@example.com', activo: false, cuenta: { email: 'a@example.com' } });
    if (options?.method === 'POST') return Promise.resolve({});
    throw Error(path);
  });
  render(<MemoryRouter><RecordsPage /></MemoryRouter>); fireEvent.click(await screen.findByRole('button', { name: /Ana Pérez/ }));
  fireEvent.click(await screen.findByRole('button', { name: 'Desvincular cuenta' }));
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar desvinculación' }));
  expect(await screen.findByText('Indicá un motivo.')).toBeInTheDocument();
  expect(mock.request).not.toHaveBeenCalledWith('/pacientes/2/desvincular', expect.anything());
  fireEvent.change(screen.getByLabelText('Motivo'), { target: { value: 'Error de vínculo' } });
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar desvinculación' }));
  expect(await screen.findByText('Cuenta desvinculada.')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Reactivar ficha' }));
  expect(await screen.findByText('Ficha reactivada.')).toBeInTheDocument();
});
it('crea una ficha con datos mínimos y confirma su resultado', async () => {
  mock.request.mockImplementation((path: string, options?: { method?: string }) => {
    if (path.startsWith('/pacientes?')) return Promise.resolve({ items: [], total: 0, limit: 20, offset: 0 });
    if (path === '/pacientes' && options?.method === 'POST') return Promise.resolve({ id: 5 });
    if (path === '/pacientes/5') return Promise.resolve({ id: 5, nombre: 'Juan', apellido: 'Sol', dni: '123', telefono: '456', email: 'j@example.com', activo: true, cuenta: null });
    if (path.includes('/turnos?')) return Promise.resolve([]);
    throw Error(path);
  });
  render(<MemoryRouter><RecordsPage /></MemoryRouter>); fireEvent.click(screen.getByRole('button', { name: 'Nueva ficha' }));
  for (const [label, value] of [['Nombre', 'Juan'], ['Apellido de ficha', 'Sol'], ['DNI', '123'], ['Teléfono', '456'], ['Correo', 'j@example.com']]) fireEvent.change(screen.getByLabelText(label), { target: { value } });
  fireEvent.click(screen.getByRole('button', { name: 'Crear ficha' }));
  expect(await screen.findByText('Ficha creada.')).toBeInTheDocument();
  expect(mock.request).toHaveBeenCalledWith('/pacientes', expect.objectContaining({ method: 'POST', body: expect.objectContaining({ nombre: 'Juan', dni: '123' }) }));
});
it('ante conflicto al reactivar conserva contexto y ofrece actualizar', async () => {
  mock.request.mockImplementation((path: string, options?: { method?: string }) => {
    if (path.startsWith('/pacientes?')) return Promise.resolve({ items: [{ id: 2, nombre: 'Ana', apellido: 'Pérez', activo: false }], total: 1 });
    if (path.includes('/turnos?')) return Promise.resolve([]);
    if (path === '/pacientes/2') return Promise.resolve({ id: 2, nombre: 'Ana', apellido: 'Pérez', dni: '123', telefono: '456', email: 'a@example.com', activo: false, cuenta: null });
    if (options?.method === 'POST') return Promise.reject(new ApiError(409));
    throw Error(path);
  });
  render(<MemoryRouter><RecordsPage /></MemoryRouter>); fireEvent.click(await screen.findByRole('button', { name: /Ana Pérez/ }));
  fireEvent.click(await screen.findByRole('button', { name: 'Reactivar ficha' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('cambió');
  expect(screen.getByRole('button', { name: 'Actualizar ficha' })).toBeInTheDocument();
});
it('permite buscar por DNI exacto y muestra vacío autorizado', async () => {
  mock.request.mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
  render(<MemoryRouter><RecordsPage /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('DNI de búsqueda'), { target: { value: '12345678' } });
  fireEvent.click(screen.getByRole('button', { name: 'Buscar' }));
  expect(await screen.findByText('No hay fichas para mostrar.')).toBeInTheDocument();
  expect(mock.request).toHaveBeenCalledWith(expect.stringContaining('dni=12345678'));
});
