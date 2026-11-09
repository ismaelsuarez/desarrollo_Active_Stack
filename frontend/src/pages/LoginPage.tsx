import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ApiError } from '../api/client';
import { useSession } from '../auth/provider';
import { Button, Notice, PageTemplate, TextField } from '../components/ui';
import './public.css';

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
