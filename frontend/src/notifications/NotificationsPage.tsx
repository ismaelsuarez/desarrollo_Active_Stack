import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useSession } from '../auth/provider';
import { ApiError } from '../api/client';
import { Button, Notice, PageTemplate } from '../components/ui';
import './notifications.css';
import { displayClinicTime, useClinicZone } from './time';
import { Summary } from './Summary';

type Notification = { id: number; turno_id: number | null; tipo: string; programada_para: string; intentos?: number };
const typeLabels: Record<string, string> = { solicitud_confirmacion: 'Solicitud de confirmación', recordatorio: 'Recordatorio', cancelacion_por_personal: 'Cancelación', reprogramacion_por_personal: 'Reprogramación', liberacion: 'Liberación' };

export function NotificationsPage() {
  const { session, state } = useSession();
  const zone = useClinicZone();
  const [channel, setChannel] = useState<'whatsapp' | 'email'>('whatsapp');
  const [offset, setOffset] = useState(0);
  const [retry, setRetry] = useState(0);
  const [items, setItems] = useState<Notification[] | null>(null);
  const [error, setError] = useState(false);
  const [actionError, setActionError] = useState('');
  const [message, setMessage] = useState('');
  const [fallback, setFallback] = useState('');
  const [busy, setBusy] = useState<number | null>(null);
  const inFlight = useRef(false);
  useEffect(() => {
    let active = true;
    setItems(null); setError(false);
    const status = channel === 'whatsapp' ? 'preparada' : 'fallida';
    session.request<Notification[]>(`/notificaciones?canal=${channel}&estado=${status}&limit=20&offset=${offset}`)
      .then(data => { if (active) setItems(data); })
      .catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, [session, state.profile?.id, channel, offset, retry]);
  async function openWhatsApp(id: number) {
    if (inFlight.current) return; inFlight.current = true;
    setActionError(''); setMessage(''); setFallback(''); setBusy(id);
    try {
      const result = await session.request<{ enlace_whatsapp: string }>(`/notificaciones/${id}/whatsapp`);
      const url = new URL(result.enlace_whatsapp);
      if (url.protocol !== 'https:' || url.hostname !== 'wa.me' || url.port || url.username || url.password) throw new Error('invalid');
      const opened = window.open(url.href, '_blank', 'noopener,noreferrer');
      if (!opened) { setFallback(url.href); setMessage('Si la ventana fue bloqueada, abrí el enlace seguro.'); }
      else setMessage('WhatsApp abierto. Marcá enviada solo después de enviarla.');
    } catch { setActionError('No pudimos abrir WhatsApp o el enlace no válido.'); }
    finally { inFlight.current = false; setBusy(null); }
  }
  async function markSent(id: number) {
    if (inFlight.current) return; inFlight.current = true;
    setBusy(id); setActionError(''); setMessage(''); setFallback('');
    try {
      await session.request(`/notificaciones/${id}/marcar-enviada`, { method: 'POST' });
      setMessage('Se guardó el registro de envío; no confirma la entrega.');
    } catch (e) {
      setActionError(e instanceof ApiError && e.status === 409 ? 'La notificación cambió. Revisá su estado.' : 'No pudimos confirmar el resultado. Revisá el estado antes de reintentar.');
    } finally { setRetry(n => n + 1); window.dispatchEvent(new Event('operaciones-actualizadas')); inFlight.current = false; setBusy(null); }
  }
  return <PageTemplate title="Notificaciones" description="Revisá los mensajes preparados y los turnos que necesitan atención.">
    <Summary revision={retry} onSelect={value => { setChannel(value); setOffset(0); }} />
    <nav className="notifications-tabs" aria-label="Bandejas"><Button variant={channel === 'whatsapp' ? 'primary' : 'secondary'} onClick={() => { setChannel('whatsapp'); setOffset(0); }}>WhatsApp preparado</Button><Button variant={channel === 'email' ? 'primary' : 'secondary'} onClick={() => { setChannel('email'); setOffset(0); }}>Correos fallidos</Button><Link to="/sin-confirmar">Sin confirmar</Link>{state.profile?.rol === 'administrador' && <Link to="/estado-operativo">Estado operativo</Link>}</nav>
    <section className="notifications-panel"><h2>{channel === 'whatsapp' ? 'WhatsApp preparados' : 'Correos fallidos'}</h2><p>{channel === 'whatsapp' ? 'Abrir el enlace no marca el mensaje como enviado.' : 'Revisá los envíos que no pudieron completarse.'}</p>
    {actionError && <Notice kind="error">{actionError}</Notice>}{message && <Notice>{message}</Notice>}{fallback && <a href={fallback} target="_blank" rel="noopener noreferrer">Abrir enlace seguro de WhatsApp</a>}
    {error && <><Notice kind="error">No pudimos cargar las notificaciones.</Notice><Button onClick={() => setRetry(n => n + 1)}>Reintentar lectura</Button></>}
    {!items && !error && <Notice>Cargando notificaciones…</Notice>}
    {items && (items.length === 0 ? <p>No hay notificaciones en esta bandeja.</p> : <ul className="notifications-list">{items.map(item => <li key={item.id}><div><strong>{typeLabels[item.tipo] ?? item.tipo.replaceAll('_', ' ')}</strong><p>Notificación {item.id} · {item.turno_id ? <Link to={`/agenda?turno=${item.turno_id}`}>Turno {item.turno_id}</Link> : 'Sin turno'} · {displayClinicTime(item.programada_para, zone)}{channel === 'email' && item.intentos !== undefined && <> · {item.intentos} intentos</>}</p></div>{channel === 'whatsapp' && <div className="notifications-actions"><Button disabled={busy !== null} onClick={() => void openWhatsApp(item.id)} aria-label={`Abrir WhatsApp ${item.id}`}>Abrir WhatsApp</Button><Button disabled={busy !== null} variant="secondary" onClick={() => void markSent(item.id)} aria-label={`Marcar enviada ${item.id}`}>Marcar enviada</Button></div>}</li>)}</ul>)}
    {items && <div className="notifications-actions"><Button variant="secondary" disabled={offset === 0} onClick={() => setOffset(n => Math.max(0, n - 20))}>Anterior</Button><span>Página {offset / 20 + 1}</span><Button variant="secondary" disabled={items.length < 20} onClick={() => setOffset(n => n + 20)}>Siguiente</Button></div>}</section>
  </PageTemplate>;
}

export function HealthPage() {
  const { session, state } = useSession();
  const zone = useClinicZone();
  const [data, setData] = useState<{ fallidas: number; programada_mas_antigua_segundos: number | null; enviando: number; enviando_mas_antigua_segundos: number | null; correos_del_dia: number; limite_diario: number; alerta: boolean; ultimo_barrido: { iniciado_en: string } | null } | null>(null);
  const [error, setError] = useState(false); const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true; setData(null); setError(false);
    session.request<NonNullable<typeof data>>('/notificaciones/indicadores').then(result => { if (active) setData(result); }).catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, [session, state.profile?.id, retry]);
  const age = (value: number | null) => value === null ? 'No disponible' : `${Math.floor(value)} segundos`;
  const stale = data?.ultimo_barrido && Date.now() - Date.parse(data.ultimo_barrido.iniciado_en) > 15 * 60 * 1000;
  return <PageTemplate title="Salud operativa" description="Estado del barrido y de los envíos.">
    {error && <><Notice kind="error">No pudimos cargar los indicadores.</Notice><Button onClick={() => setRetry(n => n + 1)}>Reintentar lectura</Button></>}
    {!data && !error && <Notice>Cargando indicadores…</Notice>}
    {data && <section className="notifications-panel"><h2>Estado operativo</h2>{data.ultimo_barrido ? <p>{stale && 'Advertencia: barrido antiguo · '}{displayClinicTime(data.ultimo_barrido.iniciado_en, zone)}</p> : <p>Sin barridos registrados.</p>}
      <div className="notifications-metrics"><article><p>Programada más antigua: {age(data.programada_mas_antigua_segundos)}</p></article><article><p>Enviando: {data.enviando} · antigüedad: {age(data.enviando_mas_antigua_segundos)}</p></article><article><p>Fallidas: {data.fallidas}</p></article><article><p>Correos del día: {data.correos_del_dia} de {data.limite_diario}</p></article></div>{data.alerta && <Notice kind="warning">Alerta de cuota de correo.</Notice>}</section>}
  </PageTemplate>;
}
