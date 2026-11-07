import { Link, Navigate, Route, Routes } from 'react-router-dom';
import { useSession } from '../auth/provider';
import { Guard } from '../auth/guard';
import type { Role } from '../auth/session';
import { LoginPage, RegisterPage, EmailRequestPage, TokenActionPage, ResetPasswordPage } from '../pages/public';
import { AccountPage } from '../account/AccountPage';
import { RoleLayout } from './layout';
import { PageTemplate } from '../components/ui';
import { BookingPage } from '../booking/BookingPage';
import { AppointmentsPage } from '../booking/AppointmentsPage';
import { AgendaPage } from '../staff/AgendaPage';
import { RecordsPage } from '../records/RecordsPage';
import { LinkingPage } from '../records/LinkingPage';
import { StaffNav } from './StaffNav';
import { AdminPage } from '../admin/AdminPage';
import { NotificationsPage, HealthPage } from '../notifications/NotificationsPage';
import { Unconfirmed } from '../notifications/Unconfirmed';
import { AbsenteeismPage } from '../indicators/AbsenteeismPage';

function Entry() {
  const { state } = useSession();
  if (state.loading) return <main><p role="status">Estamos verificando tu sesión. Esperá un momento.</p></main>;
  if (state.profile) return <Navigate to={`/${state.profile.rol}`} replace />;
  return <LoginPage />;
}

export function AppRoutes() {
  const roles: Role[] = ['paciente', 'recepcion', 'profesional', 'administrador', 'administrativo'];
  return <Routes>
    <Route path="/" element={<Entry />} />
    <Route path="/ingresar" element={<Entry />} />
    <Route path="/reservar" element={<BookingPage />} />
    <Route path="/mis-turnos" element={<Guard roles={['paciente']}><AppointmentsPage /></Guard>} />
    <Route path="/agenda" element={<Guard roles={['recepcion', 'profesional', 'administrador']}><StaffNav /><AgendaPage /></Guard>} />
    <Route path="/pacientes" element={<Guard roles={['recepcion', 'profesional', 'administrador']}><StaffNav /><RecordsPage /></Guard>} />
    <Route path="/solicitudes" element={<Guard roles={['recepcion', 'administrador']}><StaffNav /><LinkingPage /></Guard>} />
    <Route path="/configuracion/*" element={<Guard roles={['administrador']}><StaffNav /><AdminPage /></Guard>} />
    <Route path="/notificaciones" element={<Guard roles={['recepcion', 'administrador']}><StaffNav /><NotificationsPage /></Guard>} />
    <Route path="/sin-confirmar" element={<Guard roles={['recepcion', 'administrador']}><StaffNav /><Unconfirmed /></Guard>} />
    <Route path="/estado-operativo" element={<Guard roles={['administrador']}><StaffNav /><HealthPage /></Guard>} />
    <Route path="/ausentismo" element={<Guard roles={['administrador']}><StaffNav /><AbsenteeismPage /></Guard>} />
    <Route path="/registro" element={<RegisterPage />} />
    <Route path="/recuperar-password" element={<EmailRequestPage mode="recover" />} />
    <Route path="/reenviar-verificacion" element={<EmailRequestPage mode="resend" />} />
    <Route path="/verificar-email" element={<TokenActionPage action="verify" />} />
    <Route path="/restablecer-password" element={<ResetPasswordPage />} />
    <Route path="/restablecer" element={<ResetPasswordPage />} />
    <Route path="/confirmar-turno" element={<TokenActionPage action="confirm" />} />
    <Route path="/confirmar" element={<TokenActionPage action="confirm" />} />
    <Route path="/cuenta" element={<Guard><AccountPage /></Guard>} />
    {roles.map(role => <Route key={role} path={`/${role}`} element={<Guard roles={[role]}><RoleLayout /></Guard>} />)}
    <Route path="*" element={<PageTemplate title="Página no encontrada"><p>No encontramos la página que buscabas.</p><Link to="/">Ir al inicio</Link></PageTemplate>} />
  </Routes>;
}
