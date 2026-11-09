import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../api/client';
import { useSession } from '../auth/provider';
import './records.css';

type Patient = { id: number; nombre: string; apellido: string };
type LinkRequest = { id: number; estado: string; email: string; email_verificado: boolean; dni_declarado: string; ficha_existente?: Patient | null; ficha_vinculada?: Patient | null };
type Page = { items: LinkRequest[]; total: number; offset: number; limit: number };

export function LinkingPage() {
  const { session, state } = useSession();
  const [items, setItems] = useState<Page | null>(null); const [patients, setPatients] = useState<Patient[]>([]);
  const [filter, setFilter] = useState(''); const [offset, setOffset] = useState(0); const [selected, setSelected] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [message, setMessage] = useState('');
  const [patientSearch, setPatientSearch] = useState('');
  const [patientQuery, setPatientQuery] = useState(''); const [patientOffset, setPatientOffset] = useState(0); const [patientTotal, setPatientTotal] = useState(0);
  const [reasons, setReasons] = useState<Record<number, string>>({});
  const sending = useRef(false); const currentList = useRef(0); const currentPatients = useRef(0);
  const identity = `${state.profile?.id ?? ''}:${state.profile?.rol ?? ''}`;
  const currentIdentity = useRef(identity); currentIdentity.current = identity;
  const load = useCallback(async () => {
    const listGeneration = ++currentList.current; const patientsGeneration = ++currentPatients.current;
    const params = new URLSearchParams({ limit: '20', offset: String(offset) }); if (filter) params.set('estado', filter);
    try { const [requests, records] = await Promise.all([session.request<Page>(`/solicitudes-vinculacion?${params}`), session.request<{ items: Patient[]; total: number }>('/pacientes?limit=100&offset=0')]); if (currentList.current === listGeneration) { setItems(requests); setError(''); } if (currentPatients.current === patientsGeneration) { setPatients(records.items); setPatientOffset(0); setPatientTotal(records.total); setPatientQuery(''); } }
    catch { if (currentList.current === listGeneration) setError('No pudimos cargar las solicitudes.'); }
  }, [session, filter, offset, state.profile?.id, state.profile?.rol]);
  useEffect(() => { setItems(null); setPatients([]); setSelected({}); setReasons({}); setMessage(''); void load(); return () => { currentList.current++; currentPatients.current++; }; }, [load]);
  async function searchPatients(query = patientSearch.trim(), nextOffset = 0) {
    const generation = ++currentPatients.current;
    const params = new URLSearchParams({ limit: '100', offset: String(nextOffset) }); if (query) params.set('apellido', query);
    try { const result = await session.request<{ items: Patient[]; total: number }>(`/pacientes?${params}`); if (currentPatients.current === generation) { setPatients(result.items); setPatientTotal(result.total); setPatientOffset(nextOffset); setPatientQuery(query); setSelected({}); } }
    catch { if (currentPatients.current === generation) setError('No pudimos buscar las fichas.'); }
  }
  async function resolve(item: LinkRequest, action: 'vincular' | 'rechazar') {
    if (sending.current || (action === 'vincular' && (!item.email_verificado || !selected[item.id]))) return;
    sending.current = true; setBusy(true); setError(''); setMessage('');
    try { await session.request(`/solicitudes-vinculacion/${item.id}/${action}`, { method: 'POST', body: action === 'vincular' ? { paciente_id: Number(selected[item.id]) } : reasons[item.id]?.trim() ? { motivo: reasons[item.id].trim() } : {} }); if (identity !== currentIdentity.current) return; await load(); if (identity === currentIdentity.current) setMessage('Solicitud actualizada.'); }
    catch (e) { if (identity === currentIdentity.current) setError(e instanceof ApiError && e.status === 409 ? 'La solicitud o ficha cambió. Actualizá antes de volver a intentar.' : 'No pudimos confirmar el resultado. Actualizá antes de intentar nuevamente.'); }
    finally { sending.current = false; setBusy(false); }
  }
  return <main className="records-page"><h1>Solicitudes de vinculación</h1><p>Revisá las solicitudes y vinculá cuentas con sus fichas.</p><section aria-label="Filtros y búsqueda" className="records-filters"><h2>Filtros y búsqueda</h2><div className="records-filter-actions"><label>Estado <select value={filter} onChange={e => { setFilter(e.target.value); setOffset(0); }}><option value="">Todas</option><option value="pendiente">Pendientes</option><option value="vinculada">Vinculadas</option><option value="rechazada">Rechazadas</option></select></label><button onClick={() => void load()}>Actualizar solicitudes</button></div>
    {error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}<form onSubmit={e => { e.preventDefault(); void searchPatients(); }}><label>Buscar ficha por apellido <input value={patientSearch} onChange={e => setPatientSearch(e.target.value)} /></label><button>Buscar ficha</button><button type="button" disabled={patientOffset === 0} onClick={() => void searchPatients(patientQuery, Math.max(0, patientOffset - 100))}>Fichas anteriores</button><button type="button" disabled={patientOffset + 100 >= patientTotal} onClick={() => void searchPatients(patientQuery, patientOffset + 100)}>Más fichas</button></form></section>
    {items?.items.length === 0 && <section aria-label="Resultados de solicitudes" className="records-empty"><h2>Solicitudes</h2><p>No hay solicitudes para mostrar.</p></section>}{items?.items.map(item => <article key={item.id}><h2>Solicitud {item.id}</h2><p>{item.email} · DNI {item.dni_declarado} · {item.estado}</p>{!item.email_verificado && <p>Correo no verificado</p>}{item.ficha_existente && <p>Ficha coincidente: {item.ficha_existente.nombre} {item.ficha_existente.apellido}</p>}{item.ficha_vinculada && <p>Ficha vinculada: {item.ficha_vinculada.nombre} {item.ficha_vinculada.apellido}</p>}
      {item.estado !== 'vinculada' && <><label>Ficha para solicitud {item.id} <select value={selected[item.id] ?? ''} onChange={e => setSelected({ ...selected, [item.id]: e.target.value })}><option value="">Elegí una ficha</option>{patients.map(p => <option key={p.id} value={p.id}>{p.nombre} {p.apellido} (#{p.id})</option>)}</select></label><button disabled={busy || !item.email_verificado || !selected[item.id]} onClick={() => void resolve(item, 'vincular')}>Vincular</button>{item.estado === 'pendiente' && <><label>Motivo de rechazo {item.id}<input value={reasons[item.id] ?? ''} onChange={e => setReasons({ ...reasons, [item.id]: e.target.value })} /></label><button disabled={busy} onClick={() => void resolve(item, 'rechazar')}>Rechazar</button></>}</>}
    </article>)}{items && <nav aria-label="Páginas"><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>Anterior</button><button disabled={offset + 20 >= items.total} onClick={() => setOffset(offset + 20)}>Siguiente</button></nav>}</main>;
}
