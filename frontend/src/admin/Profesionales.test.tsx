import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import { Profesionales } from './Profesionales';

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock('../auth/provider', () => ({ useSession: () => ({ session: api }) }));
beforeEach(() => api.request.mockReset());
const setup = () => api.request.mockImplementation((path: string, options?: { method?: string }) => {
  if (!options?.method && path === '/boxes') return Promise.resolve([{ id: 1, nombre: 'Box 1', activo: true }]);
  if (!options?.method && path === '/usuarios') return Promise.resolve([{ id: 2, nombre_usuario: 'ana', rol: 'profesional', activo: true }]);
  if (!options?.method && path === '/profesionales') return Promise.resolve([]);
  return Promise.resolve({ id: 4, usuario_id: 2, box_id: 1, nombre: 'Ana', apellido: 'Ríos', activo: true });
});
it('crea profesional con cuenta y box disponibles', async () => {
  setup(); render(<Profesionales />);
  await screen.findByText('No hay profesionales registrados.');
  fireEvent.change(screen.getByLabelText('Nombre profesional'), { target: { value: 'Ana' } });
  fireEvent.change(screen.getByLabelText('Apellido profesional'), { target: { value: 'Ríos' } });
  fireEvent.change(screen.getByLabelText('Cuenta'), { target: { value: '2' } });
  fireEvent.change(screen.getByLabelText('Box asignado'), { target: { value: '1' } });
  fireEvent.click(screen.getByRole('button', { name: 'Crear profesional' }));
  await screen.findByText(/Ana Ríos · Box 1 · Activo/);
  expect(api.request).toHaveBeenCalledWith('/profesionales', { method: 'POST', body: { nombre: 'Ana', apellido: 'Ríos', usuario_id: 2, box_id: 1 } });
});
it('conserva formulario y explica box ocupado', async () => {
  setup();
  const implementation = api.request.getMockImplementation()!;
  api.request.mockImplementation((path: string, options?: { method?: string }) => path === '/profesionales' && options?.method === 'POST' ? Promise.reject(new ApiError(409)) : implementation(path, options));
  render(<Profesionales />); await screen.findByText('No hay profesionales registrados.');
  fireEvent.change(screen.getByLabelText('Nombre profesional'), { target: { value: 'Ana' } });
  fireEvent.change(screen.getByLabelText('Apellido profesional'), { target: { value: 'Ríos' } });
  fireEvent.change(screen.getByLabelText('Cuenta'), { target: { value: '2' } });
  fireEvent.change(screen.getByLabelText('Box asignado'), { target: { value: '1' } });
  fireEvent.click(screen.getByRole('button', { name: 'Crear profesional' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/box.*asociad/i);
  expect(screen.getByLabelText('Nombre profesional')).toHaveValue('Ana');
});
it('rechaza cuenta incompatible sin descartar el formulario', async () => {
  setup(); const implementation = api.request.getMockImplementation()!;
  api.request.mockImplementation((path: string, options?: { method?: string }) => path === '/profesionales' && options?.method === 'POST' ? Promise.reject(new ApiError(422)) : implementation(path, options));
  render(<Profesionales />); await screen.findByText('No hay profesionales registrados.');
  fireEvent.change(screen.getByLabelText('Nombre profesional'), { target: { value: 'Ana' } });
  fireEvent.change(screen.getByLabelText('Apellido profesional'), { target: { value: 'Ríos' } });
  fireEvent.change(screen.getByLabelText('Cuenta'), { target: { value: '2' } });
  fireEvent.change(screen.getByLabelText('Box asignado'), { target: { value: '1' } });
  fireEvent.click(screen.getByRole('button', { name: 'Crear profesional' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/cuenta debe ser profesional/);
  expect(screen.getByLabelText('Nombre profesional')).toHaveValue('Ana');
});
it('crea box y desactiva sin eliminar profesional', async () => {
  setup(); const implementation = api.request.getMockImplementation()!;
  const p = { id: 4, usuario_id: 2, box_id: 1, nombre: 'Ana', apellido: 'Ríos', activo: true };
  api.request.mockImplementation((path: string, options?: { method?: string }) => {
    if (path === '/profesionales' && !options?.method) return Promise.resolve([p]);
    if (path === '/profesionales/4') return Promise.resolve({ ...p, activo: false });
    if (path === '/boxes' && options?.method === 'POST') return Promise.resolve({ id: 3, nombre: 'Box 2', activo: true });
    return implementation(path, options);
  });
  render(<Profesionales />); await screen.findByText(/Ana Ríos · Box 1 · Activo/);
  fireEvent.change(screen.getByLabelText('Nombre del box'), { target: { value: 'Box 2' } });
  fireEvent.click(screen.getByRole('button', { name: 'Crear box' }));
  await screen.findByText('Box 2 · Activo');
  fireEvent.click(screen.getByRole('button', { name: 'Desactivar Ana Ríos' }));
  await screen.findByText(/Ana Ríos · Box 1 · Inactivo/);
  expect(api.request).toHaveBeenCalledWith('/profesionales/4', { method: 'PATCH', body: { activo: false } });
});
