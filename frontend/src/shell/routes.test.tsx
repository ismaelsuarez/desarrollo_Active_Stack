import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AppRoutes } from './routes';

const mockSession = vi.hoisted(() => ({ state: { loading: false, profile: null as null | { rol: string; nombre_usuario: string } }, session: { logout: vi.fn() } }));
vi.mock('../auth/provider', () => ({ useSession: () => mockSession }));
vi.mock('../pages/public', () => ({ LoginPage: () => <p>Formulario ingreso</p>, RegisterPage: () => <p>Registro</p>, EmailRequestPage: () => <p>Correo</p>, TokenActionPage: () => <p>Enlace</p>, ResetPasswordPage: () => <p>Restablecer</p> }));
vi.mock('../account/AccountPage', () => ({ AccountPage: () => <p>Cuenta privada</p> }));
vi.mock('../booking/BookingPage', () => ({ BookingPage: () => <p>Reserva pública</p> }));
vi.mock('../booking/AppointmentsPage', () => ({ AppointmentsPage: () => <p>Turnos privados</p> }));
vi.mock('../staff/AgendaPage', () => ({ AgendaPage: () => <p>Agenda del personal</p> }));
vi.mock('../records/RecordsPage', () => ({ RecordsPage: () => <p>Fichas autorizadas</p> }));
vi.mock('../records/LinkingPage', () => ({ LinkingPage: () => <p>Solicitudes del personal</p> }));
vi.mock('../admin/AdminPage', () => ({ AdminPage: () => <p>Configuración del consultorio</p> }));
vi.mock('../notifications/NotificationsPage', () => ({ NotificationsPage: () => <p>Operación de notificaciones</p>, HealthPage: () => <p>Salud operativa</p> }));
vi.mock('../notifications/Unconfirmed', () => ({ Unconfirmed: () => <p>Turnos sin confirmar pendientes</p> }));
vi.mock('../notifications/Counters', () => ({ Counters: () => <p>Indicadores operativos</p> }));
vi.mock('../indicators/AbsenteeismPage', () => ({ AbsenteeismPage: () => <p>Informe de ausentismo</p> }));

