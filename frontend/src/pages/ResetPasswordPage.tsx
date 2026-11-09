import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, request } from '../api/client';
import { Button, Notice, PageTemplate, TextField } from '../components/ui';
import { consumeFragment } from './tokenFragment';
import './public.css';

type Message = { mensaje: string };
export function ResetPasswordPage() {
  const token = useRef<string | null | undefined>(undefined);
  const [ready, setReady] = useState(false); const [password, setPassword] = useState(''); const [message, setMessage] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  useEffect(() => { if (token.current === undefined) token.current = consumeFragment(); setReady(true); }, []);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!token.current || busy) return;
    if (password.length < 8 || password.length > 128) { setError('La contraseña debe tener entre 8 y 128 caracteres.'); return; }
    setBusy(true); setError('');
    try { const result = await request<Message>('/auth/restablecer-password', { method: 'POST', body: { token: token.current, password } }); token.current = null; setPassword(''); setMessage(result.mensaje); }
    catch (e) { const uncertainResult = !(e instanceof ApiError) || (e.status !== 400 && e.status !== 422); setUncertain(uncertainResult); if (uncertainResult) setPassword(''); setError(e instanceof ApiError && e.status === 422 ? 'La contraseña debe tener al menos 8 caracteres.' : e instanceof ApiError && e.status === 400 ? 'El enlace no es válido, venció o ya fue utilizado.' : 'No pudimos confirmar el cambio. Probá ingresar con la contraseña nueva o pedí un enlace nuevo.'); } finally { setBusy(false); }
  }
  return <PageTemplate title="Restablecer contraseña"><div className="public-card">{error && <Notice kind="error">{error}</Notice>}{message ? <Notice kind="success">{message}</Notice> : uncertain ? null : ready && !token.current ? <Notice kind="error">Falta el enlace para restablecer la contraseña. Solicitá uno nuevo.</Notice> : ready ? <form className="public-form" onSubmit={submit}><TextField label="Nueva contraseña" type="password" autoComplete="new-password" minLength={8} maxLength={128} required value={password} onChange={e => setPassword(e.target.value)} /><Button type="submit" disabled={busy}>Restablecer contraseña</Button></form> : <Notice>Preparando enlace…</Notice>}<p><Link to="/ingresar">Ir a ingresar</Link> · <Link to="/recuperar-password">Solicitar un enlace</Link></p></div></PageTemplate>;
}
