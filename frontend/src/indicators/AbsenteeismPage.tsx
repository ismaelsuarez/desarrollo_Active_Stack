import { useCallback, useEffect, useState } from 'react';
import { useSession } from '../auth/provider';
import { request } from '../api/client';
import { useRef } from 'react';
import './indicators.css';

type Counts = { ausentes: number; atendidos: number; cancelados: number; liberados: number; sin_cierre: number; tasa: number | null };
type Report = { resumen: Counts; evolucion: (Counts & { mes: string })[]; profesionales: (Counts & { profesional_id: number; nombre: string })[] };
type Professional = { id: number; nombre: string; apellido: string };
const percentage = (value: number | null) => value === null ? 'Sin datos' : `${new Intl.NumberFormat('es-AR', { maximumFractionDigits: 1 }).format(value * 100)} %`;
const clinicDate = (date: Date, timeZone: string) => {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(date);
  const part = (type: string) => parts.find(item => item.type === type)?.value ?? '';
  return `${part('year')}-${part('month')}-${part('day')}`;
};

export function AbsenteeismPage() {
  const { session } = useSession();
  const [hasta, setHasta] = useState('');
  const [desde, setDesde] = useState('');
  const [zoneError, setZoneError] = useState(false);
  const [zoneAttempt, setZoneAttempt] = useState(0);
  const [profesional, setProfesional] = useState('');
  const [people, setPeople] = useState<Professional[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState('');
  const [peopleError, setPeopleError] = useState(false);
  const [busy, setBusy] = useState(false);
  const sequence = useRef(0);
  const [filters, setFilters] = useState<{ desde: string; hasta: string; profesional: string } | null>(null);
  useEffect(() => {
    let active = true;
    request<{ zona_horaria: string }>('/publico/consultorio').then(clinic => {
      const end = clinicDate(new Date(), clinic.zona_horaria);
      const start = `${end.slice(0, 8)}01`;
      if (active) { setDesde(start); setHasta(end); setFilters({ desde: start, hasta: end, profesional: '' }); setZoneError(false); }
    }).catch(() => { if (active) setZoneError(true); });
    return () => { active = false; };
  }, [zoneAttempt]);
  const load = useCallback(async () => {
    if (!filters) return;
    const current = ++sequence.current;
    setBusy(true); setError('');
    const params = new URLSearchParams({ desde: filters.desde, hasta: filters.hasta });
    if (filters.profesional) params.set('profesional_id', filters.profesional);
    try { const result = await session.request<Report>(`/indicadores/ausentismo?${params}`); if (current === sequence.current) setReport(result); }
    catch { if (current === sequence.current) { setReport(null); setError('No pudimos cargar el indicador. Revisá la conexión e intentá nuevamente.'); } }
    finally { if (current === sequence.current) setBusy(false); }
  }, [session, filters]);
  useEffect(() => { void load(); return () => { sequence.current++; }; }, [load]);
  const loadPeople = useCallback(async () => { try { setPeople(await session.request<Professional[]>('/profesionales')); setPeopleError(false); } catch { setPeopleError(true); } }, [session]);
  useEffect(() => { void loadPeople(); }, [loadPeople]);
  return <main className="indicator-page"><p className="indicator-eyebrow">Administración</p><h1>Indicador de ausentismo</h1><p>Consultá las ausencias y otros resultados de los turnos por período y profesional.</p>
    <section className="indicator-panel"><h2>Filtros</h2><form className="indicator-filters" onSubmit={event => { event.preventDefault(); if (desde > hasta) { setError('La fecha desde no puede ser posterior a hasta.'); return; } setFilters({ desde, hasta, profesional }); }}>
      <label>Desde<input required type="date" disabled={!filters} value={desde} onChange={e => setDesde(e.target.value)} /></label>
      <label>Hasta<input required type="date" disabled={!filters} value={hasta} onChange={e => setHasta(e.target.value)} /></label>
      <label>Profesional<select value={profesional} onChange={e => setProfesional(e.target.value)}><option value="">Todos los profesionales</option>{people.map(p => <option value={p.id} key={p.id}>{p.nombre} {p.apellido}</option>)}</select></label><button type="submit" disabled={!filters}>Consultar</button>
    </form></section>
    {zoneError && <div role="alert" className="indicator-alert">No pudimos obtener la zona horaria del consultorio. <button type="button" onClick={() => { setZoneError(false); setZoneAttempt(value => value + 1); }}>Reintentar zona horaria</button></div>}
    {peopleError && <div role="alert" className="indicator-alert"><span>No pudimos cargar los profesionales.</span> <button type="button" onClick={() => void loadPeople()}>Reintentar profesionales</button></div>}
    {busy && <p role="status">Cargando indicador…</p>}{error && <div role="alert" className="indicator-alert">{error} <button type="button" onClick={() => void load()}>Reintentar</button></div>}
    {!busy && !error && report && <><div className="indicator-metrics"><div className="indicator-panel">Tasa de ausentismo<strong>{percentage(report.resumen.tasa)}</strong><small>{report.resumen.ausentes} ausentes de {report.resumen.ausentes + report.resumen.atendidos} cerrados</small></div><div className="indicator-panel">Ausentes<strong>{report.resumen.ausentes}</strong></div><div className="indicator-panel">Cancelados / liberados<strong>{report.resumen.cancelados} / {report.resumen.liberados}</strong></div><div className="indicator-panel">Sin cierre<strong>{report.resumen.sin_cierre}</strong></div></div>
    {report.profesionales.length === 0 && report.evolucion.length === 0 && <p>Sin datos para este período.</p>}
    {(report.evolucion.length > 0 || report.profesionales.length > 0) && <div className="indicator-content"><section className="indicator-panel"><h2>Evolución mensual</h2><p>Tasa de ausentismo de los turnos cerrados.</p><div className="indicator-bars">{report.evolucion.map(row => <div className="indicator-bar-column" key={row.mes}>{row.tasa === null ? <span>Sin datos</span> : <div role="meter" aria-label={`${row.mes}: ${percentage(row.tasa)}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={row.tasa * 100} className="indicator-bar" style={{ height: `${row.tasa / Math.max(...report.evolucion.map(item => item.tasa ?? 0), 0.01) * 100}%` }}>{percentage(row.tasa)}</div>}<small>{row.mes}</small></div>)}</div></section><section className="indicator-panel"><h2>Por profesional</h2><div className="indicator-table"><table><thead><tr><th>Profesional</th><th>Ausentes</th><th>Atendidos</th><th>Tasa</th></tr></thead><tbody>{report.profesionales.map(row => <tr key={row.profesional_id}><td>{row.nombre}</td><td>{row.ausentes}</td><td>{row.atendidos}</td><td>{percentage(row.tasa)}</td></tr>)}</tbody></table></div><p>La tasa es ausentes / (atendidos + ausentes). Cancelados, liberados y turnos sin cierre no forman parte del cálculo.</p></section></div>}</>}
  </main>;
}
