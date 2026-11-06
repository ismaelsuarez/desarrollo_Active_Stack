import { Link } from 'react-router-dom';
import { useSession } from '../auth/provider';
import { Counters } from '../notifications/Counters';
import './staff-nav.css';

export function StaffNav() {
  const { state } = useSession();
  const role = state.profile?.rol;
  return <header className="staff-header">
    <nav aria-label="Navegación principal"><Link to={`/${role}`}>Inicio</Link><Link to="/agenda">Agenda</Link><Link to="/pacientes">Pacientes</Link>{(role === 'administrador' || role === 'recepcion') && <><Link to="/solicitudes">Solicitudes</Link><Link to="/notificaciones">Notificaciones</Link></>}{role === 'administrador' && <><Link to="/configuracion">Configuración</Link><Link to="/estado-operativo">Estado operativo</Link></>}<Link to="/cuenta">Mi cuenta</Link></nav>
    {(role === 'recepcion' || role === 'administrador') && <Counters />}
  </header>;
}
