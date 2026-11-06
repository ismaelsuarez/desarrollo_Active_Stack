import { useCallback, useEffect, useRef, useState } from 'react';
import { useSession } from '../auth/provider';
import { ApiError } from '../api/client';

type StaffRole = 'recepcion' | 'profesional' | 'administrador' | 'administrativo';
type Staff = { id: number; nombre_usuario: string; email: string; rol: StaffRole; activo: boolean };
const empty = { nombre_usuario: '', email: '', password: '', rol: 'recepcion' as StaffRole };

export function Personal() {
  const { session } = useSession();
  const [items, setItems] = useState<Staff[] | null>(null);
  const [draft, setDraft] = useState(empty);
  const [editing, setEditing] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [invalidFields, setInvalidFields] = useState<string[]>([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const sending = useRef(false);
  const load = useCallback(async () => {
    try { setItems(await session.request<Staff[]>('/usuarios')); setError(''); }
    catch { setError('No pudimos cargar el personal.'); }
  }, [session]);
  useEffect(() => { void load(); }, [load]);
  async function save() {
    if (sending.current) return;
    sending.current = true; setBusy(true); setError(''); setInvalidFields([]); setMessage('');
    try {
      const body = editing === null ? draft : { nombre_usuario: draft.nombre_usuario, email: draft.email, rol: draft.rol };
      const saved = await session.request<Staff>(editing === null ? '/usuarios' : `/usuarios/${editing}`, { method: editing === null ? 'POST' : 'PATCH', body });
      setItems(current => current ? [...current.filter(item => item.id !== saved.id), saved] : [saved]);
      setDraft(empty); setEditing(null); setMessage('Personal guardado.');
    } catch (e) {
      if (e instanceof ApiError) setInvalidFields(e.invalidFields);
      setError(e instanceof ApiError ? e.status === 409 ? 'El usuario o correo ya está registrado.' : e.status === 422 ? 'Revisá los datos ingresados.' : 'No se pudo guardar el personal.' : 'No pudimos confirmar el resultado. Actualizá la lista antes de intentar nuevamente.');
    } finally { sending.current = false; setBusy(false); }
  }
  async function deactivate(id: number) {
    if (sending.current) return;
    sending.current = true; setBusy(true); setError(''); setMessage('');
    try { await session.request(`/usuarios/${id}`, { method: 'DELETE' }); setItems(current => current?.map(item => item.id === id ? { ...item, activo: false } : item) ?? null); setMessage('Personal desactivado; se conserva su historial.'); }
    catch (e) { setError(e instanceof ApiError ? 'No se pudo desactivar el personal.' : 'No pudimos confirmar el resultado. Actualizá la lista antes de intentar nuevamente.'); }
    finally { sending.current = false; setBusy(false); }
  }
  return <section><h2>Personal</h2>
    {error && <div role="alert">{error} <button type="button" onClick={() => void load()}>Actualizar lista</button></div>}
    {message && <p role="status">{message}</p>}
    {!items && !error && <p role="status">Cargando personal…</p>}
    {items?.length === 0 && <p>No hay personal registrado.</p>}
    {items?.map(item => <div key={item.id}><p>{item.nombre_usuario} · {item.email} · {item.rol} · {item.activo ? 'Activo' : 'Inactivo'}</p><button type="button" onClick={() => { setDraft({ nombre_usuario: item.nombre_usuario, email: item.email, rol: item.rol, password: '' }); setEditing(item.id); }}>Editar {item.nombre_usuario}</button>{item.activo && <button type="button" disabled={busy} onClick={() => void deactivate(item.id)}>Desactivar {item.nombre_usuario}</button>}</div>)}
    <form onSubmit={e => { e.preventDefault(); void save(); }}>
      <label>Usuario <input required aria-invalid={invalidFields.includes('nombre_usuario')} value={draft.nombre_usuario} onChange={e => setDraft({ ...draft, nombre_usuario: e.target.value })} /></label>{invalidFields.includes('nombre_usuario') && <p>Revisá el usuario.</p>}
      <label>Correo <input required type="email" aria-invalid={invalidFields.includes('email')} value={draft.email} onChange={e => setDraft({ ...draft, email: e.target.value })} /></label>{invalidFields.includes('email') && <p>Revisá el correo.</p>}
      {editing === null && <><label>Contraseña inicial <input required type="password" minLength={12} maxLength={128} aria-invalid={invalidFields.includes('password')} value={draft.password} onChange={e => setDraft({ ...draft, password: e.target.value })} /></label>{invalidFields.includes('password') && <p>Revisá la contraseña.</p>}</>}
      <label>Rol <select value={draft.rol} onChange={e => setDraft({ ...draft, rol: e.target.value as StaffRole })}><option value="recepcion">Recepción</option><option value="profesional">Profesional</option><option value="administrador">Administrador</option><option value="administrativo">Administrativo</option></select></label>
      <button disabled={busy}>{editing === null ? 'Crear personal' : 'Guardar personal'}</button>
      {editing !== null && <button type="button" onClick={() => { setEditing(null); setDraft(empty); }}>Cancelar edición</button>}
    </form>
  </section>;
}
