import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { useSession } from '../auth/provider';
import { Counters } from '../notifications/Counters';
import './staff-nav.css';

export function StaffNav() {
  const { state, session } = useSession();
  const [open, setOpen] = useState(false); const [logoutError, setLogoutError] = useState(false);
  const role = state.profile?.rol;
  const { pathname, search } = useLocation();
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
  return <header className={`staff-header ${open ? 'staff-header--open' : ''}`}>
    <Link className="staff-brand" to={`/${role}`}><img src="/logo-provisional.svg" alt="Logo provisional" /><span>Sistema de Turnos y Agenda Odontológica</span></Link>
    <button className="staff-menu-toggle" type="button" aria-expanded={open} aria-controls="staff-navigation" onClick={() => setOpen(value => !value)}>☰ <span>Menú</span></button>
    <div className="staff-mobile-title">Panel del consultorio</div>
    <div className="staff-nav-content"><p className="staff-nav-label">ESPACIO DE TRABAJO</p>
    <nav id="staff-navigation" ref={nav} aria-label="Navegación principal" onClick={() => setOpen(false)}><NavLink to={`/${role}`}><span aria-hidden="true">⌂</span>Inicio</NavLink><NavLink to="/cuenta" state={{returnTo: pathname + search}}><span aria-hidden="true">◉</span>Mi cuenta</NavLink><NavLink to="/agenda"><span aria-hidden="true">▦</span>Agenda</NavLink><NavLink to="/pacientes"><span aria-hidden="true">♧</span>Pacientes</NavLink>{(role === 'administrador' || role === 'recepcion') && <><NavLink to="/solicitudes"><span aria-hidden="true">▤</span>Solicitudes</NavLink><NavLink to="/notificaciones"><span aria-hidden="true">◇</span>Notificaciones</NavLink></>}{role === 'administrador' && <><NavLink to="/estado-operativo"><span aria-hidden="true">◌</span>Estado operativo</NavLink><NavLink to="/configuracion"><span aria-hidden="true">⚙</span>Configuración</NavLink><NavLink to="/ausentismo"><span aria-hidden="true">▥</span>Ausentismo</NavLink></>}</nav>
    <div className="staff-profile"><span className="staff-avatar" aria-hidden="true">{(state.profile?.nombre_usuario ?? 'U').slice(0, 2).toUpperCase()}</span><div><strong>{state.profile?.nombre_usuario}</strong><small>{role}</small></div></div>
    <button className="staff-logout" type="button" onClick={() => { void session.logout().catch(() => setLogoutError(true)); }}>Cerrar sesión</button>
    {logoutError && <p role="status">No pudimos confirmar el cierre de sesión en el servidor.</p>}</div>
    {(role === 'recepcion' || role === 'administrador') && <div className="staff-counters"><Counters /></div>}
  </header>;
}
