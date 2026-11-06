import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, afterEach, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import { NotificationsPage } from './NotificationsPage';

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock('../auth/provider', () => ({ useSession: () => ({ session: api, state: { profile: { id: 1, rol: 'recepcion' } } }) }));
vi.mock('./Summary', () => ({ Summary: () => null }));

beforeEach(() => api.request.mockReset());
afterEach(() => vi.restoreAllMocks());
it('consulta WhatsApp preparado y muestra solo información operativa', async () => {
  api.request.mockResolvedValueOnce([{ id: 8, turno_id: 42, tipo: 'recordatorio', programada_para: '2026-11-06T12:00:00Z' }]);
  render(<MemoryRouter><NotificationsPage /></MemoryRouter>);
  expect(await screen.findByText(/recordatorio/i)).toBeInTheDocument();
  expect(screen.getByText(/Turno 42/)).toBeInTheDocument();
  expect(api.request).toHaveBeenCalledWith('/notificaciones?canal=whatsapp&estado=preparada&limit=20&offset=0');
});
it('indica carga mientras espera la respuesta', () => {
  api.request.mockImplementationOnce(() => new Promise(() => {}));
  render(<MemoryRouter><NotificationsPage /></MemoryRouter>);
  expect(screen.getByRole('status')).toHaveTextContent('Cargando notificaciones');
});
it('muestra error y permite reintentar la lectura', async () => {
  api.request.mockRejectedValueOnce(new Error('sin conexión')).mockResolvedValueOnce([]);
  render(<MemoryRouter><NotificationsPage /></MemoryRouter>);
  expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos cargar');
  fireEvent.click(screen.getByRole('button', { name: 'Reintentar lectura' }));
  expect(await screen.findByText('No hay notificaciones en esta bandeja.')).toBeInTheDocument();
});
it('presenta el tipo de correo en lenguaje claro y los intentos', async () => {
  api.request.mockResolvedValueOnce([]).mockResolvedValueOnce([{ id: 9, turno_id: 42, tipo: 'solicitud_confirmacion', intentos: 3, programada_para: '2026-11-06T12:00:00Z' }]);
  render(<MemoryRouter><NotificationsPage /></MemoryRouter>);
  await screen.findByText('No hay notificaciones en esta bandeja.');
  fireEvent.click(screen.getByRole('button', { name: 'Correos fallidos' }));
  expect(await screen.findByText('Solicitud de confirmación')).toBeInTheDocument();
  expect(screen.getByText(/3 intentos/)).toBeInTheDocument();
});
it('cambia de canal y pagina sin inventar destinatarios', async () => {
  const page = Array.from({ length: 20 }, (_, index) => ({ id: index + 1, turno_id: null, tipo: 'recordatorio', programada_para: '2026-11-06T12:00:00Z' }));
  api.request.mockResolvedValueOnce(page).mockResolvedValueOnce([]).mockResolvedValueOnce([]);
  render(<MemoryRouter><NotificationsPage /></MemoryRouter>);
  expect(await screen.findAllByRole('listitem')).toHaveLength(20);
  fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }));
  expect(await screen.findByText('No hay notificaciones en esta bandeja.')).toBeInTheDocument();
  expect(api.request).toHaveBeenCalledWith('/notificaciones?canal=whatsapp&estado=preparada&limit=20&offset=20');
  fireEvent.click(screen.getByRole('button', { name: 'Correos fallidos' }));
  expect(await screen.findByText('No hay notificaciones en esta bandeja.')).toBeInTheDocument();
  expect(api.request).toHaveBeenCalledWith('/notificaciones?canal=email&estado=fallida&limit=20&offset=0');
});
it('abre enlace de la API y marca enviada por separado', async () => {
  const row = { id: 8, turno_id: 42, tipo: 'recordatorio', programada_para: '2026-11-06T12:00:00Z' };
  api.request.mockResolvedValueOnce([row]).mockResolvedValueOnce({ id: 8, enlace_whatsapp: 'https://wa.me/5491112345678?text=hola' }).mockResolvedValueOnce({ id: 8, estado: 'enviada_manual' }).mockResolvedValueOnce([]);
  const open = vi.spyOn(window, 'open').mockReturnValue({} as Window);
  render(<MemoryRouter><NotificationsPage /></MemoryRouter>);
  await screen.findByText(/recordatorio/i);
  fireEvent.click(screen.getByRole('button', { name: 'Abrir WhatsApp 8' }));
  await screen.findByText(/WhatsApp abierto/);
  expect(open).toHaveBeenCalledWith('https://wa.me/5491112345678?text=hola', '_blank', 'noopener,noreferrer');
  fireEvent.click(screen.getByRole('button', { name: 'Marcar enviada 8' }));
  expect(await screen.findByText(/registro de envío/)).toBeInTheDocument();
  expect(api.request).toHaveBeenCalledWith('/notificaciones/8/marcar-enviada', { method: 'POST' });
});
it('rechaza destino no autorizado sin abrirlo', async () => {
  api.request.mockResolvedValueOnce([{ id: 8, turno_id: 42, tipo: 'recordatorio', programada_para: '2026-11-06T12:00:00Z' }]).mockResolvedValueOnce({ id: 8, enlace_whatsapp: 'https://evil.example/' });
  const open = vi.spyOn(window, 'open');
  render(<MemoryRouter><NotificationsPage /></MemoryRouter>);
  await screen.findByText(/recordatorio/i);
  fireEvent.click(screen.getByRole('button', { name: 'Abrir WhatsApp 8' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('enlace no válido');
  expect(open).not.toHaveBeenCalled();
});
it('informa conflicto y vuelve a consultar sin repetir la escritura', async () => {
  const row = { id: 8, turno_id: 42, tipo: 'recordatorio', programada_para: '2026-11-06T12:00:00Z' };
  api.request.mockResolvedValueOnce([row]).mockRejectedValueOnce(new ApiError(409)).mockResolvedValueOnce([]);
  render(<MemoryRouter><NotificationsPage /></MemoryRouter>);
  await screen.findByText(/recordatorio/i);
  fireEvent.click(screen.getByRole('button', { name: 'Marcar enviada 8' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/cambió/);
  expect(api.request.mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(1);
});
it('ofrece enlace seguro si la ventana no se abre', async () => {
  api.request.mockResolvedValueOnce([{ id: 8, turno_id: 42, tipo: 'recordatorio', programada_para: '2026-11-06T12:00:00Z' }]).mockResolvedValueOnce({ enlace_whatsapp: 'https://wa.me/5491112345678' });
  vi.spyOn(window, 'open').mockReturnValue(null);
  render(<MemoryRouter><NotificationsPage /></MemoryRouter>);
  await screen.findByText(/recordatorio/i);
  fireEvent.click(screen.getByRole('button', { name: 'Abrir WhatsApp 8' }));
  expect(await screen.findByRole('link', { name: /enlace seguro/ })).toHaveAttribute('href', 'https://wa.me/5491112345678');
});
it('ante escritura incierta consulta el estado sin repetir POST', async () => {
  const row = { id: 8, turno_id: 42, tipo: 'recordatorio', programada_para: '2026-11-06T12:00:00Z' };
  api.request.mockResolvedValueOnce([row]).mockRejectedValueOnce(new Error('sin conexión')).mockResolvedValueOnce([]);
  render(<MemoryRouter><NotificationsPage /></MemoryRouter>);
  await screen.findByText(/recordatorio/i);
  fireEvent.click(screen.getByRole('button', { name: 'Marcar enviada 8' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/confirmar el resultado/);
  expect(await screen.findByText('No hay notificaciones en esta bandeja.')).toBeInTheDocument();
  expect(api.request.mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(1);
});
it('evita dos escrituras simultáneas ante doble activación', async () => {
  let resolveWrite: () => void = () => {};
  api.request.mockResolvedValueOnce([{ id: 8, turno_id: 42, tipo: 'recordatorio', programada_para: '2026-11-06T12:00:00Z' }]).mockImplementationOnce(() => new Promise(resolve => { resolveWrite = () => resolve({}); })).mockResolvedValueOnce([]);
  render(<MemoryRouter><NotificationsPage /></MemoryRouter>);
  const button = await screen.findByRole('button', { name: 'Marcar enviada 8' });
  act(() => { button.click(); button.click(); });
  expect(api.request.mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(1);
  await act(async () => resolveWrite());
});

it.each([new ApiError(409), new Error('sin conexión')])('oculta enlace alternativo al cambiar el estado de la notificación (%s)', async error => {
  const row = { id: 8, turno_id: 42, tipo: 'recordatorio', programada_para: '2026-11-06T12:00:00Z' };
  api.request.mockResolvedValueOnce([row]).mockResolvedValueOnce({ enlace_whatsapp: 'https://wa.me/5491112345678' }).mockRejectedValueOnce(error).mockResolvedValueOnce([row]);
  vi.spyOn(window, 'open').mockReturnValue(null);
  render(<MemoryRouter><NotificationsPage /></MemoryRouter>);
  fireEvent.click(await screen.findByRole('button', { name: 'Abrir WhatsApp 8' }));
  expect(await screen.findByRole('link', { name: /enlace seguro/ })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Marcar enviada 8' }));
  await screen.findByRole('alert');
  expect(screen.queryByRole('link', { name: /enlace seguro/ })).not.toBeInTheDocument();
});
