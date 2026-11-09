import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { request } from '../api/client';
import { Button, Notice, PageTemplate, TextField } from '../components/ui';
import { failure } from './publicErrors';
import './public.css';

type Message = { mensaje: string };
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

