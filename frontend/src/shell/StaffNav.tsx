import { Link } from 'react-router-dom';
import { useSession } from '../auth/provider';
import './staff-nav.css';

export function StaffNav() {
  const { state } = useSession();
  const role = state.profile?.rol;
  return <header className="staff-header">
    <nav aria-label="Navegación principal"><Link to={`/${role}`}>Inicio</Link><Link to="/agenda">Agenda</Link><Link to="/pacientes">Pacientes</Link>{(role === 'administrador' || role === 'recepcion') && <Link to="/solicitudes">Solicitudes</Link>}{role === 'administrador' && <Link to="/configuracion">Configuración</Link>}<Link to="/cuenta">Mi cuenta</Link></nav>
  </header>;
}
