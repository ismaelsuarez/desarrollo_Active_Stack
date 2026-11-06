import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useSession } from '../auth/provider';

type Count = number | 'error' | null;
export function Counters() {
  const { session, state } = useSession();
  const [whats, setWhats] = useState<Count>(null);
  const [pending, setPending] = useState<Count>(null);
  const [revision, setRevision] = useState(0);
  useEffect(() => { const refresh = () => setRevision(value => value + 1); window.addEventListener('operaciones-actualizadas', refresh); return () => window.removeEventListener('operaciones-actualizadas', refresh); }, []);
  useEffect(() => {
    let active = true;
    setWhats(null); setPending(null);
    session.request<unknown[]>('/notificaciones?canal=whatsapp&estado=preparada&limit=100&offset=0').then(rows => { if (active) setWhats(rows.length); }).catch(() => { if (active) setWhats('error'); });
    session.request<unknown[]>('/turnos?sin_confirmar=true').then(rows => { if (active) setPending(rows.length); }).catch(() => { if (active) setPending('error'); });
    return () => { active = false; };
  }, [session, state.profile?.id, revision]);
  const label = (value: Count, bounded = false) => value === null ? 'cargando' : value === 'error' ? 'no disponible' : bounded && value >= 100 ? '99+' : String(value);
  return <div aria-label="Indicadores de recepción"><Link to="/notificaciones">WhatsApp: {label(whats, true)}</Link> <Link to="/sin-confirmar">Sin confirmar: {label(pending)}</Link></div>;
}
