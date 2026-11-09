import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import { LinkingPage } from './LinkingPage';
const mock = vi.hoisted(() => ({ request: vi.fn(), id: 1 }));
vi.mock('../auth/provider', () => ({ useSession: () => ({ session: mock, state: { profile: { id: mock.id, rol: 'recepcion' } } }) }));
beforeEach(() => { mock.request.mockReset(); mock.id = 1; });

it('descarta respuestas de otra sesión aunque lleguen después', async () => {
  let finish!: (x: unknown) => void;
  mock.request.mockImplementation((path: string) => {
    if (path.startsWith('/pacientes?')) return Promise.resolve({ items: [], total: 0 });
    if (mock.id === 1) return new Promise(resolve => { finish = resolve; });
    return Promise.resolve({ items: [], total: 0 });
  });
  const view = render(<LinkingPage />);
  mock.id = 2; view.rerender(<LinkingPage />);
  expect(await screen.findByText('No hay solicitudes para mostrar.')).toBeInTheDocument();
  expect(screen.getByRole('region', {name: 'Resultados de solicitudes'})).toHaveTextContent('No hay solicitudes para mostrar.');
  expect(screen.getByRole('region', {name: 'Filtros y búsqueda'})).toBeInTheDocument();
  await act(async () => finish({ items: [{ id: 9, email: 'privado@example.com', estado: 'pendiente', email_verificado: true, dni_declarado: '1' }], total: 1 }));
  expect(screen.queryByText(/privado@example.com/)).not.toBeInTheDocument();
});
it('vincula una solicitud rechazada a la ficha elegida', async () => {
  mock.request.mockImplementation((path: string, options?: { method?: string }) => {
    if (path.startsWith('/solicitudes-vinculacion?')) return Promise.resolve({ items: [{ id: 4, estado: 'rechazada', email: 'ana@example.com', email_verificado: true, dni_declarado: '123' }], total: 1, limit: 20, offset: 0 });
    if (path.startsWith('/pacientes?')) return Promise.resolve({ items: [{ id: 8, nombre: 'Ana', apellido: 'Pérez' }], total: 1 });
    if (options?.method === 'POST') return Promise.resolve({});
    throw Error(path);
  });
  render(<LinkingPage />);
  expect(await screen.findByText(/ana@example.com/)).toBeInTheDocument();
  fireEvent.change(await screen.findByLabelText('Ficha para solicitud 4'), { target: { value: '8' } });
  fireEvent.click(screen.getByRole('button', { name: 'Vincular' }));
  expect(await screen.findByText('Solicitud actualizada.')).toBeInTheDocument();
  expect(mock.request).toHaveBeenCalledWith('/solicitudes-vinculacion/4/vincular', { method: 'POST', body: { paciente_id: 8 } });
});
it('muestra un conflicto recuperable y evita vincular cuentas no verificadas', async () => {
  mock.request.mockImplementation((path: string, options?: { method?: string }) => {
    if (path.startsWith('/solicitudes-vinculacion?')) return Promise.resolve({ items: [{ id: 5, estado: 'pendiente', email: 'x@example.com', email_verificado: false, dni_declarado: '7' }], total: 1, limit: 20, offset: 0 });
    if (path.startsWith('/pacientes?')) return Promise.resolve({ items: [], total: 0 });
    if (options?.method === 'POST') return Promise.reject(new ApiError(409));
    throw Error(path);
  });
  render(<LinkingPage />);
  expect(await screen.findByText('Correo no verificado')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Vincular' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Rechazar' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('cambió');
  expect(screen.getByRole('button', { name: 'Actualizar solicitudes' })).toBeInTheDocument();
});
it('permite buscar la ficha por apellido antes de vincular', async () => {
  mock.request.mockImplementation((path: string) => {
    if (path.startsWith('/solicitudes-vinculacion?')) return Promise.resolve({ items: [{ id: 4, estado: 'pendiente', email: 'ana@example.com', email_verificado: true, dni_declarado: '123' }], total: 1 });
    if (path.startsWith('/pacientes?')) return Promise.resolve({ items: path.includes('apellido=Rojas') ? [{ id: 180, nombre: 'Ana', apellido: 'Rojas' }] : [], total: 0 });
    throw Error(path);
  });
  render(<LinkingPage />); await screen.findByText(/ana@example.com/);
  fireEvent.change(screen.getByLabelText('Buscar ficha por apellido'), { target: { value: 'Rojas' } });
  fireEvent.click(screen.getByRole('button', { name: 'Buscar ficha' }));
  expect(await screen.findByRole('option', { name: 'Ana Rojas (#180)' })).toBeInTheDocument();
});
it('rechaza una pendiente y vuelve a cargar su estado resuelto', async () => {
  let rejected = false;
  mock.request.mockImplementation((path: string, options?: { method?: string }) => {
    if (path.startsWith('/solicitudes-vinculacion?')) return Promise.resolve({ items: [{ id: 5, estado: rejected ? 'rechazada' : 'pendiente', email: 'x@example.com', email_verificado: true, dni_declarado: '7' }], total: 1 });
    if (path.startsWith('/pacientes?')) return Promise.resolve({ items: [], total: 0 });
    if (options?.method === 'POST') { rejected = true; return Promise.resolve({}); }
    throw Error(path);
  });
  render(<LinkingPage />); fireEvent.change(await screen.findByLabelText('Motivo de rechazo 5'), { target: { value: 'Datos incorrectos' } }); fireEvent.click(screen.getByRole('button', { name: 'Rechazar' }));
  expect(await screen.findByText(/rechazada/)).toBeInTheDocument();
  expect(mock.request).toHaveBeenCalledWith('/solicitudes-vinculacion/5/rechazar', { method: 'POST', body: { motivo: 'Datos incorrectos' } });
  expect(screen.queryByRole('button', { name: 'Rechazar' })).not.toBeInTheDocument();
});
it('permite explorar otra página de fichas disponibles', async () => {
  mock.request.mockImplementation((path: string) => {
    if (path.startsWith('/solicitudes-vinculacion?')) return Promise.resolve({ items: [{ id: 4, estado: 'pendiente', email: 'ana@example.com', email_verificado: true, dni_declarado: '123' }], total: 1 });
    if (path.startsWith('/pacientes?')) return Promise.resolve({ items: path.includes('offset=100') ? [{ id: 180, nombre: 'Ana', apellido: 'Rojas' }] : [], total: 101 });
    throw Error(path);
  });
  render(<LinkingPage />); await screen.findByText(/ana@example.com/);
  fireEvent.click(screen.getByRole('button', { name: 'Más fichas' }));
  expect(await screen.findByRole('option', { name: 'Ana Rojas (#180)' })).toBeInTheDocument();
});
