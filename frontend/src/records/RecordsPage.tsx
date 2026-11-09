import { useCallback, useEffect, useRef, useState } from 'react';
import { useSession } from '../auth/provider';
import { ApiError } from '../api/client';
import { useSearchParams } from 'react-router-dom';
import './records.css';

type Summary = { id: number; nombre: string; apellido: string; activo: boolean };
type RecordDetail = Summary & { dni: string; telefono: string; email: string; obra_social?: string | null; notas?: string | null; cuenta?: { email: string } | null };
type Page = { items: Summary[]; total: number; limit: number; offset: number };
type Appointment = { id: number; inicio: string; estado: string };

export function RecordsPage() {
  const { session, state } = useSession();
  const [searchParams] = useSearchParams();
  const fichaParam = searchParams.get('ficha');
  const [page, setPage] = useState<Page | null>(null);
  const [detail, setDetail] = useState<RecordDetail | null>(null);
  const [history, setHistory] = useState<Appointment[]>([]);
  const [historyOffset, setHistoryOffset] = useState(0); const [historyHasNext, setHistoryHasNext] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false); const [historyError, setHistoryError] = useState(false); const [retryOffset, setRetryOffset] = useState(0);
  const [error, setError] = useState('');
  const [message, setMessage] = useState(''); const [editing, setEditing] = useState(false); const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState<RecordDetail | null>(null);
  const [unlinking, setUnlinking] = useState(false); const [reason, setReason] = useState('');
  const [creating, setCreating] = useState(false); const [newRecord, setNewRecord] = useState({ nombre: '', apellido: '', dni: '', telefono: '', email: '' });
  const [apellido, setApellido] = useState(''); const [dni, setDni] = useState(''); const [phone, setPhone] = useState('');
  const [query, setQuery] = useState({ apellido: '', dni: '', telefono: '' }); const [offset, setOffset] = useState(0);
  const sending = useRef(false); const currentDetail = useRef(0); const currentSearch = useRef(0);
  const identity = `${state.profile?.id ?? ''}:${state.profile?.rol ?? ''}`;
  const currentIdentity = useRef(identity); currentIdentity.current = identity;
  const load = useCallback(async () => {
    const generation = ++currentSearch.current;
    const params = new URLSearchParams({ limit: '20', offset: String(offset) });
    for (const [key, value] of Object.entries(query)) if (value) params.set(key, value);
    try { const result = await session.request<Page>(`/pacientes?${params}`); if (currentSearch.current === generation) { setPage(result); setError(''); } }
    catch { if (currentSearch.current === generation) setError('No pudimos cargar las fichas.'); }
  }, [session, query, offset, state.profile?.id, state.profile?.rol]);
  useEffect(() => { setPage(null); void load(); return () => { currentSearch.current++; }; }, [load]);
  const open = useCallback(async (id: number) => {
    const generation = ++currentDetail.current; setDetail(null); setHistory([]); setHistoryOffset(0); setHistoryHasNext(false); setHistoryError(false); setHistoryLoading(false); setEditing(false); setUnlinking(false); setReason('');
    try { const [record, appointments] = await Promise.all([session.request<RecordDetail>(`/pacientes/${id}`), session.request<Appointment[]>(`/pacientes/${id}/turnos?limit=21&offset=0`).then(value => ({ value }), () => ({ value: null }))]); if (currentDetail.current === generation) { setDetail(record); setDraft(record); setHistory(appointments.value?.slice(0, 20) ?? []); setHistoryHasNext((appointments.value?.length ?? 0) > 20); setHistoryError(appointments.value === null); setRetryOffset(0); setError(''); } }
    catch { if (currentDetail.current === generation) setError('No pudimos cargar la ficha.'); }
  }, [session, state.profile?.id, state.profile?.rol]);
  async function loadHistory(nextOffset: number) {
    if (!detail || historyLoading) return;
    const generation = currentDetail.current; setHistoryLoading(true); setHistoryError(false); setRetryOffset(nextOffset);
    try { const appointments = await session.request<Appointment[]>(`/pacientes/${detail.id}/turnos?limit=21&offset=${nextOffset}`); if (currentDetail.current === generation) { setHistory(appointments.slice(0, 20)); setHistoryHasNext(appointments.length > 20); setHistoryOffset(nextOffset); } }
    catch { if (currentDetail.current === generation) setHistoryError(true); }
    finally { if (currentDetail.current === generation) setHistoryLoading(false); }
  }
  useEffect(() => {
    setDetail(null); setDraft(null); setHistory([]); setMessage(''); setError('');
    if (fichaParam && /^[1-9]\d*$/.test(fichaParam) && Number.isSafeInteger(Number(fichaParam))) void open(Number(fichaParam));
    return () => { currentDetail.current++; };
  }, [fichaParam, open]);
  async function save() {
    if (!draft || sending.current) return;
    sending.current = true; setBusy(true); setMessage(''); setError('');
    try { const { nombre, apellido, dni, telefono, email, obra_social, notas } = draft; await session.request(`/pacientes/${draft.id}`, { method: 'PATCH', body: { nombre, apellido, dni, telefono, email, obra_social: obra_social || null, notas: notas || null } }); if (identity !== currentIdentity.current) return; await open(draft.id); if (identity !== currentIdentity.current) return; setEditing(false); setMessage('Ficha actualizada.'); }
    catch { if (identity === currentIdentity.current) setError('No pudimos guardar. Actualizá la ficha antes de volver a intentar.'); }
    finally { sending.current = false; setBusy(false); }
  }
  async function recordAction(action: 'desvincular' | 'reactivar') {
    if (!detail || sending.current) return;
    if (action === 'desvincular' && !reason.trim()) { setError('Indicá un motivo.'); return; }
    sending.current = true; setBusy(true); setError(''); setMessage('');
    try { await session.request(`/pacientes/${detail.id}/${action}`, { method: 'POST', ...(action === 'desvincular' ? { body: { motivo: reason.trim() } } : {}) }); if (identity !== currentIdentity.current) return; await open(detail.id); if (identity !== currentIdentity.current) return; setUnlinking(false); setReason(''); setMessage(action === 'desvincular' ? 'Cuenta desvinculada.' : 'Ficha reactivada.'); }
    catch (e) { if (identity === currentIdentity.current) setError(e instanceof ApiError && e.status === 409 ? 'La ficha cambió. Actualizá antes de volver a intentar.' : 'No pudimos confirmar el resultado. Actualizá la ficha antes de intentar nuevamente.'); }
    finally { sending.current = false; setBusy(false); }
  }
  async function create() {
    if (sending.current) return; sending.current = true; setBusy(true); setError(''); setMessage('');
    try { const result = await session.request<{ id: number }>('/pacientes', { method: 'POST', body: newRecord }); if (identity !== currentIdentity.current) return; setCreating(false); setNewRecord({ nombre: '', apellido: '', dni: '', telefono: '', email: '' }); await load(); if (identity !== currentIdentity.current) return; await open(result.id); if (identity === currentIdentity.current) setMessage('Ficha creada.'); }
    catch (e) { if (identity === currentIdentity.current) setError(e instanceof ApiError && e.status === 409 ? 'La ficha ya existe o cambió. Buscala antes de intentar nuevamente.' : 'No pudimos confirmar la creación. Buscá la ficha antes de volver a intentar.'); }
    finally { sending.current = false; setBusy(false); }
  }
  return <main className="records-page"><h1>Pacientes</h1>{state.profile?.rol !== 'profesional' && <button onClick={() => setCreating(true)}>Nueva ficha</button>}{creating && <form onSubmit={e => { e.preventDefault(); void create(); }}>{(['nombre','apellido','dni','telefono','email'] as const).map(field => <label key={field}>{({nombre:'Nombre',apellido:'Apellido de ficha',dni:'DNI',telefono:'Teléfono',email:'Correo'})[field]} <input required value={newRecord[field]} onChange={e => setNewRecord({ ...newRecord, [field]: e.target.value })} /></label>)}<button disabled={busy}>Crear ficha</button><button type="button" onClick={() => setCreating(false)}>Cancelar creación</button></form>}<form onSubmit={e => { e.preventDefault(); setOffset(0); setQuery({ apellido: apellido.trim(), dni: dni.trim(), telefono: phone.trim() }); }}><label>Apellido <input value={apellido} onChange={e => setApellido(e.target.value)} /></label><label>DNI de búsqueda <input value={dni} onChange={e => setDni(e.target.value)} /></label><label>Teléfono de búsqueda <input value={phone} onChange={e => setPhone(e.target.value)} /></label><button>Buscar</button></form>{error && <p role="alert">{error}</p>}{!page && !error && <p role="status">Cargando fichas…</p>}{page?.items.length === 0 && <section aria-label="Resultados de pacientes" className="records-empty"><h2>Resultados</h2><p>No hay fichas para mostrar.</p></section>}{page?.items.map(p => <button key={p.id} onClick={() => void open(p.id)}>{p.nombre} {p.apellido}</button>)}
    {page && <nav aria-label="Páginas"><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>Anterior</button><button disabled={offset + 20 >= page.total} onClick={() => setOffset(offset + 20)}>Siguiente</button></nav>}
    {message && <p role="status">{message}</p>}{detail && <section><h2>{detail.nombre} {detail.apellido}</h2><p>DNI: {detail.dni} · Teléfono: {detail.telefono} · Correo: {detail.email}</p>{state.profile?.rol !== 'profesional' && <><p>{detail.cuenta ? detail.cuenta.email : 'Sin cuenta vinculada'}</p><button onClick={() => setEditing(true)}>Editar</button>{detail.cuenta && <button onClick={() => setUnlinking(true)}>Desvincular cuenta</button>}{!detail.activo && <button disabled={busy} onClick={() => void recordAction('reactivar')}>Reactivar ficha</button>}</>}{unlinking && <form onSubmit={e => { e.preventDefault(); void recordAction('desvincular'); }}><label>Motivo <input value={reason} onChange={e => setReason(e.target.value)} /></label><button disabled={busy}>Confirmar desvinculación</button><button type="button" onClick={() => setUnlinking(false)}>Cancelar</button></form>}{error && <button onClick={() => void open(detail.id)}>Actualizar ficha</button>}{editing && draft && <form onSubmit={e => { e.preventDefault(); void save(); }}>{(['nombre','apellido','dni','telefono','email','obra_social','notas'] as const).map(field => <label key={field}>{({nombre:'Nombre',apellido:'Apellido',dni:'DNI',telefono:'Teléfono',email:'Correo',obra_social:'Obra social',notas:'Notas'})[field]} <input value={draft[field] ?? ''} onChange={e => setDraft({ ...draft, [field]: e.target.value })} /></label>)}<button disabled={busy}>Guardar cambios</button><button type="button" onClick={() => setEditing(false)}>Cancelar edición</button></form>}<h3>Historial de turnos</h3>{history.map(a => <p key={a.id}>{a.inicio} · {a.estado}</p>)}<p>Se muestran hasta 20 turnos por página.</p>{historyLoading && <p role="status">Cargando historial…</p>}{historyError && <><p role="alert">No pudimos cargar esta página del historial.</p><button onClick={() => void loadHistory(retryOffset)}>Reintentar historial</button></>}<nav aria-label="Páginas del historial"><button disabled={historyLoading || historyOffset === 0} onClick={() => void loadHistory(historyOffset - 20)}>Anterior historial</button><span>Página {historyOffset / 20 + 1}</span><button disabled={historyLoading || !historyHasNext} onClick={() => void loadHistory(historyOffset + 20)}>Siguiente historial</button></nav></section>}
  </main>;
}
