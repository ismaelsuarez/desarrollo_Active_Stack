import { render, screen, waitFor } from '@testing-library/react';
import { StrictMode } from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { SessionProvider, useSession } from './provider';

afterEach(() => vi.unstubAllGlobals());

it('restaura una sola vez bajo StrictMode y publica la sesión', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ access_token: 'secret' })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ id: 1, nombre_usuario: 'María', rol: 'paciente' })));
  vi.stubGlobal('fetch', fetcher);
  function View() { const { state } = useSession(); return <p>{state.profile?.nombre_usuario ?? 'Cargando'}</p>; }
  render(<StrictMode><SessionProvider><View /></SessionProvider></StrictMode>);
  await waitFor(() => expect(screen.getByText('María')).toBeInTheDocument());
  expect(fetcher.mock.calls.filter(([url]) => url === '/api/v1/auth/refresh')).toHaveLength(1);
});
