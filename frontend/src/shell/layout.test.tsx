import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { RoleLayout } from './layout';

vi.mock('../auth/provider', () => ({ useSession: () => ({
  state: { loading: false, profile: { rol: 'paciente', nombre_usuario: 'maria' } },
  session: { logout: vi.fn() },
}) }));

describe('navegación de cuenta', () => {
  it('muestra el área y la navegación del rol sin funciones futuras', () => {
    render(<MemoryRouter><RoleLayout /></MemoryRouter>);
    expect(screen.getByRole('heading', { name: /hola, maria/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Mi cuenta' })).toHaveAttribute('href', '/cuenta');
    expect(screen.getByRole('button', { name: 'Cerrar sesión' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Reservar turno' })).toHaveAttribute('href', '/reservar');
    expect(screen.getByRole('link', { name: 'Mis turnos' })).toHaveAttribute('href', '/mis-turnos');
  });
});
