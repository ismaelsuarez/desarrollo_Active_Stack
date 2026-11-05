import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AppRoutes } from './routes';

const mockSession = vi.hoisted(() => ({ state: { loading: false, profile: null as null | { rol: string; nombre_usuario: string } }, session: { logout: vi.fn() } }));
vi.mock('../auth/provider', () => ({ useSession: () => mockSession }));
vi.mock('../pages/public', () => ({ LoginPage: () => <p>Formulario ingreso</p>, RegisterPage: () => <p>Registro</p>, EmailRequestPage: () => <p>Correo</p>, TokenActionPage: () => <p>Enlace</p>, ResetPasswordPage: () => <p>Restablecer</p> }));
vi.mock('../account/AccountPage', () => ({ AccountPage: () => <p>Cuenta privada</p> }));

describe('rutas', () => {
  beforeEach(() => { mockSession.state = { loading: false, profile: null }; });
  it('resuelve rutas públicas directas sin sesión', () => {
    render(<MemoryRouter initialEntries={['/restablecer']}><AppRoutes /></MemoryRouter>);
    expect(screen.getByText('Restablecer')).toBeInTheDocument();
  });
  it('envía a ingreso al visitante que abre una ruta privada', () => {
    render(<MemoryRouter initialEntries={['/cuenta']}><AppRoutes /></MemoryRouter>);
    expect(screen.getByText('Formulario ingreso')).toBeInTheDocument();
    expect(screen.queryByText('Cuenta privada')).not.toBeInTheDocument();
  });
  it('redirige al área del rol y niega una ruta ajena', () => {
    mockSession.state.profile = { rol: 'profesional', nombre_usuario: 'maria' };
    const view = render(<MemoryRouter initialEntries={['/ingresar']}><AppRoutes /></MemoryRouter>);
    expect(screen.getByRole('heading', { name: /hola, maria/i })).toBeInTheDocument();
    view.unmount();
    render(<MemoryRouter initialEntries={['/administrador']}><AppRoutes /></MemoryRouter>);
    expect(screen.getByText(/no tenés permiso/i)).toBeInTheDocument();
  });
  it('muestra un estado propio al administrativo sin dar acceso a recepción', () => {
    mockSession.state.profile = { rol: 'administrativo', nombre_usuario: 'ana' };
    const view = render(<MemoryRouter initialEntries={['/administrativo']}><AppRoutes /></MemoryRouter>);
    expect(screen.getByText(/funciones para este rol todavía no están disponibles/i)).toBeInTheDocument();
    view.unmount();
    render(<MemoryRouter initialEntries={['/recepcion']}><AppRoutes /></MemoryRouter>);
    expect(screen.getByText(/no tenés permiso/i)).toBeInTheDocument();
  });
  it('informa rutas inexistentes', () => {
    render(<MemoryRouter initialEntries={['/no-existe']}><AppRoutes /></MemoryRouter>);
    expect(screen.getByRole('heading', { name: 'Página no encontrada' })).toBeInTheDocument();
  });
});
