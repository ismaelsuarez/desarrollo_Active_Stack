import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { request } from '../api/client';
import { useSession } from '../auth/provider';
import { formatClinicTime } from '../booking/time';
import { Button, Notice, PageTemplate } from '../components/ui';
import { StaffNuevoTurno, StaffTurnoDetalle } from './StaffTurno';
import './agenda.css';

type Clinic = { zona_horaria: string };
type Professional = { id: number; nombre: string; apellido?: string; activo?: boolean };
type Turno = { id: number; inicio: string; paciente_nombre: string; paciente_apellido: string; estado: string; es_sobreturno: boolean; acciones_permitidas: string[] };

export function AgendaPage() {
  const { session, state } = useSession();
  const [params] = useSearchParams();
  const role = state.profile?.rol;
  const userId = state.profile?.id;
  const [date, setDate] = useState('');
  const [zone, setZone] = useState('UTC');
  const [professional, setProfessional] = useState<number | null>(null);
  const [professionals, setProfessionals] = useState<Professional[]>([]);
  const [turnos, setTurnos] = useState<Turno[] | null>(null);
  const [error, setError] = useState('');
  const [initialized, setInitialized] = useState(false);
  const [initRetry, setInitRetry] = useState(0);
  const [retry, setRetry] = useState(0);
  const [view, setView] = useState<'agenda' | 'new' | number>(() => {
    const raw = params.get('turno');
    return raw && /^[1-9]\d*$/.test(raw) && Number.isSafeInteger(Number(raw)) ? Number(raw) : 'agenda';
  });
  useEffect(() => {
    let active = true;
    setInitialized(false); setProfessional(null); setTurnos(null); setError('');
    Promise.all([request<Clinic>('/publico/consultorio'), role === 'profesional' || role === 'administrador' ? session.request<{ profesional_id: number | null }>('/agenda/contexto') : Promise.resolve({ profesional_id: null }), role === 'profesional' ? Promise.resolve([] as Professional[]) : role === 'administrador' ? session.request<Professional[]>('/profesionales') : request<Professional[]>('/publico/profesionales')])
      .then(([clinic, context, list]) => { if (active) { setZone(clinic.zona_horaria); setDate(new Intl.DateTimeFormat('en-CA', { timeZone: clinic.zona_horaria, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())); setProfessional(context.profesional_id); setProfessionals(list); setInitialized(true); } })
      .catch(() => { if (active) setError('No pudimos cargar la agenda.'); });
    return () => { active = false; };
  }, [session, role, userId, initRetry]);
  useEffect(() => {
    setTurnos(null); setError('');
    if (!professional || !date) return;
    let active = true;
    session.request<Turno[]>(`/agenda?${new URLSearchParams({ profesional_id: String(professional), fecha: date })}`)
      .then(result => { if (active) setTurnos(result); })
      .catch(() => { if (active) setError('No pudimos cargar la agenda.'); });
    return () => { active = false; };
  }, [session, professional, date, retry, userId]);
  if (view === 'new') return <PageTemplate title="Dar turno"><StaffNuevoTurno onClose={() => setView('agenda')} onSaved={() => setRetry(n => n + 1)} /></PageTemplate>;
  if (typeof view === 'number') return <PageTemplate title="Detalle del turno"><StaffTurnoDetalle turnoId={view} onClose={() => setView('agenda')} onSaved={() => setRetry(n => n + 1)} /></PageTemplate>;
  return <PageTemplate title={role === 'profesional' ? 'Mi agenda' : 'Agenda'} description="Organizá los turnos del consultorio.">{role !== 'profesional' && <Button onClick={() => setView('new')}>Dar turno</Button>}<div className="staff-filters">{role !== 'profesional' && <label>Profesional<select value={professional ?? ''} onChange={e => setProfessional(e.target.value ? Number(e.target.value) : null)}><option value="">Elegí un profesional</option>{professionals.map(p => <option key={p.id} value={p.id}>{p.nombre}{p.apellido ? ` ${p.apellido}` : ''}{p.activo === false ? ' (inactivo)' : ''}</option>)}</select></label>}<label>Fecha<input type="date" value={date} onChange={e => setDate(e.target.value)} /></label></div>
    {error && <><Notice kind="error">{error}</Notice><Button variant="secondary" onClick={() => initialized ? setRetry(n => n + 1) : setInitRetry(n => n + 1)}>Intentar de nuevo</Button></>}
    {initialized && role === 'profesional' && !professional && <Notice>No tenés una agenda vinculada. Comunicate con el consultorio.</Notice>}
    {initialized && professional && date && !turnos && !error && <Notice>Cargando agenda…</Notice>}
    {turnos && <section className="staff-schedule-panel" aria-label="Turnos del día"><h2>Turnos del día</h2>{turnos.length === 0 ? <p>No hay turnos para esta fecha.</p> : <ul className="staff-schedule">{turnos.map(t => <li key={t.id} className={t.es_sobreturno ? 'staff-appointment staff-appointment--over' : 'staff-appointment'}><span>{formatClinicTime(t.inicio, zone)} · {t.paciente_nombre} {t.paciente_apellido} · {t.estado}{t.es_sobreturno && ' · Sobreturno'}</span><Button variant="secondary" aria-label={`Ver turno de ${t.paciente_nombre} ${t.paciente_apellido}`} onClick={() => setView(t.id)}>Ver turno</Button></li>)}</ul>}</section>}
  </PageTemplate>;
}
