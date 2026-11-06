import { useEffect, useRef, useState } from 'react';
import { useSession } from '../auth/provider';
import { ApiError } from '../api/client';
type Profesional = { id: number; nombre: string; apellido: string; activo: boolean };
type Bloque = { dia_semana: number; hora_inicio: string; hora_fin: string };
const days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
export function Horarios() {
  const { session } = useSession();
  const [profesionales, setProfesionales] = useState<Profesional[]>([]);
  const [selected, setSelected] = useState(''); const [bloques, setBloques] = useState<Bloque[] | null>(null);
  const [error, setError] = useState(''); const [message, setMessage] = useState(''); const [busy, setBusy] = useState(false);
  const generation = useRef(0); const sending = useRef(false);
  useEffect(() => { void session.request<Profesional[]>('/profesionales').then(setProfesionales).catch(() => setError('No pudimos cargar profesionales.')); }, [session]);
  useEffect(() => {
    const current = ++generation.current; setBloques(null); setError(''); setMessage('');
    if (!selected) return;
    void session.request<{ bloques: Bloque[] }>(`/profesionales/${selected}/horario-semanal`).then(data => { if (generation.current === current) setBloques(data.bloques.map(b => ({ dia_semana: b.dia_semana, hora_inicio: b.hora_inicio.slice(0, 5), hora_fin: b.hora_fin.slice(0, 5) }))); }).catch(() => { if (generation.current === current) setError('No pudimos cargar el horario.'); });
    return () => { generation.current++; };
  }, [session, selected]);
  function change(i: number, values: Partial<Bloque>) { setBloques(current => current?.map((item, index) => index === i ? { ...item, ...values } : item) ?? null); }
  async function save() {
    if (!bloques || !selected || sending.current) return;
    if (bloques.some(b => !b.hora_inicio || !b.hora_fin || b.hora_inicio >= b.hora_fin)) { setError('El inicio debe ser anterior al fin en todos los bloques.'); return; }
    const ordered = [...bloques].sort((a, b) => a.dia_semana - b.dia_semana || a.hora_inicio.localeCompare(b.hora_inicio));
    if (ordered.some((b, i) => i > 0 && ordered[i - 1].dia_semana === b.dia_semana && b.hora_inicio < ordered[i - 1].hora_fin)) { setError('Los bloques del mismo día se superponen.'); return; }
    sending.current = true; setBusy(true); setError(''); setMessage(''); const current = generation.current;
    try { const data = await session.request<{ bloques: Bloque[] }>(`/profesionales/${selected}/horario-semanal`, { method: 'PUT', body: { bloques } }); if (generation.current === current) { setBloques(data.bloques.map(b => ({ dia_semana: b.dia_semana, hora_inicio: b.hora_inicio.slice(0, 5), hora_fin: b.hora_fin.slice(0, 5) }))); setMessage('Horario guardado.'); } }
    catch (e) { if (generation.current === current) setError(e instanceof ApiError ? 'No pudimos guardar el horario. Revisá los bloques.' : 'No pudimos confirmar el resultado. Consultá el horario antes de volver a intentar.'); }
    finally { sending.current = false; setBusy(false); }
  }
  return <section><h2>Horario semanal</h2><label>Profesional de horario <select value={selected} onChange={e => setSelected(e.target.value)}><option value="">Elegí un profesional</option>{profesionales.filter(p => p.activo).map(p => <option key={p.id} value={p.id}>{p.nombre} {p.apellido}</option>)}</select></label>
    {error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}{selected && !bloques && !error && <p role="status">Cargando horario…</p>}
    {bloques && <form onSubmit={e => { e.preventDefault(); void save(); }}>{bloques.length === 0 && <p>No hay bloques semanales.</p>}{bloques.map((b, i) => <fieldset key={i}><legend>Bloque {i + 1}</legend><label>Día {i + 1} <select value={b.dia_semana} onChange={e => change(i, { dia_semana: Number(e.target.value) })}>{days.map((day, d) => <option key={day} value={d + 1}>{day}</option>)}</select></label><label>Inicio {i + 1} <input type="time" required value={b.hora_inicio} onChange={e => change(i, { hora_inicio: e.target.value })} /></label><label>Fin {i + 1} <input type="time" required value={b.hora_fin} onChange={e => change(i, { hora_fin: e.target.value })} /></label><button type="button" onClick={() => setBloques(bloques.filter((_, index) => index !== i))}>Quitar bloque {i + 1}</button></fieldset>)}<button type="button" onClick={() => setBloques([...bloques, { dia_semana: 1, hora_inicio: '', hora_fin: '' }])}>Agregar bloque</button><button disabled={busy}>Guardar horario</button></form>}
  </section>;
}
