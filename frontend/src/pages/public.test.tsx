import { StrictMode } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import { EmailRequestPage, LoginPage, RegisterPage, ResetPasswordPage, TokenActionPage } from './public';

const mocks = vi.hoisted(() => ({ request: vi.fn(), login: vi.fn(), state: { profile: null, loading: false, logoutUnconfirmed: false } }));
vi.mock('../api/client', async (importOriginal) => ({ ...(await importOriginal<typeof import('../api/client')>()), request: mocks.request }));
vi.mock('../auth/provider', () => ({ useSession: () => ({ session: { login: mocks.login }, state: mocks.state }) }));

beforeEach(() => { mocks.request.mockReset(); mocks.login.mockReset(); mocks.state.logoutUnconfirmed = false; window.history.replaceState(null, '', '/'); });
const show = (element: React.ReactNode) => render(<MemoryRouter>{element}</MemoryRouter>);

describe('cuentas públicas', () => {
  it('presenta formato y consentimiento del aviso sin duplicar casillas', async () => {
    mocks.request.mockResolvedValueOnce({ texto: '**Título**\n\nTexto informativo.\n\n☐ Leí y acepto el aviso.', version: 'v1' });
    show(<RegisterPage />);
    expect(await screen.findByText('Título', { selector: 'strong' })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Leí y acepto el aviso.' })).not.toBeChecked();
    expect(screen.getAllByRole('checkbox')).toHaveLength(1);
    expect(document.body.textContent).not.toContain('☐');
    expect(document.body.textContent).not.toContain('**');
  });
  it('avisa cuando el servicio tarda en cargar el aviso', async () => {
    mocks.request.mockImplementation((_path: string, options: { onWait?: () => void }) => {
      options?.onWait?.();
      return new Promise(() => undefined);
    });
    show(<RegisterPage />);
    expect(await screen.findByText(/servicio está demorando/i)).toBeInTheDocument();
  });
  it('solicita aviso y no permite registrarse sin aceptación', async () => {
    mocks.request.mockResolvedValueOnce({ texto: 'Aviso vigente', version: 'v1' });
    show(<RegisterPage />);
    expect(await screen.findByText('Aviso vigente')).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: /acepto/i })).not.toBeChecked();
    expect(screen.getByRole('button', { name: /crear cuenta/i })).toBeDisabled();
  });

  it('envía la versión del aviso aceptado sin rol ni consultorio', async () => {
    mocks.request.mockResolvedValueOnce({ texto: 'Aviso vigente', version: 'v2' }).mockResolvedValueOnce({ mensaje: 'Revisá tu correo' });
    show(<RegisterPage />);
    await screen.findByText('Aviso vigente');
    for (const [label, value] of [['Nombre', 'Ana'], ['Apellido', 'Pérez'], ['DNI', '12345678'], ['Teléfono', '123456'], ['Correo electrónico', 'ana@example.com'], ['Nombre de usuario', 'ana'], ['Contraseña', '12345678']]) {
      fireEvent.change(screen.getByLabelText(label), { target: { value } });
    }
    fireEvent.click(screen.getByRole('checkbox', { name: /acepto/i }));
    fireEvent.click(screen.getByRole('button', { name: /crear cuenta/i }));
    await waitFor(() => expect(mocks.request).toHaveBeenCalledWith('/auth/registro', { method: 'POST', body: {
      nombre: 'Ana', apellido: 'Pérez', dni: '12345678', telefono: '123456', email: 'ana@example.com', obra_social: null,
      nombre_usuario: 'ana', password: '12345678', acepta_aviso_privacidad: true, aviso_privacidad_version: 'v2',
    } }));
    expect(await screen.findByText('Revisá tu correo')).toBeInTheDocument();
  });

  it('si cambia el aviso pide una nueva aceptación', async () => {
    mocks.request.mockResolvedValueOnce({ texto: 'Aviso anterior', version: 'v1' }).mockRejectedValueOnce(new ApiError(422)).mockResolvedValueOnce({ texto: 'Aviso actualizado', version: 'v2' });
    show(<RegisterPage />); await screen.findByText('Aviso anterior');
    for (const label of ['Nombre', 'Apellido', 'DNI', 'Teléfono', 'Nombre de usuario', 'Contraseña']) fireEvent.change(screen.getByLabelText(label), { target: { value: '12345678' } });
    fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: 'ana@example.com' } });
    fireEvent.click(screen.getByRole('checkbox')); fireEvent.click(screen.getByRole('button', { name: /crear cuenta/i }));
    expect(await screen.findByText('Aviso actualizado')).toBeInTheDocument();
    expect(screen.getByRole('checkbox')).not.toBeChecked();
    expect(screen.getByRole('button', { name: /crear cuenta/i })).toBeDisabled();
  });

  it('bloquea el registro cuando no puede cargar el aviso', async () => {
    mocks.request.mockRejectedValueOnce(new Error('red'));
    show(<RegisterPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/aviso de privacidad/i);
    expect(screen.getByRole('button', { name: /crear cuenta/i })).toBeDisabled();
  });

  it('presenta errores de campos del registro', async () => {
    mocks.request.mockResolvedValueOnce({ texto: 'Aviso', version: 'v1' }).mockRejectedValueOnce(new ApiError(422, ['dni']));
    show(<RegisterPage />); await screen.findByText('Aviso');
    for (const label of ['Nombre', 'Apellido', 'DNI', 'Teléfono', 'Nombre de usuario', 'Contraseña']) fireEvent.change(screen.getByLabelText(label), { target: { value: '12345678' } });
    fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: 'ana@example.com' } });
    fireEvent.click(screen.getByRole('checkbox')); fireEvent.click(screen.getByRole('button', { name: /crear cuenta/i }));
    await waitFor(() => expect(screen.getByLabelText('DNI')).toHaveAttribute('aria-invalid', 'true'));
    expect(screen.getByLabelText('DNI')).toHaveAccessibleDescription('Revisá este dato.');
  });

  it('muestra error genérico de credenciales', async () => {
    mocks.login.mockRejectedValueOnce(new ApiError(401));
    show(<LoginPage />);
    fireEvent.change(screen.getByLabelText('Usuario o correo'), { target: { value: 'ana' } });
    fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'incorrecta' } });
    fireEvent.click(screen.getByRole('button', { name: 'Ingresar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/no pudimos ingresar/i);
  });

  it('advierte cuando no se confirmó la revocación al cerrar sesión', () => {
    mocks.state.logoutUnconfirmed = true;
    show(<LoginPage />);
    expect(screen.getByRole('status')).toHaveTextContent('No pudimos confirmar el cierre de sesión en el servidor.');
  });

  it('ofrece reenvío si el correo no fue verificado', async () => {
    mocks.login.mockRejectedValueOnce(new ApiError(403)); show(<LoginPage />);
    fireEvent.change(screen.getByLabelText('Usuario o correo'), { target: { value: 'ana' } });
    fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: '12345678' } });
    fireEvent.click(screen.getByRole('button', { name: 'Ingresar' }));
    expect(await screen.findByRole('link', { name: 'Reenviar enlace' })).toHaveAttribute('href', '/reenviar-verificacion');
  });

  it('procesa el fragmento una sola vez incluso en StrictMode', async () => {
    window.history.replaceState(null, '', '/verificar-email#token=secreto');
    mocks.request.mockResolvedValue({ mensaje: 'Correo verificado' });
    show(<StrictMode><TokenActionPage action="verify" /></StrictMode>);
    expect(await screen.findByText('Correo verificado')).toBeInTheDocument();
    expect(mocks.request).toHaveBeenCalledTimes(1);
    expect(mocks.request).toHaveBeenCalledWith('/auth/verificar-email', { method: 'POST', body: { token: 'secreto' } });
    expect(window.location.hash).toBe('');
    expect(document.body.textContent).not.toContain('secreto');
  });

  it('no envía un enlace ausente', async () => {
    show(<ResetPasswordPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/enlace/i);
    expect(mocks.request).not.toHaveBeenCalled();
  });

  it('confirma el turno con token exclusivamente en el cuerpo', async () => {
    window.history.replaceState(null, '', '/confirmar-turno#token=otro'); mocks.request.mockResolvedValue({});
    show(<TokenActionPage action="confirm" />);
    expect(await screen.findByText('Turno confirmado')).toBeInTheDocument();
    expect(mocks.request).toHaveBeenCalledWith('/turnos/confirmar-por-enlace', { method: 'POST', body: { token: 'otro' } });
    expect(window.location.hash).toBe('');
  });

  it('informa enlace rechazado sin repetir la operación', async () => {
    window.history.replaceState(null, '', '/verificar-email#token=caducado'); mocks.request.mockRejectedValueOnce(new ApiError(400));
    show(<TokenActionPage action="verify" />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/venció/i);
    expect(mocks.request).toHaveBeenCalledTimes(1);
  });

  it('restablece contraseña usando el token en cuerpo', async () => {
    window.history.replaceState(null, '', '/restablecer-password#token=privado'); mocks.request.mockResolvedValueOnce({ mensaje: 'Contraseña restablecida' });
    show(<ResetPasswordPage />);
    fireEvent.change(await screen.findByLabelText('Nueva contraseña'), { target: { value: '12345678' } });
    fireEvent.click(screen.getByRole('button', { name: 'Restablecer contraseña' }));
    expect(await screen.findByText('Contraseña restablecida')).toBeInTheDocument();
    expect(mocks.request).toHaveBeenCalledWith('/auth/restablecer-password', { method: 'POST', body: { token: 'privado', password: '12345678' } });
    expect(window.location.hash).toBe('');
  });

  it('informa rechazo de enlace de restablecimiento', async () => {
    window.history.replaceState(null, '', '/restablecer-password#token=caducado'); mocks.request.mockRejectedValueOnce(new ApiError(400));
    show(<ResetPasswordPage />);
    fireEvent.change(await screen.findByLabelText('Nueva contraseña'), { target: { value: '12345678' } });
    fireEvent.click(screen.getByRole('button', { name: 'Restablecer contraseña' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/venció/i);
    expect(mocks.request).toHaveBeenCalledTimes(1);
  });

  it('rechaza contraseñas demasiado cortas antes de enviar', async () => {
    window.history.replaceState(null, '', '/restablecer-password#token=valido');
    show(<ResetPasswordPage />);
    const field = await screen.findByLabelText('Nueva contraseña');
    fireEvent.change(field, { target: { value: 'corta' } });
    expect(field).toHaveAttribute('minlength', '8');
    fireEvent.submit(field.closest('form')!);
    expect(mocks.request).not.toHaveBeenCalled();
  });

  it('envía solicitud de recuperación y muestra respuesta genérica', async () => {
    mocks.request.mockResolvedValueOnce({ mensaje: 'Si corresponde, recibirás un correo' });
    show(<EmailRequestPage mode="recover" />);
    fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: 'ana@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: /enviar enlace/i }));
    await waitFor(() => expect(mocks.request).toHaveBeenCalledWith('/auth/recuperar-password', { method: 'POST', body: { email: 'ana@example.com' } }));
    expect(await screen.findByText(/si corresponde/i)).toBeInTheDocument();
  });

  it('el reenvío usa mensaje genérico y respeta límites', async () => {
    mocks.request.mockRejectedValueOnce(new ApiError(429)); show(<EmailRequestPage mode="resend" />);
    fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: 'ana@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: /solicitar enlace/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/demasiados intentos/i);
    expect(mocks.request).toHaveBeenCalledWith('/auth/reenviar-verificacion', { method: 'POST', body: { email: 'ana@example.com' } });
  });

  it('muestra respuesta genérica después de reenviar', async () => {
    mocks.request.mockResolvedValueOnce({ mensaje: 'Si corresponde, recibirás un correo' }); show(<EmailRequestPage mode="resend" />);
    fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: 'ana@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: /solicitar enlace/i }));
    expect(await screen.findByText(/si corresponde/i)).toBeInTheDocument();
  });

  it('informa fallo de recuperación sin revelar cuentas', async () => {
    mocks.request.mockRejectedValueOnce(new Error('red')); show(<EmailRequestPage mode="recover" />);
    fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: 'ana@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: /enviar enlace/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/no pudimos continuar/i);
    expect(mocks.request).toHaveBeenCalledTimes(1);
  });
});
