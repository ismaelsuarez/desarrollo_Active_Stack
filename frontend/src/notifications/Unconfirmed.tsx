import { useEffect, useState } from 'react';
import { useSession } from '../auth/provider';
import { Button, Notice, PageTemplate } from '../components/ui';
import { StaffTurnoDetalle } from '../staff/StaffTurno';
import './notifications.css';
import { displayClinicTime, useClinicZone } from './time';

type Turno = { id: number; paciente_nombre: string; paciente_apellido: string; inicio: string; acciones_permitidas: string[] };
export function Unconfirmed() {
  const { session, state } = useSession();
  const zone = useClinicZone();
  const [items, setItems] = useState<Turno[] | null>(null);
  const [retry, setRetry] = useState(0);
  const [readError, setReadError] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  useEffect(() => {
    let active = true; setItems(null); setReadError(false);
    session.request<Turno[]>('/turnos?sin_confirmar=true').then(rows => { if (active) setItems(rows); }).catch(() => { if (active) setReadError(true); });
    return () => { active = false; };
  }, [session, state.profile?.id, retry]);
  if (selected !== null) return <PageTemplate title="Detalle del turno"><StaffTurnoDetalle turnoId={selected} onClose={() => setSelected(null)} onSaved={() => { setRetry(n => n + 1); window.dispatchEvent(new Event('operaciones-actualizadas')); }} /></PageTemplate>;
  return <PageTemplate title="Turnos sin confirmar"><p>Consultá y resolvé los turnos que requieren atención.</p>
    {readError && <><Notice kind="error">No pudimos cargar los turnos.</Notice><Button onClick={() => setRetry(n => n + 1)}>Reintentar lectura</Button></>}
    {!items && !readError && <Notice>Cargando turnos…</Notice>}
    {items && (items.length === 0 ? <p>No hay turnos sin confirmar.</p> : <ul className="notifications-list">{items.map(t => <li key={t.id}><div><strong>{t.paciente_nombre} {t.paciente_apellido}</strong><p>{displayClinicTime(t.inicio, zone)}</p></div><div className="notifications-actions"><Button variant="secondary" onClick={() => setSelected(t.id)} aria-label={`Ver turno ${t.id}`}>Ver turno y acciones</Button></div></li>)}</ul>)}
  </PageTemplate>;
}
