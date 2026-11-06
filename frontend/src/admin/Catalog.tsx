import { useCallback, useEffect, useRef, useState } from 'react';
import type { ClipboardEvent, KeyboardEvent } from 'react';
import { useSession } from '../auth/provider';
import { ApiError } from '../api/client';

type Prestacion = { id: number; nombre: string; duracion_min: number; activa: boolean; sugerida: boolean };
type Config = { modo_liberacion: 'manual' | 'automatico'; horas_confirmacion: number; horas_recordatorio: number; horas_liberacion: number; horas_limite_paciente: number; telefono: string | null; minutos_granularidad: number; dias_anticipacion_maxima: number; max_turnos_activos_paciente: number };
const uncertain = 'No pudimos confirmar el resultado. Actualizá los datos antes de intentar nuevamente.';
const onlyDigits = (value: string) => /^\d*$/.test(value);
const integerKey = (event: KeyboardEvent<HTMLInputElement>) => {
  if (!event.ctrlKey && !event.metaKey && !event.altKey && (event.key === 'e' || event.key === 'E')) event.preventDefault();
};
const integerPaste = (event: ClipboardEvent<HTMLInputElement>) => {
  if (!onlyDigits(event.clipboardData.getData('text'))) event.preventDefault();
};

export function Prestaciones() {
  const { session } = useSession();
  const [items, setItems] = useState<Prestacion[] | null>(null);
  const [nombre, setNombre] = useState('');
  const [duracion, setDuracion] = useState('');
  const [editing, setEditing] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [invalid, setInvalid] = useState<string[]>([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const sending = useRef(false);
  const load = useCallback(async () => { try { setItems(await session.request<Prestacion[]>('/prestaciones')); setError(''); } catch { setError('No pudimos cargar las prestaciones.'); } }, [session]);
  useEffect(() => { void load(); }, [load]);
  async function save() {
    if (sending.current) return;
    const minutes = Number(duracion);
    if (!Number.isInteger(minutes) || minutes < 1) { setInvalid(['duracion_min']); setError('La duración debe ser un número entero mayor a cero.'); return; }
    sending.current = true; setBusy(true); setError(''); setInvalid([]); setMessage('');
    try {
      const saved = await session.request<Prestacion>(editing === null ? '/prestaciones' : `/prestaciones/${editing}`, { method: editing === null ? 'POST' : 'PATCH', body: { nombre, duracion_min: minutes } });
      setItems(current => [...(current ?? []).filter(item => item.id !== saved.id), saved]);
      setNombre(''); setDuracion(''); setEditing(null); setMessage('Prestación guardada.');
    } catch (e) { if (e instanceof ApiError) setInvalid(e.invalidFields); setError(e instanceof ApiError ? e.status === 409 ? 'Ya existe una prestación con ese nombre.' : e.status === 422 ? 'Revisá los datos ingresados.' : 'No se pudo guardar la prestación.' : uncertain); }
    finally { sending.current = false; setBusy(false); }
  }
  async function deactivate(id: number) {
    if (sending.current) return;
    sending.current = true; setBusy(true); setError(''); setMessage('');
    try { await session.request(`/prestaciones/${id}`, { method: 'DELETE' }); setItems(current => current?.map(item => item.id === id ? { ...item, activa: false } : item) ?? null); setMessage('Prestación desactivada.'); }
    catch (e) { setError(e instanceof ApiError ? 'No se pudo desactivar la prestación.' : uncertain); }
    finally { sending.current = false; setBusy(false); }
  }
  return <section><h2>Prestaciones</h2>
    {error && <div role="alert">{error} <button type="button" onClick={() => void load()}>Actualizar prestaciones</button></div>}
    {message && <p role="status">{message}</p>}
    {!items && !error && <p role="status">Cargando prestaciones…</p>}
    {items?.length === 0 && <p>No hay prestaciones registradas.</p>}
    {items?.map(item => <div key={item.id}><p>{item.nombre} · {item.duracion_min} minutos · {item.activa ? 'Activa' : 'Inactiva'}</p><button type="button" onClick={() => { setEditing(item.id); setNombre(item.nombre); setDuracion(String(item.duracion_min)); }}>Editar {item.nombre}</button>{item.activa && <button type="button" disabled={busy} onClick={() => void deactivate(item.id)}>Desactivar {item.nombre}</button>}</div>)}
    <form onSubmit={e => { e.preventDefault(); void save(); }} noValidate>
      <label>Nombre de prestación <input required maxLength={160} aria-invalid={invalid.includes('nombre')} value={nombre} onChange={e => setNombre(e.target.value)} /></label>{invalid.includes('nombre') && <p>Revisá el nombre.</p>}
      <label>Duración en minutos <input required type="number" min={1} step={1} onKeyDown={integerKey} onPaste={integerPaste} aria-invalid={invalid.includes('duracion_min')} value={duracion} onChange={e => { if (onlyDigits(e.target.value)) setDuracion(e.target.value); }} /></label>{invalid.includes('duracion_min') && <p>Revisá la duración.</p>}
      <button disabled={busy}>{editing === null ? 'Crear prestación' : 'Guardar prestación'}</button>
      {editing !== null && <button type="button" onClick={() => { setEditing(null); setNombre(''); setDuracion(''); }}>Cancelar edición</button>}
    </form>
  </section>;
}

const fields = [
  ['horas_confirmacion', 'Confirmación en horas', 1, undefined], ['horas_recordatorio', 'Recordatorio en horas', 1, undefined],
  ['horas_liberacion', 'Liberación en horas', 1, undefined], ['horas_limite_paciente', 'Límite del paciente en horas', 1, undefined],
  ['minutos_granularidad', 'Granularidad en minutos', 5, 120], ['dias_anticipacion_maxima', 'Anticipación máxima en días', 1, undefined],
  ['max_turnos_activos_paciente', 'Máximo de turnos activos', 1, undefined],
] as const;

export function Parametros() {
  const { session } = useSession();
  const [draft, setDraft] = useState<Config | null>(null);
  const [error, setError] = useState(''); const [message, setMessage] = useState(''); const [invalid, setInvalid] = useState<string[]>([]); const [busy, setBusy] = useState(false); const sending = useRef(false);
  const load = useCallback(async () => { try { setDraft(await session.request<Config>('/consultorio')); setError(''); } catch { setError('No pudimos cargar los parámetros.'); } }, [session]);
  useEffect(() => { void load(); }, [load]);
  async function save() {
    if (!draft || sending.current) return;
    setError(''); setInvalid([]); setMessage('');
    const bad = fields.filter(([key, , min, max]) => !Number.isInteger(draft[key]) || draft[key] < min || (max !== undefined && draft[key] > max)).map(([key]) => key);
    if (bad.length) { setInvalid(bad); setError('Revisá los límites indicados en los campos.'); return; }
    if (!(draft.horas_confirmacion > draft.horas_recordatorio && draft.horas_recordatorio > draft.horas_liberacion)) { setInvalid(['horas_confirmacion', 'horas_recordatorio', 'horas_liberacion']); setError('Los plazos deben cumplir confirmación > recordatorio > liberación.'); return; }
    sending.current = true; setBusy(true);
    try { setDraft(await session.request<Config>('/consultorio', { method: 'PATCH', body: draft })); setMessage('Parámetros guardados.'); }
    catch (e) { if (e instanceof ApiError) setInvalid(e.invalidFields); setError(e instanceof ApiError ? e.status === 422 ? 'Revisá los parámetros ingresados.' : 'No se pudieron guardar los parámetros.' : uncertain); }
    finally { sending.current = false; setBusy(false); }
  }
  return <section><h2>Parámetros del consultorio</h2>
    {error && <div role="alert">{error} <button type="button" onClick={() => void load()}>Actualizar parámetros</button></div>}
    {message && <p role="status">{message}</p>}
    {!draft && !error && <p role="status">Cargando parámetros…</p>}
    {draft && <form onSubmit={e => { e.preventDefault(); void save(); }} noValidate>
      <label>Modo de liberación <select value={draft.modo_liberacion} onChange={e => setDraft({ ...draft, modo_liberacion: e.target.value as Config['modo_liberacion'] })}><option value="manual">Manual</option><option value="automatico">Automático</option></select></label>
      <label>Teléfono del consultorio <input maxLength={40} aria-invalid={invalid.includes('telefono')} value={draft.telefono ?? ''} onChange={e => setDraft({ ...draft, telefono: e.target.value || null })} /></label>{invalid.includes('telefono') && <p>Revisá el teléfono.</p>}
      {fields.map(([key, label, min, max]) => <div key={key}><label>{label} <input type="number" min={min} max={max} step={1} onKeyDown={integerKey} onPaste={integerPaste} aria-invalid={invalid.includes(key)} value={draft[key]} onChange={e => { if (onlyDigits(e.target.value)) setDraft({ ...draft, [key]: Number(e.target.value) }); }} /></label>{invalid.includes(key) && <p>Revisá {label.toLowerCase()}.</p>}</div>)}
      <button disabled={busy}>Guardar parámetros</button>
    </form>}
  </section>;
}
