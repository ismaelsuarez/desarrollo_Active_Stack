import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { Unconfirmed } from './Unconfirmed';
const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock('../auth/provider', () => ({ useSession: () => ({ session: api, state: { profile: { id: 1, rol: 'recepcion' } } }) }));
vi.mock('../staff/StaffTurno', () => ({ StaffTurnoDetalle: ({ turnoId, onClose }: { turnoId: number; onClose: () => void }) => <section>Detalle de turno {turnoId}<button onClick={onClose}>Volver a turnos</button></section> }));
beforeEach(() => { api.request.mockReset(); });
it('muestra turnos y enlaza al detalle para ejecutar acciones autorizadas', async () => {
  api.request.mockResolvedValueOnce([{ id: 4, paciente_nombre: 'Ana', paciente_apellido: 'Pérez', inicio: '2026-11-06T12:00:00Z', acciones_permitidas: ['confirmar'] }]);
  render(<MemoryRouter><Unconfirmed /></MemoryRouter>);
  expect(await screen.findByText(/Ana Pérez/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Ver turno 4' }));
  expect(screen.getByText('Detalle de turno 4')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Volver a turnos' }));
  expect(screen.getByText(/Ana Pérez/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /confirmar turno/i })).not.toBeInTheDocument();
});
it('permite reintentar errores de lectura y presenta vacío', async () => {
  api.request.mockRejectedValueOnce(new Error('error')).mockResolvedValueOnce([]);
  render(<MemoryRouter><Unconfirmed /></MemoryRouter>);
  expect(await screen.findByRole('alert')).toHaveTextContent(/no pudimos cargar/i);
  fireEvent.click(screen.getByRole('button', { name: 'Reintentar lectura' }));
  expect(await screen.findByText('No hay turnos sin confirmar.')).toBeInTheDocument();
});
