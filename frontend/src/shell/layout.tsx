import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useSession } from '../auth/provider';
import { Button, Notice, PageTemplate } from '../components/ui';
import './layout.css';
import { Counters } from '../notifications/Counters';

export function RoleLayout() {
  const { state, session } = useSession();
  const [logoutError, setLogoutError] = useState(false);
  if (!state.profile) return logoutError ? <Notice kind="warning">No pudimos confirmar el cierre de sesión en el servidor.</Notice> : null;
  const { nombre_usuario, rol } = state.profile;
  return <PageTemplate title={`Hola, ${nombre_usuario}`} description="Este es tu espacio de trabajo.">
    <div className="role-layout">
      {['paciente', 'administrativo'].includes(rol) && <nav aria-label="Navegación de la cuenta">
        <Link to={`/${rol}`}>Inicio</Link>
        <Link to="/cuenta">Mi cuenta</Link>
        {rol === 'paciente' && <><Link to="/reservar">Reservar turno</Link><Link to="/mis-turnos">Mis turnos</Link></>}
        {['recepcion', 'profesional', 'administrador'].includes(rol) && <Link to="/agenda">Agenda</Link>}
        {['recepcion', 'profesional', 'administrador'].includes(rol) && <Link to="/pacientes">Pacientes</Link>}
        {['recepcion', 'administrador'].includes(rol) && <Link to="/solicitudes">Solicitudes</Link>}
        {['recepcion', 'administrador'].includes(rol) && <Link to="/notificaciones">Notificaciones</Link>}
        {rol === 'administrador' && <Link to="/estado-operativo">Estado operativo</Link>}
        {rol === 'administrador' && <Link to="/configuracion">Configuración</Link>}
        {rol === 'administrador' && <Link to="/ausentismo">Ausentismo</Link>}
        <Button variant="secondary" onClick={() => { void session.logout().catch(() => setLogoutError(true)); }}>Cerrar sesión</Button>
      </nav>}
      <section className="role-layout__content">
        {['recepcion', 'profesional', 'administrador'].includes(rol) && <><div className="team-welcome"><div><span>ESPACIO DEL EQUIPO</span><h2>Una agenda clara para trabajar mejor.</h2><p>Accedé a las herramientas del consultorio desde un solo lugar.</p><Link className="team-primary-link" to="/agenda">Ir a la agenda ↗</Link></div><span aria-hidden="true">✳</span></div><div className="team-section-title"><p>ACCESOS RÁPIDOS</p><h2>Tu espacio de trabajo</h2></div><div className="team-quick-grid"><Link to="/agenda"><span aria-hidden="true">▦</span><strong>Agenda</strong><small>Consultá y organizá los turnos.</small></Link><Link to="/pacientes"><span aria-hidden="true">♧</span><strong>Pacientes</strong><small>Buscá y gestioná las fichas.</small></Link>{['recepcion', 'administrador'].includes(rol) && <Link to="/notificaciones"><span aria-hidden="true">◇</span><strong>Notificaciones</strong><small>Revisá mensajes pendientes.</small></Link>}</div></>}
        {['recepcion', 'administrador'].includes(rol) && <section className="team-activity"><h2>Actividad de recepción</h2><p>Revisá los pendientes de comunicación.</p><Counters /></section>}
        {rol === 'administrativo'
          ? <p>Tu cuenta está activa. Las funciones para este rol todavía no están disponibles.</p>
          : rol === 'paciente'
            ? <p>Reservá un turno o revisá tus turnos desde el menú.</p>
            : <p>Elegí una opción del menú para comenzar.</p>}
      </section>
    </div>
  </PageTemplate>;
}
