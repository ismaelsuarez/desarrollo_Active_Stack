import { useEffect, useRef } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useSession } from '../auth/provider';
import { Counters } from '../notifications/Counters';
import './staff-nav.css';

export function StaffNav() {
  const { state } = useSession();
  const role = state.profile?.rol;
  const { pathname } = useLocation();
  const nav = useRef<HTMLElement>(null);
  useEffect(() => {
    const container = nav.current;
    const current = container?.querySelector<HTMLElement>('[aria-current="page"]');
    if (!container || !current || container.scrollWidth <= container.clientWidth) return;
    const bounds = container.getBoundingClientRect();
    const item = current.getBoundingClientRect();
    if (item.right > bounds.right) container.scrollLeft += item.right - bounds.right;
    else if (item.left < bounds.left) container.scrollLeft -= bounds.left - item.left;
  }, [pathname, role]);
  return <header className="staff-header">
    <nav ref={nav} aria-label="Navegación principal"><NavLink to={`/${role}`}>Inicio</NavLink><NavLink to="/agenda">Agenda</NavLink><NavLink to="/pacientes">Pacientes</NavLink>{(role === 'administrador' || role === 'recepcion') && <><NavLink to="/solicitudes">Solicitudes</NavLink><NavLink to="/notificaciones">Notificaciones</NavLink></>}{role === 'administrador' && <><NavLink to="/configuracion">Configuración</NavLink><NavLink to="/estado-operativo">Estado operativo</NavLink><NavLink to="/ausentismo">Ausentismo</NavLink></>}<NavLink to="/cuenta">Mi cuenta</NavLink></nav>
    {(role === 'recepcion' || role === 'administrador') && <Counters />}
  </header>;
}
