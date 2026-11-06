import { render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { HealthPage } from './NotificationsPage';
const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock('../auth/provider', () => ({ useSession: () => ({ session: api, state: { profile: { id: 1, rol: 'administrador' } } }) }));
beforeEach(() => { api.request.mockReset(); });
const health = { fallidas: 0, programada_mas_antigua_segundos: null, enviando: 2, enviando_mas_antigua_segundos: 7200, correos_del_dia: 395, limite_diario: 500, alerta: false, ultimo_barrido: null };
it('muestra cuota sin alerta antes del umbral y antigüedad de enviando', async () => {
  api.request.mockResolvedValueOnce(health);
  render(<HealthPage />);
  expect(await screen.findByText(/395 de 500/)).toBeInTheDocument();
  expect(screen.queryByText(/alerta de cuota/i)).not.toBeInTheDocument();
  expect(screen.getByText(/7200 segundos/)).toBeInTheDocument();
  expect(screen.getByText(/sin barridos registrados/i)).toBeInTheDocument();
});
it('muestra alerta del servidor y advierte barrido antiguo', async () => {
  api.request.mockResolvedValueOnce({ ...health, correos_del_dia: 400, alerta: true, ultimo_barrido: { iniciado_en: '2020-01-01T00:00:00Z' } });
  render(<HealthPage />);
  expect(await screen.findByText(/alerta de cuota/i)).toBeInTheDocument();
  expect(screen.getByText(/barrido antiguo/i)).toBeInTheDocument();
});
it('muestra un error sin inventar ceros', async () => {
  api.request.mockRejectedValueOnce(new Error('sin conexión'));
  render(<HealthPage />);
  expect(await screen.findByRole('alert')).toHaveTextContent(/no pudimos cargar/i);
  expect(screen.queryByText(/0 de 500/)).not.toBeInTheDocument();
});
it('muestra ceros y antigüedad desconocida cuando corresponde', async () => {
  api.request.mockResolvedValueOnce({ ...health, enviando: 0, enviando_mas_antigua_segundos: null, correos_del_dia: 0, ultimo_barrido: { iniciado_en: new Date().toISOString() } });
  render(<HealthPage />);
  expect(await screen.findByText(/0 de 500/)).toBeInTheDocument();
  expect(screen.getByText(/Enviando: 0 · antigüedad: No disponible/)).toBeInTheDocument();
  expect(screen.queryByText(/barrido antiguo/i)).not.toBeInTheDocument();
});
