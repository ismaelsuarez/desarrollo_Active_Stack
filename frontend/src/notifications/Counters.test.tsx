import { act, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { Counters } from './Counters';

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock('../auth/provider', () => ({ useSession: () => ({ session: api, state: { profile: { id: 1, rol: 'recepcion' } } }) }));
beforeEach(() => { api.request.mockReset(); });
it.each([[0, '0'], [99, '99'], [100, '99+']])('muestra conteo acotado con %s resultados', async (size, expected) => {
  api.request.mockImplementation((path: string) => Promise.resolve(path.startsWith('/notificaciones') ? Array.from({ length: size }) : []));
  render(<MemoryRouter><Counters /></MemoryRouter>);
  expect(await screen.findByText(`WhatsApp: ${expected}`)).toBeInTheDocument();
  expect(screen.getByText('Sin confirmar: 0')).toBeInTheDocument();
});
it('muestra error desconocido en lugar de cero', async () => {
  api.request.mockRejectedValue(new Error('sin conexión'));
  render(<MemoryRouter><Counters /></MemoryRouter>);
  expect(await screen.findByText('WhatsApp: no disponible')).toBeInTheDocument();
  expect(screen.getByText('Sin confirmar: no disponible')).toBeInTheDocument();
});
it('muestra carga mientras ambos conteos están pendientes', () => {
  api.request.mockImplementation(() => new Promise(() => {}));
  render(<MemoryRouter><Counters /></MemoryRouter>);
  expect(screen.getByText('WhatsApp: cargando')).toBeInTheDocument();
  expect(screen.getByText('Sin confirmar: cargando')).toBeInTheDocument();
});
it('actualiza contadores al cambiar una notificación o turno', async () => {
  let count = 1;
  api.request.mockImplementation((path: string) => Promise.resolve(path.startsWith('/notificaciones') ? Array.from({ length: count }) : []));
  render(<MemoryRouter><Counters /></MemoryRouter>);
  expect(await screen.findByText('WhatsApp: 1')).toBeInTheDocument();
  count = 0; act(() => window.dispatchEvent(new Event('operaciones-actualizadas')));
  expect(await screen.findByText('WhatsApp: 0')).toBeInTheDocument();
});
