import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, request } from '../api/client';
import { Button, Notice, PageTemplate, TextField } from '../components/ui';
import { failure } from './publicErrors';
import './public.css';

type Message = { mensaje: string };
type Privacy = { texto: string; version: string };
function privacyParts(texto: string): { body: string; consent: string } {
  const parts = texto.split(/\n\s*☐\s*/);
  return parts.length === 2 ? { body: parts[0], consent: parts[1].trim() } : { body: texto, consent: 'Leí y acepto el aviso de privacidad.' };
}
function PrivacyText({ text }: { text: string }) {
  return <div className="privacy-text">{text.split('\n\n').map((paragraph, index) => <p key={index}>{paragraph.split(/(\*\*[^*]+\*\*)/g).map((part, item) => part.startsWith('**') && part.endsWith('**') ? <strong key={item}>{part.slice(2, -2)}</strong> : part)}</p>)}</div>;
}


const fields = [
  ['nombre', 'Nombre', 'text'], ['apellido', 'Apellido', 'text'], ['dni', 'DNI', 'text'],
  ['telefono', 'Teléfono', 'tel'], ['email', 'Correo electrónico', 'email'], ['obra_social', 'Obra social (opcional)', 'text'],
  ['nombre_usuario', 'Nombre de usuario', 'text'], ['password', 'Contraseña', 'password'],
] as const;

export function RegisterPage() {
  const [privacy, setPrivacy] = useState<Privacy | null>(null);
  const [accepted, setAccepted] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [invalidFields, setInvalidFields] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [waiting, setWaiting] = useState(false);
  const [loadingPrivacy, setLoadingPrivacy] = useState(true);
  async function loadPrivacy() {
    setPrivacy(null); setAccepted(false); setWaiting(false); setLoadingPrivacy(true);
    try { setPrivacy(await request<Privacy>('/publico/aviso-privacidad', { onWait: () => setWaiting(true) })); } catch { setError('No pudimos cargar el aviso de privacidad. Intentá nuevamente.'); } finally { setWaiting(false); setLoadingPrivacy(false); }
  }
  useEffect(() => { void loadPrivacy(); }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!privacy || !accepted || busy) return;
    const data = new FormData(event.currentTarget);
    const body: Record<string, string | boolean | null> = {};
    for (const [name] of fields) body[name] = String(data.get(name) ?? '') || (name === 'obra_social' ? null : '');
    body.acepta_aviso_privacidad = true; body.aviso_privacidad_version = privacy.version;
    setBusy(true); setError(''); setInvalidFields([]);
    try { const result = await request<Message>('/auth/registro', { method: 'POST', body }); setMessage(result.mensaje); }
    catch (e) {
      if (e instanceof ApiError && e.status === 422 && e.invalidFields.length === 0) {
        await loadPrivacy(); setError('El aviso de privacidad puede haber cambiado. Revisalo y aceptalo nuevamente.');
      } else { setInvalidFields(e instanceof ApiError ? e.invalidFields : []); setError(failure(e)); }
    } finally { setBusy(false); }
  }
  return <PageTemplate title="Crear una cuenta" description="Completá tus datos para crear tu cuenta."><div className="public-card">
    {waiting && <Notice kind="warning">El servicio está demorando. Estamos intentando nuevamente.</Notice>}
    {message ? <Notice kind="success">{message}</Notice> : <>
      {error && <Notice kind="error">{error}</Notice>}
      <form className="public-form" onSubmit={submit}>
        {fields.map(([name, label, type]) => <TextField key={name} name={name} label={label} type={type} required={name !== 'obra_social'} autoComplete={name === 'password' ? 'new-password' : undefined} error={invalidFields.includes(name) ? 'Revisá este dato.' : undefined} />)}
        <section aria-labelledby="privacy-title"><h2 id="privacy-title">Aviso de privacidad</h2>{privacy ? <><PrivacyText text={privacyParts(privacy.texto).body} /><p>Versión: {privacy.version}</p><label><input type="checkbox" checked={accepted} onChange={e => setAccepted(e.target.checked)} /> {privacyParts(privacy.texto).consent}</label></> : loadingPrivacy ? <p>Cargando aviso de privacidad…</p> : <><p>El aviso no está disponible.</p><Button onClick={() => { setError(''); void loadPrivacy(); }}>Volver a cargar</Button></>}</section>
        <Button type="submit" disabled={!privacy || !accepted || busy}>Crear cuenta</Button><Link to="/ingresar">Volver a ingresar</Link>
      </form></>}
  </div></PageTemplate>;
}

