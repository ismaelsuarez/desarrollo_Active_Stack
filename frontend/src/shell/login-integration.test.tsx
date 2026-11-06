import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { SessionProvider } from '../auth/provider';
import { AppRoutes } from './routes';

afterEach(() => vi.unstubAllGlobals());

it.each([
  [401, /no pudimos ingresar/i],
  [403, /verificá tu correo/i],
  [429, /demasiados intentos/i],
])('mantiene visible el error %i después del intento de ingreso', async (status, message) => {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => new Response('{}', {
    status: url.endsWith('/auth/login') ? status : 401,
    headers: { 'Content-Type': 'application/json' },
  })));
  render(<MemoryRouter initialEntries={['/ingresar']}><SessionProvider><AppRoutes /></SessionProvider></MemoryRouter>);
  fireEvent.change(await screen.findByLabelText('Usuario o correo'), { target: { value: 'ana' } });
  fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'incorrecta' } });
  fireEvent.click(screen.getByRole('button', { name: 'Ingresar' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(message);
});
