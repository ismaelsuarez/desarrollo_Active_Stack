import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useSession } from '../auth/provider';
import { ApiError } from '../api/client';
type Profesional = { id: number; nombre: string; apellido: string; activo: boolean };
type Bloqueo = { id: number; profesional_id: number | null; tipo: string; inicio: string; fin: string; motivo: string | null };
export function Bloqueos() {
  const { session } = useSession();
  const [profesionales, setProfesionales] = useState<Profesional[]>([]); const [scope, setScope] = useState('');
  const [items, setItems] = useState<Bloqueo[] | null>(null); const [tipo, setTipo] = useState('bloqueo'); const [inicio, setInicio] = useState(''); const [fin, setFin] = useState(''); const [motivo, setMotivo] = useState('');
  const [affected, setAffected] = useState<number[] | null>(null); const [error, setError] = useState(''); const [message, setMessage] = useState(''); const [busy, setBusy] = useState(false);
  const generation = useRef(0); const sending = useRef(false);
  const path = scope ? `/profesionales/${scope}/bloqueos` : '/bloqueos';
  const load = useCallback(async () => { const current = ++generation.current; setItems(null); setError(''); try { const result = await session.request<Bloqueo[]>(path); if (generation.current === current) setItems(result); } catch { if (generation.current === current) setError('No pudimos cargar los bloqueos.'); } }, [session, path]);
  useEffect(() => { void session.request<Profesional[]>('/profesionales').then(setProfesionales).catch(() => setError('No pudimos cargar profesionales.')); }, [session]);
  useEffect(() => { setAffected(null); setMessage(''); void load(); return () => { generation.current++; }; }, [load]);
  async function save() {
    if (sending.current) return;
    if (!inicio || !fin || inicio >= fin) { setError('El inicio debe ser anterior al fin.'); return; }
    sending.current = true; setBusy(true); setError(''); setMessage(''); const current = generation.current;
    try { const result = await session.request<Bloqueo>(path, { method: 'POST', body: { tipo, inicio, fin, motivo: motivo.trim() || null } }); if (current === generation.current) { setItems(old => [...(old ?? []), result]); setAffected(null); setMessage('Bloqueo creado.'); setInicio(''); setFin(''); setMotivo(''); } }
    catch (e) { if (current === generation.current) { if (e instanceof ApiError && e.status === 409 && e.affectedAppointments) { setAffected(e.affectedAppointments); } else setError(e instanceof ApiError ? 'No se pudo crear el bloqueo. Revisá los datos.' : 'No pudimos confirmar el resultado. Consultá los bloqueos antes de volver a intentar.'); } }
    finally { sending.current = false; setBusy(false); }
  }
  async function remove(id: number) {
    if (sending.current) return;
    sending.current = true; setBusy(true); setError(''); setMessage(''); const current = generation.current;
    try { await session.request(`/bloqueos/${id}`, { method: 'DELETE' }); if (generation.current === current) { setItems(old => old?.filter(item => item.id !== id) ?? null); setMessage('Bloqueo eliminado.'); } }
    catch (e) { if (generation.current === current) setError(e instanceof ApiError ? 'No se pudo eliminar el bloqueo.' : 'No pudimos confirmar el resultado. Consultá los bloqueos antes de volver a intentar.'); }
    finally { sending.current = false; setBusy(false); }
  }
  const vigentes = items?.filter(item => new Date(item.fin).getTime() > Date.now());
  return <section><h2>Excepciones y bloqueos</h2><p>Un bloqueo impide ofrecer turnos en un período para el consultorio o un profesional.</p><h3>Bloqueos vigentes</h3><label>Alcance <select value={scope} onChange={e => setScope(e.target.value)}><option value="">Todo el consultorio</option>{profesionales.filter(p => p.activo).map(p => <option key={p.id} value={p.id}>{p.nombre} {p.apellido}</option>)}</select></label>
    {error && <div role="alert">{error} <button type="button" onClick={() => void load()}>Consultar bloqueos</button></div>}{message && <p role="status">{message}</p>}
    {!items && !error && <p role="status">Cargando bloqueos…</p>}{vigentes?.length === 0 && <p>No hay bloqueos registrados.</p>}{vigentes?.map(item => <div className="admin-bloqueo-row" key={item.id}><p>{item.tipo} · {item.inicio} a {item.fin} · {item.profesional_id === null ? 'Todo el consultorio' : 'Profesional'}{item.motivo ? ` · ${item.motivo}` : ''}</p><button type="button" disabled={busy} onClick={() => void remove(item.id)}>Eliminar bloqueo {item.id}</button></div>)}
    <h3>Nuevo bloqueo</h3><p>Elegí el período que no estará disponible. Si coincide con turnos, primero deberás resolverlos.</p><form onSubmit={e => { e.preventDefault(); void save(); }}><label>Tipo <select value={tipo} onChange={e => setTipo(e.target.value)}><option value="bloqueo">Bloqueo</option><option value="feriado">Feriado</option><option value="vacaciones">Vacaciones</option><option value="ausencia">Ausencia</option></select></label><label>Desde <input type="datetime-local" required value={inicio} onChange={e => setInicio(e.target.value)} /></label><label>Hasta <input type="datetime-local" required value={fin} onChange={e => setFin(e.target.value)} /></label><label>Motivo <input maxLength={500} value={motivo} onChange={e => setMotivo(e.target.value)} /></label>
      {affected && <div role="alert"><strong>No se creó el bloqueo: hay turnos afectados.</strong><p>Resolvé cada turno desde la agenda y volvé a intentar. Ningún turno se modifica automáticamente.</p><ul>{affected.map(id => <li key={id}><Link to={`/agenda?turno=${id}`} target="_blank" rel="noopener noreferrer">Turno #{id}</Link></li>)}</ul></div>}
      <button disabled={busy}>{affected ? 'Volver a intentar' : 'Crear bloqueo'}</button>
    </form>
  </section>;
}
