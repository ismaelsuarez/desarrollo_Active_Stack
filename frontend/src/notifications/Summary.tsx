import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useSession } from '../auth/provider';

type Count = number | 'error' | null;
export function Summary({ onSelect, revision = 0 }: { onSelect: (value: 'whatsapp' | 'email') => void; revision?: number }) {
  const { session, state } = useSession();
  const [counts, setCounts] = useState<[Count, Count, Count]>([null, null, null]);
  useEffect(() => {
    let active = true; setCounts([null, null, null]);
    const paths = ['/notificaciones?canal=whatsapp&estado=preparada&limit=100&offset=0', '/notificaciones?canal=email&estado=fallida&limit=100&offset=0', '/turnos?sin_confirmar=true'];
    paths.forEach((path, index) => {
      session.request<unknown[]>(path).then(rows => { if (active) setCounts(current => { const next: [Count, Count, Count] = [...current]; next[index] = rows.length; return next; }); }).catch(() => { if (active) setCounts(current => { const next: [Count, Count, Count] = [...current]; next[index] = 'error'; return next; }); });
    });
    return () => { active = false; };
  }, [session, state.profile?.id, revision]);
  const label = (value: Count, bounded: boolean) => value === null ? 'Cargando' : value === 'error' ? 'No disponible' : bounded && value >= 100 ? '99+' : String(value);
  return <section className="notifications-summary" aria-label="Resumen de operación">
    <button type="button" onClick={() => onSelect('whatsapp')}><span>WhatsApp preparados</span><strong>{label(counts[0], true)}</strong><small>Para enviar manualmente</small></button>
    <button type="button" onClick={() => onSelect('email')}><span>Correos fallidos</span><strong>{label(counts[1], true)}</strong><small>Requiere revisión</small></button>
    <Link to="/sin-confirmar"><span>Turnos sin confirmar</span><strong>{label(counts[2], false)}</strong><small>Para resolver</small></Link>
  </section>;
}
