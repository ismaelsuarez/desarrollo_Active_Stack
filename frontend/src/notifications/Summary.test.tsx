import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { Summary } from './Summary';
const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock('../auth/provider', () => ({ useSession: () => ({ session: api, state: { profile: { id: 1, rol: 'recepcion' } } }) }));
beforeEach(() => { api.request.mockReset(); });
it('presenta tres tarjetas y permite elegir la bandeja', async () => {
  api.request.mockImplementation((path: string) => Promise.resolve(path.includes('whatsapp') ? [{ id: 1 }] : path.includes('email') ? [{ id: 2 }, { id: 3 }] : []));
  const select = vi.fn(); render(<MemoryRouter><Summary onSelect={select} /></MemoryRouter>);
  expect(await screen.findByText('2')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /correos fallidos/i }));
  expect(select).toHaveBeenCalledWith('email');
  expect(screen.getByRole('link', { name: /turnos sin confirmar/i })).toHaveAttribute('href', '/sin-confirmar');
});
it('no presenta error como cero y acota bandejas a 99+', async () => {
  api.request.mockImplementation((path: string) => path.includes('email') ? Promise.reject(new Error('fallo')) : Promise.resolve(path.includes('whatsapp') ? Array.from({ length: 100 }) : []));
  render(<MemoryRouter><Summary onSelect={() => {}} /></MemoryRouter>);
  expect(await screen.findByText('99+')).toBeInTheDocument();
  expect(await screen.findByText('No disponible')).toBeInTheDocument();
});