describe('rutas', () => {
  beforeEach(() => { mockSession.state = { loading: false, profile: null }; });
  it('ofrece ausentismo solo al administrador', () => {
    mockSession.state.profile = { rol: 'administrador', nombre_usuario: 'ana' };
    const admin = render(<MemoryRouter initialEntries={['/administrador']}><AppRoutes /></MemoryRouter>);
    expect(screen.getByRole('link', { name: 'Ausentismo' })).toHaveAttribute('href', '/ausentismo');
    admin.unmount();
    mockSession.state.profile = { rol: 'recepcion', nombre_usuario: 'ana' };
    render(<MemoryRouter initialEntries={['/recepcion']}><AppRoutes /></MemoryRouter>);
    expect(screen.queryByRole('link', { name: 'Ausentismo' })).not.toBeInTheDocument();
  });
  it('protege el informe de ausentismo para los demás roles', () => {
    for (const rol of ['administrador', 'recepcion', 'profesional', 'paciente', 'administrativo']) {
      mockSession.state.profile = { rol, nombre_usuario: 'ana' };
      const view = render(<MemoryRouter initialEntries={['/ausentismo']}><AppRoutes /></MemoryRouter>);
      if (rol === 'administrador') expect(screen.getByText('Informe de ausentismo')).toBeInTheDocument();
      else expect(screen.queryByText('Informe de ausentismo')).not.toBeInTheDocument();
      view.unmount();
    }
  });
  it('restringe notificaciones a recepción y administración y salud solo a administración', () => {
    for (const rol of ['recepcion', 'administrador']) {
      mockSession.state.profile = { rol, nombre_usuario: 'ana' };
      const view = render(<MemoryRouter initialEntries={['/notificaciones']}><AppRoutes /></MemoryRouter>);
      expect(screen.getByText('Operación de notificaciones')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: 'Notificaciones' })).toHaveAttribute('href', '/notificaciones');
      view.unmount();
    }
    for (const rol of ['profesional', 'paciente']) {
      mockSession.state.profile = { rol, nombre_usuario: 'ana' };
      const view = render(<MemoryRouter initialEntries={['/notificaciones']}><AppRoutes /></MemoryRouter>);
      expect(screen.queryByText('Operación de notificaciones')).not.toBeInTheDocument();
      view.unmount();
    }
    mockSession.state.profile = { rol: 'recepcion', nombre_usuario: 'ana' };
    const denied = render(<MemoryRouter initialEntries={['/estado-operativo']}><AppRoutes /></MemoryRouter>);
    expect(screen.queryByText('Salud operativa')).not.toBeInTheDocument();
    denied.unmount();
    mockSession.state.profile = { rol: 'administrador', nombre_usuario: 'ana' };
    const admin = render(<MemoryRouter initialEntries={['/estado-operativo']}><AppRoutes /></MemoryRouter>);
    expect(screen.getByText('Salud operativa')).toBeInTheDocument();
    admin.unmount();
    mockSession.state.profile = null;
    render(<MemoryRouter initialEntries={['/notificaciones']}><AppRoutes /></MemoryRouter>);
    expect(screen.getByText('Formulario ingreso')).toBeInTheDocument();
  });
  it('protege la lista sin confirmar para recepción y administrador', () => {
    for (const rol of ['recepcion', 'administrador', 'profesional']) {
      mockSession.state.profile = { rol, nombre_usuario: 'ana' };
      const view = render(<MemoryRouter initialEntries={['/sin-confirmar']}><AppRoutes /></MemoryRouter>);
      if (rol === 'profesional') expect(screen.queryByText('Turnos sin confirmar pendientes')).not.toBeInTheDocument();
      else expect(screen.getByText('Turnos sin confirmar pendientes')).toBeInTheDocument();
      view.unmount();
    }
  });
  it('permite configuración solamente al administrador', () => {
    mockSession.state.profile = { rol: 'administrador', nombre_usuario: 'ana' };
    const admin = render(<MemoryRouter initialEntries={['/configuracion']}><AppRoutes /></MemoryRouter>);
    expect(screen.getByText('Configuración del consultorio')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Configuración' })).toHaveAttribute('href', '/configuracion');
    admin.unmount();
    for (const rol of ['paciente', 'recepcion', 'profesional', 'administrativo']) {
      mockSession.state.profile = { rol, nombre_usuario: 'ana' };
      const view = render(<MemoryRouter initialEntries={['/configuracion']}><AppRoutes /></MemoryRouter>);
      expect(screen.queryByText('Configuración del consultorio')).not.toBeInTheDocument();
      view.unmount();
    }
    mockSession.state.profile = null;
    render(<MemoryRouter initialEntries={['/configuracion']}><AppRoutes /></MemoryRouter>);
    expect(screen.getByText('Formulario ingreso')).toBeInTheDocument();
    expect(screen.queryByText('Configuración del consultorio')).not.toBeInTheDocument();
  });
  it('ofrece configuración desde el inicio del administrador', () => {
    mockSession.state.profile = { rol: 'administrador', nombre_usuario: 'ana' };
    render(<MemoryRouter initialEntries={['/administrador']}><AppRoutes /></MemoryRouter>);
    expect(screen.getByRole('link', { name: 'Configuración' })).toHaveAttribute('href', '/configuracion');
  });
  it('restringe agenda al personal autorizado', () => {
    mockSession.state.profile = { rol: 'profesional', nombre_usuario: 'maria' };
    const view = render(<MemoryRouter initialEntries={['/agenda']}><AppRoutes /></MemoryRouter>);
    expect(screen.getByText('Agenda del personal')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Pacientes' })).toHaveAttribute('href', '/pacientes');
    expect(screen.queryByRole('link', { name: 'Solicitudes' })).not.toBeInTheDocument();
    view.unmount();
    mockSession.state.profile = { rol: 'paciente', nombre_usuario: 'maria' };
    render(<MemoryRouter initialEntries={['/agenda']}><AppRoutes /></MemoryRouter>);
    expect(screen.queryByText('Agenda del personal')).not.toBeInTheDocument();
  });
  it('restringe solicitudes a recepción y administración y fichas al personal', () => {
    mockSession.state.profile = { rol: 'profesional', nombre_usuario: 'maria' };
    const view = render(<MemoryRouter initialEntries={['/pacientes']}><AppRoutes /></MemoryRouter>);
    expect(screen.getByText('Fichas autorizadas')).toBeInTheDocument();
    view.unmount();
    const denied = render(<MemoryRouter initialEntries={['/solicitudes']}><AppRoutes /></MemoryRouter>);
    expect(screen.queryByText('Solicitudes del personal')).not.toBeInTheDocument();
    denied.unmount();
    mockSession.state.profile = { rol: 'recepcion', nombre_usuario: 'maria' };
    render(<MemoryRouter initialEntries={['/solicitudes']}><AppRoutes /></MemoryRouter>);
    expect(screen.getByText('Solicitudes del personal')).toBeInTheDocument();
  });
  it('abre la reserva pública sin sesión', () => {
    render(<MemoryRouter initialEntries={['/reservar']}><AppRoutes /></MemoryRouter>);
    expect(screen.getByText('Reserva pública')).toBeInTheDocument();
  });
  it('protege la lista de turnos y permite el acceso al paciente', () => {
    const view = render(<MemoryRouter initialEntries={['/mis-turnos']}><AppRoutes /></MemoryRouter>);
    expect(screen.queryByText('Turnos privados')).not.toBeInTheDocument();
    view.unmount();
    mockSession.state.profile = { rol: 'paciente', nombre_usuario: 'maria' };
    render(<MemoryRouter initialEntries={['/mis-turnos']}><AppRoutes /></MemoryRouter>);
    expect(screen.getByText('Turnos privados')).toBeInTheDocument();
  });
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
