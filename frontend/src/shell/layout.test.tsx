import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { RoleLayout } from './layout';

const role = vi.hoisted(() => ({ value: 'paciente' }));
vi.mock('../auth/provider', () => ({ useSession: () => ({
  state: { loading: false, profile: { rol: role.value, nombre_usuario: 'maria' } },
  session: { logout: vi.fn() },
}) }));
vi.mock('../notifications/Counters', () => ({ Counters: () => null }));
afterEach(() => { role.value = 'paciente'; });

describe('navegación de cuenta', () => {
  it('muestra el área y la navegación del rol sin funciones futuras', () => {
    render(<MemoryRouter><RoleLayout /></MemoryRouter>);
    expect(screen.getByRole('heading', { name: /hola, maria/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Mi cuenta' })).toHaveAttribute('href', '/cuenta');
    expect(screen.getByRole('button', { name: 'Cerrar sesión' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Reservar turno' })).toHaveAttribute('href', '/reservar');
    expect(screen.getByRole('link', { name: 'Mis turnos' })).toHaveAttribute('href', '/mis-turnos');
  });
  it('orienta al administrador hacia las funciones disponibles', () => {
    role.value = 'administrador';
    render(<MemoryRouter><RoleLayout /></MemoryRouter>);
    expect(screen.getByText('Elegí una opción del menú para comenzar.')).toBeInTheDocument();
    expect(screen.queryByText(/funciones de administrador se incorporarán/i)).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Configuración' })).toHaveAttribute('href', '/configuracion');
  });
});
