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
      <nav aria-label="Navegación de la cuenta">
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
      </nav>
      <section className="role-layout__content">
        {['recepcion', 'administrador'].includes(rol) && <Counters />}
        {rol === 'administrativo'
          ? <p>Tu cuenta está activa. Las funciones para este rol todavía no están disponibles.</p>
          : rol === 'administrador'
            ? <p>Elegí una opción del menú para comenzar.</p>
            : <p>Las funciones de {rol} se incorporarán más adelante.</p>}
      </section>
    </div>
  </PageTemplate>;
}
