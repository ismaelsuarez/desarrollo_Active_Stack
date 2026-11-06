import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, request } from '../api/client';
import { useSession } from '../auth/provider';
import { Button, Notice, PageTemplate, TextField } from '../components/ui';
import { formatClinicDate, formatClinicTime } from './time';
import '../pages/public.css';

type Appointment = { id: number; profesional_id: number; prestacion_id: number; prestacion_nombre: string; inicio: string; fin: string; estado: string; acciones_permitidas: string[] };
type Clinic = { telefono: string | null; zona_horaria: string };
type Professional = { id: number; nombre: string };
type Slot = { inicio: string; fin: string };

export function AppointmentsPage() {
  const { session } = useSession();
  const [appointments, setAppointments] = useState<Appointment[] | null>(null);
  const [clinic, setClinic] = useState<Clinic | null>(null); const [professionals, setProfessionals] = useState<Professional[]>([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState(''); const [busy, setBusy] = useState(false); const sending = useRef(false);
  const [cancelId, setCancelId] = useState<number | null>(null);
  const [moving, setMoving] = useState<Appointment | null>(null); const [date, setDate] = useState('');
  const [slots, setSlots] = useState<Slot[] | null>(null); const [selected, setSelected] = useState<Slot | null>(null); const generation = useRef(0);
  const load = useCallback(async () => {
    try {
      const [items, c, p] = await Promise.all([session.request<Appointment[]>('/turnos'), request<Clinic>('/publico/consultorio'), request<Professional[]>('/publico/profesionales')]);
      setAppointments(items); setClinic(c); setProfessionals(p); setError('');
    } catch { setError('No pudimos cargar tus turnos. Intentá nuevamente.'); }
  }, [session]);
  useEffect(() => { void load(); }, [load]);
  async function perform(id: number, action: 'confirmar' | 'cancelar') {
    if (sending.current) return;
    sending.current = true; setBusy(true); setError(''); setMessage('');
    try { await session.request(`/turnos/${id}/${action}`, { method: 'POST' }); setCancelId(null); await load(); setMessage(action === 'confirmar' ? 'Turno confirmado.' : 'Turno cancelado.'); }
    catch (e) {
      await load();
      if (e instanceof ApiError && e.bookingDetail?.kind === 'deadline') setError(`El plazo terminó. Comunicate con el consultorio${clinic?.telefono ? `: ${clinic.telefono}` : '.'}`);
      else if (e instanceof ApiError) setError('No pudimos completar la acción. Revisá el estado de tu turno.');
      else setError('No pudimos confirmar el resultado. Revisá tus turnos antes de intentar nuevamente.');
    }
    finally { sending.current = false; setBusy(false); }
  }
  async function searchSlots() {
    if (!moving || !date) return;
    const current = ++generation.current; setSlots(null); setSelected(null); setError('');
    const query = new URLSearchParams({ profesional_id: String(moving.profesional_id), prestacion_id: String(moving.prestacion_id), fecha: date });
    try { const found = await request<Slot[]>(`/publico/disponibilidad?${query}`); if (generation.current === current) setSlots(found); }
    catch { if (generation.current === current) setError('No pudimos cargar los horarios.'); }
  }
  async function reschedule() {
    if (!moving || !selected || sending.current) return;
    sending.current = true; setBusy(true); setError(''); setMessage('');
    try { await session.request(`/turnos/${moving.id}`, { method: 'PATCH', body: { inicio: selected.inicio } }); setMoving(null); await load(); setMessage('Tu turno fue reprogramado.'); }
    catch (e) {
      await load();
      if (e instanceof ApiError && e.bookingDetail?.kind === 'occupied') {
        setSlots(e.bookingDetail.alternatives); setSelected(null); setError('Ese horario ya no está disponible. Tu turno anterior no cambió.');
      } else if (e instanceof ApiError) setError('No pudimos cambiar el turno. Revisá el horario o comunicate con el consultorio.');
      else setError('No pudimos confirmar el cambio. Revisá tus turnos antes de intentar nuevamente.');
    }
    finally { sending.current = false; setBusy(false); }
  }
  return <PageTemplate title="Mis turnos" description="Consultá tus turnos y su estado.">
    <p><Link to="/paciente">Volver a mi cuenta</Link> · <Link to="/reservar">Reservar otro turno</Link></p>
    {error && <Notice kind="error">{error}</Notice>}
    {message && <Notice kind="success">{message}</Notice>}
    {!appointments && !error && <Notice>Cargando tus turnos…</Notice>}
    {appointments?.length === 0 && <p>No tenés turnos para mostrar.</p>}
    {appointments?.map(item => <article className="public-card" key={item.id}>
      <h2>{item.prestacion_nombre}</h2><p>{formatClinicDate(item.inicio, clinic?.zona_horaria ?? 'UTC')} · {formatClinicTime(item.inicio, clinic?.zona_horaria ?? 'UTC')}</p>
      <p>{professionals.find(p => p.id === item.profesional_id)?.nombre ?? 'Profesional no disponible'}</p><p>Estado: {item.estado}</p>
      <div>{item.acciones_permitidas.includes('confirmar') && <Button disabled={busy} onClick={() => void perform(item.id, 'confirmar')}>Confirmar turno</Button>} {item.acciones_permitidas.includes('cancelar') && <Button disabled={busy} variant="secondary" onClick={() => setCancelId(item.id)}>Cancelar turno</Button>} {item.acciones_permitidas.includes('reprogramar') && <Button variant="secondary" disabled={busy} onClick={() => { generation.current++; setMoving(item); setDate(''); setSlots(null); setSelected(null); }}>Reprogramar</Button>}</div>
      {cancelId === item.id && <section aria-label="Confirmar cancelación"><h3>¿Querés cancelar este turno?</h3><p>Esta acción libera el horario.</p><Button disabled={busy} onClick={() => void perform(item.id, 'cancelar')}>Sí, cancelar turno</Button> <Button variant="secondary" disabled={busy} onClick={() => setCancelId(null)}>Volver</Button></section>}
      {['pendiente', 'confirmado'].includes(item.estado) && !item.acciones_permitidas.includes('cancelar') && !item.acciones_permitidas.includes('reprogramar') && <p>Para modificar este turno, comunicate con el consultorio{clinic?.telefono ? `: ${clinic.telefono}` : '.'}</p>}
      {item.estado === 'liberado' && <p>Este turno no puede confirmarse. <Link to="/reservar">Reservar de nuevo</Link></p>}
    </article>)}
    {moving && <section className="public-card"><h2>Elegí otro horario</h2><p>Tu turno actual sigue reservado hasta confirmar el cambio.</p><Notice kind="warning">Los horarios orientativos se verifican al confirmar; la duración de tu turno puede ser diferente.</Notice><TextField label="Nueva fecha" type="date" disabled={busy} value={date} onChange={e => { generation.current++; setDate(e.target.value); setSlots(null); setSelected(null); }} /><Button variant="secondary" disabled={!date || busy} onClick={() => void searchSlots()}>Buscar horarios</Button>{slots && (slots.length ? <div>{slots.map(slot => <Button variant="secondary" disabled={busy} key={slot.inicio} aria-pressed={selected?.inicio === slot.inicio} onClick={() => setSelected(slot)}>{formatClinicDate(slot.inicio, clinic?.zona_horaria ?? 'UTC')} · {formatClinicTime(slot.inicio, clinic?.zona_horaria ?? 'UTC')}</Button>)}</div> : <p>No encontramos horarios para esta fecha.</p>)}{selected && <><p>{formatClinicDate(selected.inicio, clinic?.zona_horaria ?? 'UTC')} · {formatClinicTime(selected.inicio, clinic?.zona_horaria ?? 'UTC')}</p><Button disabled={busy} onClick={() => void reschedule()}>Confirmar nuevo horario</Button></>}</section>}
  </PageTemplate>;
}
