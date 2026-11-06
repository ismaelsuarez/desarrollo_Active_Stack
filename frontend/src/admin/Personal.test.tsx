import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { Personal } from './Personal';
import { ApiError } from '../api/client';

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock('../auth/provider', () => ({ useSession: () => ({ session: api, state: { profile: { id: 1, rol: 'administrador' } } }) }));

beforeEach(() => { api.request.mockReset(); });
it('muestra carga, error de lectura y lista vacía tras actualización explícita', async () => {
  let rejectRead: (reason: Error) => void = () => {};
  api.request.mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectRead = reject; })).mockResolvedValueOnce([]);
  render(<Personal />);
  expect(screen.getByRole('status')).toHaveTextContent('Cargando personal');
  rejectRead(new Error('sin conexión'));
  expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos cargar el personal');
  fireEvent.click(screen.getByRole('button', { name: 'Actualizar lista' }));
  expect(await screen.findByText('No hay personal registrado.')).toBeInTheDocument();
  expect(api.request).toHaveBeenCalledTimes(2);
});
it('crea una cuenta de personal y actualiza la lista confirmada', async () => {
  api.request.mockResolvedValueOnce([]).mockResolvedValueOnce({ id: 2, nombre_usuario: 'ana', email: 'ana@example.com', rol: 'recepcion', activo: true });
  render(<Personal />);
  await screen.findByText('No hay personal registrado.');
  fireEvent.change(screen.getByLabelText('Usuario'), { target: { value: 'ana' } });
  fireEvent.change(screen.getByLabelText('Correo'), { target: { value: 'ana@example.com' } });
  fireEvent.change(screen.getByLabelText('Contraseña inicial'), { target: { value: '123456789012' } });
  fireEvent.click(screen.getByRole('button', { name: 'Crear personal' }));
  await screen.findByText(/ana@example.com/);
  expect(api.request).toHaveBeenCalledWith('/usuarios', { method: 'POST', body: { nombre_usuario: 'ana', email: 'ana@example.com', password: '123456789012', rol: 'recepcion' } });
});
it('conserva datos ante conflicto y no informa éxito', async () => {
  api.request.mockResolvedValueOnce([]).mockRejectedValueOnce(new Error('sin conexión'));
  render(<Personal />);
  await screen.findByText('No hay personal registrado.');
  fireEvent.change(screen.getByLabelText('Usuario'), { target: { value: 'ana' } });
  fireEvent.change(screen.getByLabelText('Correo'), { target: { value: 'ana@example.com' } });
  fireEvent.change(screen.getByLabelText('Contraseña inicial'), { target: { value: '123456789012' } });
  fireEvent.click(screen.getByRole('button', { name: 'Crear personal' }));
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/resultado/i));
  expect(screen.getByLabelText('Usuario')).toHaveValue('ana');
  expect(api.request.mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(1);
});
it('edita y desactiva sin borrar el historial mostrado', async () => {
  const initial = { id: 2, nombre_usuario: 'ana', email: 'ana@example.com', rol: 'recepcion', activo: true };
  api.request.mockResolvedValueOnce([initial]).mockResolvedValueOnce({ ...initial, rol: 'profesional' }).mockResolvedValueOnce(undefined);
  render(<Personal />);
  await screen.findByText(/ana@example.com/);
  fireEvent.click(screen.getByRole('button', { name: 'Editar ana' }));
  fireEvent.change(screen.getByLabelText('Rol'), { target: { value: 'profesional' } });
  fireEvent.click(screen.getByRole('button', { name: 'Guardar personal' }));
  await screen.findByText(/profesional · Activo/);
  expect(api.request).toHaveBeenCalledWith('/usuarios/2', { method: 'PATCH', body: { nombre_usuario: 'ana', email: 'ana@example.com', rol: 'profesional' } });
  fireEvent.click(screen.getByRole('button', { name: 'Desactivar ana' }));
  await screen.findByText(/profesional · Inactivo/);
  expect(screen.getByText(/se conserva su historial/i)).toBeInTheDocument();
});
it('muestra el campo rechazado y conserva los datos', async () => {
  api.request.mockResolvedValueOnce([]).mockRejectedValueOnce(new ApiError(422, ['email']));
  render(<Personal />);
  await screen.findByText('No hay personal registrado.');
  fireEvent.change(screen.getByLabelText('Usuario'), { target: { value: 'ana' } });
  fireEvent.change(screen.getByLabelText('Correo'), { target: { value: 'ana@example.com' } });
  fireEvent.change(screen.getByLabelText('Contraseña inicial'), { target: { value: '123456789012' } });
  fireEvent.click(screen.getByRole('button', { name: 'Crear personal' }));
  await screen.findByText('Revisá el correo.');
  expect(screen.getByLabelText('Correo')).toHaveValue('ana@example.com');
});
it('explica el conflicto de cuenta duplicada y limita los roles disponibles', async () => {
  api.request.mockResolvedValueOnce([]).mockRejectedValueOnce(new ApiError(409));
  render(<Personal />);
  await screen.findByText('No hay personal registrado.');
  expect(screen.getAllByRole('option').map(option => option.getAttribute('value'))).toEqual(['recepcion', 'profesional', 'administrador', 'administrativo']);
  fireEvent.change(screen.getByLabelText('Usuario'), { target: { value: 'ana' } });
  fireEvent.change(screen.getByLabelText('Correo'), { target: { value: 'ana@example.com' } });
  fireEvent.change(screen.getByLabelText('Contraseña inicial'), { target: { value: '123456789012' } });
  fireEvent.click(screen.getByRole('button', { name: 'Crear personal' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('ya está registrado');
  expect(screen.getByLabelText('Usuario')).toHaveValue('ana');
});
