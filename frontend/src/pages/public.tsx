import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, request } from '../api/client';
import { useSession } from '../auth/provider';
import { Button, Notice, PageTemplate, TextField } from '../components/ui';
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
const failure = (error: unknown) => error instanceof ApiError && error.status === 429 ? 'Demasiados intentos. Intentá más tarde.' : 'No pudimos continuar. Revisá los datos e intentá nuevamente.';

export function LoginPage() {
  const { session, state } = useSession();
  const [identificador, setIdentificador] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null);
    try { await session.login(identificador, password); } catch (e) { setError(e); } finally { setBusy(false); }
  }
  return <PageTemplate title="Ingresar" description="Usá los datos de tu cuenta para continuar."><div className="public-card">
    {state.logoutUnconfirmed && <Notice kind="warning">No pudimos confirmar el cierre de sesión en el servidor.</Notice>}
    {error !== null && <Notice kind="error">{error instanceof ApiError && error.status === 403 ? <>Verificá tu correo para ingresar. <Link to="/reenviar-verificacion">Reenviar enlace</Link></> : error instanceof ApiError && error.status === 429 ? 'Demasiados intentos. Intentá más tarde.' : 'No pudimos ingresar. Revisá tus datos e intentá nuevamente.'}</Notice>}
    <form className="public-form" onSubmit={submit}>
      <TextField label="Usuario o correo" name="identificador" autoComplete="username" required value={identificador} onChange={e => setIdentificador(e.target.value)} />
      <TextField label="Contraseña" name="password" type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} />
      <Link to="/recuperar-password">Olvidé mi contraseña</Link><Button type="submit" disabled={busy}>Ingresar</Button>
    </form><p>¿Todavía no tenés cuenta? <Link to="/registro">Crear cuenta</Link></p>
  </div></PageTemplate>;
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
  async function loadPrivacy() {
    setPrivacy(null); setAccepted(false); setWaiting(false);
    try { setPrivacy(await request<Privacy>('/publico/aviso-privacidad', { onWait: () => setWaiting(true) })); } catch { setError('No pudimos cargar el aviso de privacidad. Intentá nuevamente.'); } finally { setWaiting(false); }
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
        <section aria-labelledby="privacy-title"><h2 id="privacy-title">Aviso de privacidad</h2>{privacy ? <><PrivacyText text={privacyParts(privacy.texto).body} /><p>Versión: {privacy.version}</p><label><input type="checkbox" checked={accepted} onChange={e => setAccepted(e.target.checked)} /> {privacyParts(privacy.texto).consent}</label></> : <><p>El aviso no está disponible.</p><Button onClick={() => { setError(''); void loadPrivacy(); }}>Volver a cargar</Button></>}</section>
        <Button type="submit" disabled={!privacy || !accepted || busy}>Crear cuenta</Button><Link to="/ingresar">Volver a ingresar</Link>
      </form></>}
  </div></PageTemplate>;
}

export function EmailRequestPage({ mode }: { mode: 'recover' | 'resend' }) {
  const [email, setEmail] = useState(''); const [message, setMessage] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('');
    try { const result = await request<Message>(mode === 'recover' ? '/auth/recuperar-password' : '/auth/reenviar-verificacion', { method: 'POST', body: { email } }); setMessage(result.mensaje); }
    catch (e) { setError(failure(e)); } finally { setBusy(false); }
  }
  return <PageTemplate title={mode === 'recover' ? 'Recuperar contraseña' : 'Reenviar verificación'}><div className="public-card">
    {error && <Notice kind="error">{error}</Notice>}{message && <Notice kind="success">{message}</Notice>}
    <form className="public-form" onSubmit={submit}><TextField label="Correo electrónico" type="email" value={email} onChange={e => setEmail(e.target.value)} required /><Button type="submit" disabled={busy}>{mode === 'recover' ? 'Enviar enlace' : 'Solicitar enlace'}</Button><Link to="/ingresar">Volver</Link></form>
  </div></PageTemplate>;
}

function consumeFragment(): string | null {
  const token = new URLSearchParams(window.location.hash.slice(1)).get('token');
  if (window.location.hash) window.history.replaceState(window.history.state, '', window.location.pathname + window.location.search);
  return token || null;
}

export function TokenActionPage({ action }: { action: 'verify' | 'confirm' }) {
  const pending = useRef<Promise<unknown> | null>(null);
  const [result, setResult] = useState<'loading' | 'success' | 'error'>('loading');
  useEffect(() => {
    if (!pending.current) {
      const token = consumeFragment();
      pending.current = token ? request(action === 'verify' ? '/auth/verificar-email' : '/turnos/confirmar-por-enlace', { method: 'POST', body: { token } }) : Promise.reject(new Error('Enlace ausente'));
    }
    let active = true;
    pending.current.then(() => { if (active) setResult('success'); }, () => { if (active) setResult('error'); });
    return () => { active = false; };
  }, [action]);
  const title = action === 'verify' ? 'Verificar correo' : 'Confirmar turno';
  return <PageTemplate title={title}><div className="public-card">{result === 'loading' ? <Notice>Procesando enlace…</Notice> : result === 'success' ? <Notice kind="success">{action === 'verify' ? 'Correo verificado' : 'Turno confirmado'}</Notice> : <Notice kind="error">El enlace no es válido, venció o ya fue utilizado. Solicitá uno nuevo.</Notice>}<p><Link to="/ingresar">Ir a ingresar</Link></p></div></PageTemplate>;
}

export function ResetPasswordPage() {
  const token = useRef<string | null | undefined>(undefined);
  const [ready, setReady] = useState(false); const [password, setPassword] = useState(''); const [message, setMessage] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  useEffect(() => { if (token.current === undefined) token.current = consumeFragment(); setReady(true); }, []);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!token.current || busy) return;
    if (password.length < 8 || password.length > 128) { setError('La contraseña debe tener entre 8 y 128 caracteres.'); return; }
    setBusy(true); setError('');
    try { const result = await request<Message>('/auth/restablecer-password', { method: 'POST', body: { token: token.current, password } }); token.current = null; setPassword(''); setMessage(result.mensaje); }
    catch (e) { setError(e instanceof ApiError && e.status === 422 ? 'La contraseña debe tener al menos 8 caracteres.' : 'El enlace no es válido, venció o ya fue utilizado.'); } finally { setBusy(false); }
  }
  return <PageTemplate title="Restablecer contraseña"><div className="public-card">{error && <Notice kind="error">{error}</Notice>}{message ? <Notice kind="success">{message}</Notice> : ready && !token.current ? <Notice kind="error">Falta el enlace para restablecer la contraseña. Solicitá uno nuevo.</Notice> : ready ? <form className="public-form" onSubmit={submit}><TextField label="Nueva contraseña" type="password" autoComplete="new-password" minLength={8} maxLength={128} required value={password} onChange={e => setPassword(e.target.value)} /><Button type="submit" disabled={busy}>Restablecer contraseña</Button></form> : <Notice>Preparando enlace…</Notice>}<p><Link to="/recuperar-password">Solicitar un enlace</Link></p></div></PageTemplate>;
}
