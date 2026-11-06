import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Link, MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { SessionProvider } from '../auth/provider';
import { AppRoutes } from '../shell/routes';

afterEach(() => { vi.unstubAllGlobals(); window.history.replaceState(null, '', '/'); });

it('recorre consulta, registro, verificación, ingreso y reserva con API simulada', async () => {
  const fetcher = vi.fn(async (url: string, init?: RequestInit) => {
    const path = url.replace('/api/v1', '');
    let status = 200; let body: unknown = {};
    if (path === '/auth/refresh') status = 401;
    else if (path === '/publico/consultorio') body = { nombre: 'Consultorio', telefono: '1234', zona_horaria: 'America/Argentina/Buenos_Aires' };
    else if (path === '/publico/prestaciones') body = [{ id: 1, nombre: 'Consulta', duracion_min: 30 }];
    else if (path === '/publico/profesionales') body = [{ id: 2, nombre: 'Ana Pérez' }];
    else if (path.startsWith('/publico/disponibilidad')) body = [{ inicio: '2026-11-12T12:30:00Z', fin: '2026-11-12T13:00:00Z' }];
    else if (path === '/publico/aviso-privacidad') body = { texto: 'Aviso vigente', version: 'v1' };
    else if (path === '/auth/registro') body = { mensaje: 'Revisá tu correo' };
    else if (path === '/auth/verificar-email') body = { mensaje: 'Correo verificado' };
    else if (path === '/auth/login') body = { access_token: 'token-de-prueba' };
    else if (path === '/auth/me') body = { id: 1, consultorio_id: 1, nombre_usuario: 'ana', email: 'ana@example.com', rol: 'paciente', email_verificado: true };
    else if (path === '/turnos' && init?.method === 'POST') { status = 201; body = { estado: 'pendiente' }; }
    else throw new Error(`Ruta inesperada: ${path}`);
    return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetcher);
  render(<MemoryRouter initialEntries={['/reservar']}><SessionProvider><Link to="/verificar-email" onClick={() => window.history.replaceState(null, '', '/verificar-email#token=prueba')}>Abrir correo simulado</Link><AppRoutes /></SessionProvider></MemoryRouter>);
  await screen.findByText(/Consultorio · 1234/);
  fireEvent.change(screen.getByLabelText('Prestación'), { target: { value: '1' } });
  fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: '2' } });
  fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-12' } });
  fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
  fireEvent.click(await screen.findByRole('button', { name: '09:30' }));
  fireEvent.click(screen.getByRole('link', { name: 'Crear cuenta' }));
  await screen.findByText('Aviso vigente');
  for (const [label, value] of [['Nombre', 'Ana'], ['Apellido', 'Pérez'], ['DNI', '12345678'], ['Teléfono', '123456'], ['Correo electrónico', 'ana@example.com'], ['Nombre de usuario', 'ana'], ['Contraseña', '12345678']]) fireEvent.change(screen.getByLabelText(label), { target: { value } });
  fireEvent.click(screen.getByRole('checkbox')); fireEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }));
  expect(await screen.findByText('Revisá tu correo')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('link', { name: 'Abrir correo simulado' }));
  expect(await screen.findByText('Correo verificado')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('link', { name: 'Ir a ingresar' }));
  fireEvent.change(screen.getByLabelText('Usuario o correo'), { target: { value: 'ana' } });
  fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: '12345678' } });
  fireEvent.click(screen.getByRole('button', { name: 'Ingresar' }));
  fireEvent.click(await screen.findByRole('link', { name: 'Reservar turno' }));
  await screen.findByText(/Consultorio · 1234/);
  expect(screen.getByLabelText('Prestación')).toHaveValue('1');
  fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
  fireEvent.click(await screen.findByRole('button', { name: '09:30' }));
  expect(fetcher.mock.calls.filter(([url, init]) => url.endsWith('/turnos') && init?.method === 'POST')).toHaveLength(0);
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar reserva' }));
  expect(await screen.findByText(/tu turno está reservado/i)).toBeInTheDocument();
  await waitFor(() => expect(fetcher.mock.calls.filter(([url, init]) => url.endsWith('/turnos') && init?.method === 'POST')).toHaveLength(1));
});
