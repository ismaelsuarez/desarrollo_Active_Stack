import { useState, type FormEvent } from 'react';
import { ApiError } from '../api/client';
import { useSession } from '../auth/provider';
import { Button, Notice, PageTemplate, TextField } from '../components/ui';
import './account.css';

export function AccountPage() {
  const { session, state } = useSession();
  const [actual, setActual] = useState('');
  const [nueva, setNueva] = useState('');
  const [confirmacion, setConfirmacion] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [telefono, setTelefono] = useState('');
  const [email, setEmail] = useState('');
  const [currentEmail, setCurrentEmail] = useState(state.profile?.email ?? '');
  const [contactMessage, setContactMessage] = useState('');
  const [contactError, setContactError] = useState('');
  const [contactBusy, setContactBusy] = useState(false);

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (nueva !== confirmacion) { setMessage(''); setError('Las contraseñas no coinciden.'); return; }
    setMessage(''); setError(''); setBusy(true);
    try {
      await session.request('/auth/cambiar-password', { method: 'PATCH', body: { password_actual: actual, password_nueva: nueva } });
      setActual(''); setNueva(''); setConfirmacion(''); setMessage('Contraseña actualizada');
    } catch (failure) {
      setError(failure instanceof ApiError && failure.status === 403 ? 'La contraseña actual no es correcta.' :
        failure instanceof ApiError && failure.status === 422 ? 'Revisá la contraseña nueva e intentá de nuevo.' :
        'No pudimos actualizar la contraseña. Intentá nuevamente.');
    } finally { setBusy(false); }
  }

  async function updateContact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (state.profile?.rol !== 'paciente' || (!telefono.trim() && !email.trim())) return;
    const body: { telefono?: string; email?: string } = {};
    if (telefono.trim()) body.telefono = telefono;
    if (email.trim()) body.email = email;
    const changedEmail = !!body.email && body.email.trim().toLowerCase() !== currentEmail.trim().toLowerCase();
    setContactMessage(''); setContactError(''); setContactBusy(true);
    try {
      await session.request('/auth/actualizar-cuenta', { method: 'PATCH', body });
      if (body.email) setCurrentEmail(body.email.trim().toLowerCase());
      setContactMessage(changedEmail ? 'Contacto actualizado. Verificá nuevamente tu correo electrónico.' : 'Contacto actualizado.');
    } catch (failure) {
      setContactError(failure instanceof ApiError && failure.status === 409 ? 'Ese correo ya está utilizado.' :
        failure instanceof ApiError && failure.status === 422 ? 'Revisá los datos de contacto.' :
        'No pudimos actualizar el contacto. Intentá nuevamente.');
    } finally { setContactBusy(false); }
  }

  return <PageTemplate title="Mi cuenta">
    {state.profile?.rol === 'paciente' && <section className="account-card"><h2>Datos de contacto</h2><form onSubmit={updateContact}>
      <TextField label="Teléfono" type="tel" value={telefono} onChange={event => setTelefono(event.target.value)} />
      <TextField label="Correo electrónico" type="email" value={email} onChange={event => setEmail(event.target.value)} />
      <Button type="submit" disabled={contactBusy || (!telefono.trim() && !email.trim())}>Guardar contacto</Button>
      {contactError && <Notice kind="error">{contactError}</Notice>}
      {contactMessage && <Notice kind="success">{contactMessage}</Notice>}
    </form></section>}
    <div className="account-security-layout"><section className="account-card"><h2>Cambiar contraseña</h2><form onSubmit={changePassword}>
      <TextField label="Contraseña actual" type="password" value={actual} onChange={event => setActual(event.target.value)} required />
      <TextField label="Contraseña nueva" type="password" value={nueva} onChange={event => setNueva(event.target.value)} required />
      <TextField label="Confirmar nueva contraseña" type="password" value={confirmacion} onChange={event => setConfirmacion(event.target.value)} required />
      <Button type="submit" disabled={busy}>Cambiar contraseña</Button>
      {error && <Notice kind="error">{error}</Notice>}
      {message && <Notice kind="success">{message}</Notice>}
    </form></section>{state.profile?.rol !== 'paciente' && <aside className="account-security-note"><span aria-hidden="true">✳</span><h2>Seguridad de tu cuenta</h2><p>Elegí una contraseña segura y no la compartas con otras personas.</p></aside>}</div>
  </PageTemplate>;
}
