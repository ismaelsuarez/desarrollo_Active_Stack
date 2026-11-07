import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { AbsenteeismPage } from './AbsenteeismPage';

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock('../auth/provider', () => ({ useSession: () => ({ session: api }) }));
beforeEach(() => api.request.mockReset());

it('presenta el indicador y consulta el período y profesional elegidos', async () => {
  api.request.mockImplementation((path: string) => path === '/profesionales'
    ? Promise.resolve([{ id: 4, nombre: 'Ana', apellido: 'Pérez' }])
    : Promise.resolve({ resumen: { ausentes: 2, atendidos: 8, cancelados: 3, liberados: 4, sin_cierre: 1, tasa: 0.2 }, evolucion: [], profesionales: [] }));
  render(<AbsenteeismPage />);
  expect(await screen.findByText('20 %')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-01-01' } });
  fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-02-01' } });
  fireEvent.change(await screen.findByLabelText('Profesional'), { target: { value: '4' } });
  fireEvent.click(screen.getByRole('button', { name: 'Consultar' }));
  await waitFor(() => expect(api.request).toHaveBeenCalledWith('/indicadores/ausentismo?desde=2026-01-01&hasta=2026-02-01&profesional_id=4'));
});

it('informa tasa nula, vacío y permite reintentar ante error', async () => {
  api.request.mockImplementation((path: string) => path === '/profesionales' ? Promise.resolve([]) : Promise.resolve({ resumen: { ausentes: 0, atendidos: 0, cancelados: 0, liberados: 0, sin_cierre: 0, tasa: null }, evolucion: [], profesionales: [] }));
  render(<AbsenteeismPage />);
  expect(await screen.findByText('Sin datos')).toBeInTheDocument();
  expect(screen.getByText('Sin datos para este período.')).toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: 'Evolución mensual' })).not.toBeInTheDocument();
  api.request.mockImplementation((path: string) => path === '/profesionales' ? Promise.resolve([]) : Promise.reject(new Error('offline')));
  fireEvent.click(screen.getByRole('button', { name: 'Consultar' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos cargar');
  api.request.mockImplementation((path: string) => path === '/profesionales' ? Promise.resolve([]) : Promise.resolve({ resumen: { ausentes: 0, atendidos: 0, cancelados: 0, liberados: 0, sin_cierre: 0, tasa: null }, evolucion: [], profesionales: [] }));
  fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
  expect(await screen.findByText('Sin datos para este período.')).toBeInTheDocument();
});

it('muestra evolución mensual y detalle por profesional', async () => {
  const counts = { ausentes: 1, atendidos: 3, cancelados: 0, liberados: 0, sin_cierre: 0, tasa: 0.25 };
  api.request.mockImplementation((path: string) => path === '/profesionales' ? Promise.resolve([]) : Promise.resolve({ resumen: counts, evolucion: [{ ...counts, mes: '2026-09', tasa: 0.5 }, { ...counts, mes: '2026-10' }], profesionales: [{ ...counts, profesional_id: 1, nombre: 'Ana Pérez' }] }));
  render(<AbsenteeismPage />);
  expect(await screen.findByText('Ana Pérez')).toBeInTheDocument();
  expect(screen.getByRole('meter', { name: '2026-10: 25 %' })).toHaveAttribute('aria-valuenow', '25');
  expect(screen.getByRole('meter', { name: '2026-10: 25 %' })).toHaveStyle({ height: '50%' });
});

it('no reemplaza el resultado reciente por una respuesta anterior tardía', async () => {
  let finishFirst!: (value: unknown) => void;
  const pending = new Promise(resolve => { finishFirst = resolve; });
  const data = (absent: number) => ({ resumen: { ausentes: absent, atendidos: 1, cancelados: 0, liberados: 0, sin_cierre: 0, tasa: absent / (absent + 1) }, evolucion: [], profesionales: [] });
  api.request.mockImplementation((path: string) => path === '/profesionales' ? Promise.resolve([]) : pending);
  render(<AbsenteeismPage />);
  api.request.mockImplementation((path: string) => path === '/profesionales' ? Promise.resolve([]) : Promise.resolve(data(3)));
  fireEvent.click(screen.getByRole('button', { name: 'Consultar' }));
  expect(await screen.findByText('75 %')).toBeInTheDocument();
  await act(async () => { finishFirst(data(1)); await pending; });
  expect(screen.getByText('75 %')).toBeInTheDocument();
});

it('permite recuperar la lista de profesionales si falla su carga', async () => {
  let fail = true;
  api.request.mockImplementation((path: string) => path === '/profesionales' ? (fail ? Promise.reject(new Error('offline')) : Promise.resolve([{ id: 4, nombre: 'Ana', apellido: 'Pérez' }])) : Promise.resolve({ resumen: { ausentes: 0, atendidos: 0, cancelados: 0, liberados: 0, sin_cierre: 0, tasa: null }, evolucion: [], profesionales: [] }));
  render(<AbsenteeismPage />);
  expect(await screen.findByText('No pudimos cargar los profesionales.')).toBeInTheDocument();
  fail = false;
  fireEvent.click(screen.getByRole('button', { name: 'Reintentar profesionales' }));
  expect(await screen.findByRole('option', { name: 'Ana Pérez' })).toBeInTheDocument();
});
