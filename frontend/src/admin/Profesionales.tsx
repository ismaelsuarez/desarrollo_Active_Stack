import { useCallback, useEffect, useRef, useState } from 'react';
import { useSession } from '../auth/provider';
import { ApiError } from '../api/client';

type Box = { id: number; nombre: string; activo: boolean };
type Cuenta = { id: number; nombre_usuario: string; rol: string; activo: boolean };
type Profesional = { id: number; usuario_id: number | null; box_id: number; nombre: string; apellido: string; activo: boolean };
const empty = { nombre: '', apellido: '', usuario_id: '', box_id: '' };

export function Profesionales() {
  const { session } = useSession();
  const [boxes, setBoxes] = useState<Box[] | null>(null);
  const [cuentas, setCuentas] = useState<Cuenta[]>([]);
  const [profesionales, setProfesionales] = useState<Profesional[] | null>(null);
  const [draft, setDraft] = useState(empty);
  const [box, setBox] = useState('');
  const [editing, setEditing] = useState<number | null>(null);
  const [error, setError] = useState(''); const [message, setMessage] = useState(''); const [busy, setBusy] = useState(false);
  const sending = useRef(false);
  const load = useCallback(async () => {
    try {
      const [b, c, p] = await Promise.all([session.request<Box[]>('/boxes'), session.request<Cuenta[]>('/usuarios'), session.request<Profesional[]>('/profesionales')]);
      setBoxes(b); setCuentas(c); setProfesionales(p); setError('');
    } catch { setError('No pudimos cargar profesionales y boxes.'); }
  }, [session]);
  useEffect(() => { void load(); }, [load]);
  async function write(path: string, method: 'POST' | 'PATCH', body: object, success: (value: unknown) => void) {
    if (sending.current) return;
    sending.current = true; setBusy(true); setMessage(''); setError('');
    try { const result = await session.request(path, { method, body }); success(result); setMessage('Cambios guardados.'); }
    catch (e) { setError(e instanceof ApiError ? e.status === 409 ? 'La cuenta o el box ya están asociados a un profesional.' : e.status === 422 ? 'La cuenta debe ser profesional o administrador; revisá los datos.' : 'No se pudieron guardar los cambios.' : 'No pudimos confirmar el resultado. Actualizá la lista antes de volver a intentar.'); }
    finally { sending.current = false; setBusy(false); }
  }
  function save() {
    const payload = { nombre: draft.nombre, apellido: draft.apellido, box_id: Number(draft.box_id) };
    void write(editing === null ? '/profesionales' : `/profesionales/${editing}`, editing === null ? 'POST' : 'PATCH', editing === null ? { ...payload, usuario_id: Number(draft.usuario_id) } : payload, result => {
      const saved = result as Profesional; setProfesionales(current => [...(current ?? []).filter(p => p.id !== saved.id), saved]); setDraft(empty); setEditing(null);
    });
  }
  function active(item: Profesional) {
    void write(`/profesionales/${item.id}`, 'PATCH', { activo: !item.activo }, result => {
      const saved = result as Profesional; setProfesionales(current => current?.map(p => p.id === saved.id ? saved : p) ?? null);
    });
  }
  return <section><h2>Profesionales y boxes</h2>
    {error && <div role="alert">{error} <button type="button" onClick={() => void load()}>Actualizar lista</button></div>}{message && <p role="status">{message}</p>}
    {!profesionales && !error && <p role="status">Cargando profesionales…</p>}
    {profesionales?.length === 0 && <p>No hay profesionales registrados.</p>}
    {profesionales?.map(p => <div key={p.id}><p>{p.nombre} {p.apellido} · {boxes?.find(b => b.id === p.box_id)?.nombre ?? `Box ${p.box_id}`} · {p.activo ? 'Activo' : 'Inactivo'}</p><button type="button" onClick={() => { setEditing(p.id); setDraft({ nombre: p.nombre, apellido: p.apellido, box_id: String(p.box_id), usuario_id: String(p.usuario_id ?? '') }); }}>Editar {p.nombre} {p.apellido}</button><button type="button" disabled={busy} onClick={() => active(p)}>{p.activo ? 'Desactivar' : 'Activar'} {p.nombre} {p.apellido}</button></div>)}
    <form onSubmit={e => { e.preventDefault(); save(); }}>
      <label>Nombre profesional <input required value={draft.nombre} onChange={e => setDraft({ ...draft, nombre: e.target.value })} /></label>
      <label>Apellido profesional <input required value={draft.apellido} onChange={e => setDraft({ ...draft, apellido: e.target.value })} /></label>
      {editing === null && <label>Cuenta <select required value={draft.usuario_id} onChange={e => setDraft({ ...draft, usuario_id: e.target.value })}><option value="">Elegí una cuenta</option>{cuentas.filter(c => c.activo && ['profesional', 'administrador'].includes(c.rol)).map(c => <option key={c.id} value={c.id}>{c.nombre_usuario}</option>)}</select></label>}
      <label>Box asignado <select required value={draft.box_id} onChange={e => setDraft({ ...draft, box_id: e.target.value })}><option value="">Elegí un box</option>{boxes?.filter(b => b.activo).map(b => <option key={b.id} value={b.id}>{b.nombre}</option>)}</select></label>
      <button disabled={busy}>{editing === null ? 'Crear profesional' : 'Guardar profesional'}</button>{editing !== null && <button type="button" onClick={() => { setEditing(null); setDraft(empty); }}>Cancelar edición</button>}
    </form>
    <h3>Boxes</h3>{boxes?.length === 0 && <p>No hay boxes registrados.</p>}{boxes?.map(b => <p key={b.id}>{b.nombre} · {b.activo ? 'Activo' : 'Inactivo'}</p>)}
    <form onSubmit={e => { e.preventDefault(); void write('/boxes', 'POST', { nombre: box }, result => { setBoxes(current => [...(current ?? []), result as Box]); setBox(''); }); }}><label>Nombre del box <input required maxLength={80} value={box} onChange={e => setBox(e.target.value)} /></label><button disabled={busy}>Crear box</button></form>
  </section>;
}
