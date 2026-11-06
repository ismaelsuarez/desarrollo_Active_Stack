import { createEvent, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { Prestaciones, Parametros } from './Catalog';
import { ApiError } from '../api/client';

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock('../auth/provider', () => ({ useSession: () => ({ session: api }) }));
beforeEach(() => api.request.mockReset());

it('crea y luego desactiva una prestación confirmada', async () => {
  api.request.mockResolvedValueOnce([]).mockResolvedValueOnce({ id: 1, nombre: 'Consulta', duracion_min: 30, activa: true, sugerida: false }).mockResolvedValueOnce(undefined);
  render(<Prestaciones />);
  await screen.findByText('No hay prestaciones registradas.');
  fireEvent.change(screen.getByLabelText('Nombre de prestación'), { target: { value: 'Consulta' } });
  fireEvent.change(screen.getByLabelText('Duración en minutos'), { target: { value: '30' } });
  fireEvent.click(screen.getByRole('button', { name: 'Crear prestación' }));
  await screen.findByText(/Consulta · 30 minutos · Activa/);
  expect(api.request).toHaveBeenCalledWith('/prestaciones', { method: 'POST', body: { nombre: 'Consulta', duracion_min: 30 } });
  fireEvent.click(screen.getByRole('button', { name: 'Desactivar Consulta' }));
  await screen.findByText(/Consulta · 30 minutos · Inactiva/);
});
it('conserva datos y explica el duplicado', async () => {
  api.request.mockResolvedValueOnce([]).mockRejectedValueOnce(new ApiError(409));
  render(<Prestaciones />); await screen.findByText('No hay prestaciones registradas.');
  fireEvent.change(screen.getByLabelText('Nombre de prestación'), { target: { value: 'Consulta' } });
  fireEvent.change(screen.getByLabelText('Duración en minutos'), { target: { value: '30' } });
  fireEvent.click(screen.getByRole('button', { name: 'Crear prestación' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/ya existe/i);
  expect(screen.getByLabelText('Nombre de prestación')).toHaveValue('Consulta');
});
it('edita una prestación y rechaza duración inválida sin enviar', async () => {
  api.request.mockResolvedValueOnce([{ id: 1, nombre: 'Consulta', duracion_min: 30, activa: true, sugerida: false }]).mockResolvedValueOnce({ id: 1, nombre: 'Consulta', duracion_min: 45, activa: true, sugerida: false });
  render(<Prestaciones />); await screen.findByText(/Consulta · 30 minutos/);
  fireEvent.click(screen.getByRole('button', { name: 'Editar Consulta' }));
  fireEvent.change(screen.getByLabelText('Duración en minutos'), { target: { value: '0' } });
  fireEvent.click(screen.getByRole('button', { name: 'Guardar prestación' }));
  expect(screen.getByRole('alert')).toHaveTextContent(/duración/); expect(api.request).toHaveBeenCalledTimes(1);
  fireEvent.change(screen.getByLabelText('Duración en minutos'), { target: { value: '45' } });
  fireEvent.click(screen.getByRole('button', { name: 'Guardar prestación' }));
  await screen.findByText(/Consulta · 45 minutos/);
  expect(api.request).toHaveBeenLastCalledWith('/prestaciones/1', { method: 'PATCH', body: { nombre: 'Consulta', duracion_min: 45 } });
});
const config = { modo_liberacion: 'manual', horas_confirmacion: 48, horas_recordatorio: 24, horas_liberacion: 12, horas_limite_paciente: 3, telefono: '123', minutos_granularidad: 15, dias_anticipacion_maxima: 30, max_turnos_activos_paciente: 2 };
it('rechaza notación exponencial en duración y acepta enteros pegados', async () => {
  api.request.mockResolvedValueOnce([]);
  render(<Prestaciones />); await screen.findByText('No hay prestaciones registradas.');
  const input = screen.getByLabelText('Duración en minutos');
  const letter = createEvent.keyDown(input, { key: 'e', cancelable: true });
  fireEvent(input, letter);
  expect(letter.defaultPrevented).toBe(true);
  const shortcut = createEvent.keyDown(input, { key: 'e', ctrlKey: true, cancelable: true });
  fireEvent(input, shortcut);
  expect(shortcut.defaultPrevented).toBe(false);
  const paste = createEvent.paste(input, { clipboardData: { getData: () => '1e2' }, cancelable: true });
  fireEvent(input, paste);
  expect(paste.defaultPrevented).toBe(true);
  const validPaste = createEvent.paste(input, { clipboardData: { getData: () => '120' }, cancelable: true });
  fireEvent(input, validPaste);
  expect(validPaste.defaultPrevented).toBe(false);
  fireEvent.change(input, { target: { value: '30' } });
  fireEvent.change(input, { target: { value: '1e2' } });
  expect(input).toHaveValue(30);
  fireEvent.change(input, { target: { value: '120' } });
  expect(input).toHaveValue(120);
});
it('rechaza notación exponencial en parámetros y conserva enteros válidos', async () => {
  api.request.mockResolvedValueOnce(config);
  render(<Parametros />); await screen.findByDisplayValue('48');
  const input = screen.getByLabelText('Anticipación máxima en días');
  fireEvent.change(input, { target: { value: '2e2' } });
  expect(input).toHaveValue(30);
  fireEvent.change(input, { target: { value: '40' } });
  expect(input).toHaveValue(40);
});
it('guarda parámetros confirmados por el servidor', async () => {
  api.request.mockResolvedValueOnce(config).mockResolvedValueOnce({ ...config, dias_anticipacion_maxima: 45 });
  render(<Parametros />); await screen.findByDisplayValue('30');
  fireEvent.change(screen.getByLabelText('Anticipación máxima en días'), { target: { value: '45' } });
  fireEvent.click(screen.getByRole('button', { name: 'Guardar parámetros' }));
  expect(await screen.findByRole('status')).toHaveTextContent('Parámetros guardados');
  expect(api.request).toHaveBeenCalledWith('/consultorio', { method: 'PATCH', body: { ...config, dias_anticipacion_maxima: 45 } });
});
it('impide plazos desordenados y conserva la entrada', async () => {
  api.request.mockResolvedValueOnce(config);
  render(<Parametros />); await screen.findByDisplayValue('48');
  fireEvent.change(screen.getByLabelText('Confirmación en horas'), { target: { value: '10' } });
  fireEvent.click(screen.getByRole('button', { name: 'Guardar parámetros' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/confirmación.*recordatorio.*liberación/i);
  expect(api.request).toHaveBeenCalledTimes(1);
  expect(screen.getByLabelText('Confirmación en horas')).toHaveValue(10);
});
it('valida límites de reserva y conserva los datos ante rechazo del servidor', async () => {
  api.request.mockResolvedValueOnce(config).mockRejectedValueOnce(new ApiError(422, ['dias_anticipacion_maxima']));
  render(<Parametros />); await screen.findByDisplayValue('48');
  fireEvent.change(screen.getByLabelText('Granularidad en minutos'), { target: { value: '4' } });
  fireEvent.click(screen.getByRole('button', { name: 'Guardar parámetros' }));
  expect(screen.getByRole('alert')).toHaveTextContent(/límites/); expect(api.request).toHaveBeenCalledTimes(1);
  fireEvent.change(screen.getByLabelText('Granularidad en minutos'), { target: { value: '15' } });
  fireEvent.change(screen.getByLabelText('Anticipación máxima en días'), { target: { value: '40' } });
  fireEvent.click(screen.getByRole('button', { name: 'Guardar parámetros' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/revisá los parámetros/i);
  expect(screen.getByLabelText('Anticipación máxima en días')).toHaveValue(40);
  expect(screen.getByLabelText('Anticipación máxima en días')).toHaveAttribute('aria-invalid', 'true');
});
