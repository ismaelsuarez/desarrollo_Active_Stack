import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, request } from '../api/client';
import { useSession } from '../auth/provider';
import { Button, Notice, PageTemplate, TextField } from '../components/ui';
import { formatClinicDate, formatClinicTime } from './time';
import '../pages/public.css';
import './booking.css';

type Clinic = { nombre: string; telefono: string | null; direccion?: string | null; zona_horaria: string };
type Service = { id: number; nombre: string; duracion_min: number };
type Professional = { id: number; nombre: string };
type Slot = { inicio: string; fin: string };
const draft = { service: '', professional: '', date: '' };

export function BookingPage() {
  const { state, session } = useSession();
  const [clinic, setClinic] = useState<Clinic | null>(null);
  const [services, setServices] = useState<Service[]>([]);
  const [professionals, setProfessionals] = useState<Professional[]>([]);
  const [service, setService] = useState(draft.service); const [professional, setProfessional] = useState(draft.professional); const [date, setDate] = useState(draft.date);
  const [slots, setSlots] = useState<Slot[] | null>(null); const [error, setError] = useState(''); const [waiting, setWaiting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Slot | null>(null);
  const [alternatives, setAlternatives] = useState(false);
  const [booked, setBooked] = useState(''); const [busy, setBusy] = useState(false); const sending = useRef(false);
  const generation = useRef(0);
  useEffect(() => {
    let active = true;
    const options = { onWait: () => { if (active) setWaiting(true); } };
    Promise.all([request<Clinic>('/publico/consultorio', options), request<Service[]>('/publico/prestaciones', options), request<Professional[]>('/publico/profesionales', options)])
      .then(([c, s, p]) => { if (active) { setClinic(c); setServices(s); setProfessionals(p); setWaiting(false); setLoading(false); } })
      .catch((e: unknown) => { if (active) { setWaiting(false); setLoading(false); setError(e instanceof ApiError && e.status === 429 ? 'Demasiadas consultas. Intentá más tarde.' : 'No pudimos cargar los datos del consultorio.'); } });
    return () => { active = false; };
  }, []);
  function changed() { generation.current++; setSlots(null); setSelected(null); setError(''); setWaiting(false); }
  async function search() {
    const current = ++generation.current; setSlots(null); setSelected(null); setAlternatives(false); setBooked(''); setError('');
    const params = new URLSearchParams({ profesional_id: professional, prestacion_id: service, fecha: date });
    try {
      const result = await request<Slot[]>(`/publico/disponibilidad?${params}`, { onWait: () => { if (current === generation.current) setWaiting(true); } });
      if (current === generation.current) setSlots(result);
    } catch (e) { if (current === generation.current) setError(e instanceof ApiError && e.status === 429 ? 'Demasiadas consultas. Intentá más tarde.' : 'No pudimos cargar los horarios. Intentá nuevamente.'); }
    finally { if (current === generation.current) setWaiting(false); }
  }
  async function reserve() {
    if (!selected || sending.current) return;
    sending.current = true; setBusy(true); setError('');
    try {
      const result = await session.request<{ estado: string }>('/turnos', { method: 'POST', body: { profesional_id: Number(professional), prestacion_id: Number(service), inicio: selected.inicio } });
      setBooked(result.estado); setSlots(null); setSelected(null);
    } catch (e) {
      if (e instanceof ApiError && e.bookingDetail?.kind === 'occupied') {
        setError('Ese horario ya no está disponible. Elegí otra opción.'); setSlots(e.bookingDetail.alternatives); setAlternatives(true); setSelected(null);
      } else if (e instanceof ApiError && e.bookingDetail?.kind === 'limit') setError(`Alcanzaste el máximo de ${e.bookingDetail.maximum} turnos activos.`);
      else setError(e instanceof ApiError ? 'No pudimos completar la reserva. Revisá tu cuenta o comunicate con el consultorio.' : 'No pudimos confirmar el resultado. Revisá tus turnos antes de intentar nuevamente.');
    }
    finally { sending.current = false; setBusy(false); }
  }
  return <PageTemplate title="Reservá tu turno" description="Elegí una prestación, un profesional y el horario que mejor te quede.">
    {clinic && <p>{clinic.nombre}{clinic.direccion ? ` · ${clinic.direccion}` : ''}{clinic.telefono ? ` · ${clinic.telefono}` : ''}</p>}
    {loading && !waiting && <Notice>Cargando datos del consultorio…</Notice>}
    {waiting && <Notice kind="warning">El servicio está iniciando. Estamos intentando cargar los datos.</Notice>}
    {error && <Notice kind="error">{error}</Notice>}
    <div className="booking-grid"><div className="public-card booking-card"><h2>Elegí qué necesitás</h2><div className="public-form booking-form">
      <label>Prestación<select disabled={busy} value={service} onChange={e => { changed(); draft.service = e.target.value; setService(e.target.value); }}><option value="">Elegí una prestación</option>{services.map(s => <option key={s.id} value={s.id}>{s.nombre} · {s.duracion_min} min</option>)}</select></label>
      <label>Profesional<select disabled={busy} value={professional} onChange={e => { changed(); draft.professional = e.target.value; setProfessional(e.target.value); }}><option value="">Elegí un profesional</option>{professionals.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}</select></label>
      <TextField label="Fecha" type="date" disabled={busy} value={date} onChange={e => { changed(); draft.date = e.target.value; setDate(e.target.value); }} />
      <Button variant="secondary" disabled={busy || !service || !professional || !date} onClick={() => void search()}>Buscar horarios</Button>
    </div></div>
    {slots && <div className="public-card booking-card"><h2>Elegí un horario</h2><p>Hora del consultorio</p>{slots.length ? <div className="booking-slots">{slots.map(slot => <Button disabled={busy} variant="secondary" key={slot.inicio} aria-pressed={selected?.inicio === slot.inicio} onClick={() => setSelected(slot)}>{alternatives && <>{formatClinicDate(slot.inicio, clinic?.zona_horaria ?? 'UTC')} · </>}{formatClinicTime(slot.inicio, clinic?.zona_horaria ?? 'UTC')}</Button>)}</div> : <p>{alternatives ? 'No encontramos alternativas disponibles.' : 'No encontramos horarios para esta fecha.'}</p>}</div>}</div>
    {selected && !state.profile && <div className="public-card"><h2>Ingresá para reservar</h2><p>Necesitás una cuenta con correo verificado. Después de ingresar, volvé a elegir el horario antes de confirmar.</p><p><Link to="/ingresar">Ingresar</Link> · <Link to="/registro">Crear cuenta</Link></p></div>}
    {booked && <Notice kind="success">Tu turno está reservado. Estado: {booked}. <Link to="/mis-turnos">Ver mis turnos</Link></Notice>}
    {selected && state.profile?.rol === 'paciente' && <div className="public-card"><h2>Revisá tu reserva</h2><p>{services.find(s => String(s.id) === service)?.nombre} · {professionals.find(p => String(p.id) === professional)?.nombre}</p><p>{formatClinicDate(selected.inicio, clinic?.zona_horaria ?? 'UTC')} · {formatClinicTime(selected.inicio, clinic?.zona_horaria ?? 'UTC')}</p><Button disabled={busy || !state.profile.email_verificado} onClick={() => void reserve()}>Confirmar reserva</Button>{!state.profile.email_verificado && <p>Verificá tu correo antes de reservar. <Link to="/reenviar-verificacion">Reenviar enlace</Link></p>}</div>}
  </PageTemplate>;
}
