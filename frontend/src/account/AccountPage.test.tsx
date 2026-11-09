import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import { AccountPage } from './AccountPage';

const mocks = vi.hoisted(() => ({ request: vi.fn(), role: 'paciente' }));
vi.mock('../auth/provider', () => ({ useSession: () => ({
  session: { request: mocks.request },
  state: { loading: false, profile: { id: 1, email: 'ana@example.com', rol: mocks.role } },
}) }));

beforeEach(() => { mocks.request.mockReset(); mocks.role = 'paciente'; });

describe('cuenta autenticada', () => {
  it('muestra orientación de seguridad al equipo', () => {
    mocks.role = 'administrador'; render(<AccountPage />);
    expect(screen.getByRole('heading', {name: 'Seguridad de tu cuenta'})).toBeInTheDocument();
  });
  it('cambia contraseña con la actual y la nueva', async () => {
    mocks.request.mockResolvedValueOnce({ mensaje: 'Contraseña actualizada' });
    render(<AccountPage />);
    fireEvent.change(screen.getByLabelText('Contraseña actual'), { target: { value: 'actual-segura' } });
    fireEvent.change(screen.getByLabelText('Contraseña nueva'), { target: { value: 'nueva-segura' } });
    fireEvent.change(screen.getByLabelText('Confirmar nueva contraseña'), { target: { value: 'nueva-segura' } });
    fireEvent.click(screen.getByRole('button', { name: 'Cambiar contraseña' }));
    expect(await screen.findByText('Contraseña actualizada')).toBeInTheDocument();
    expect(mocks.request).toHaveBeenCalledWith('/auth/cambiar-password', {
      method: 'PATCH', body: { password_actual: 'actual-segura', password_nueva: 'nueva-segura' },
    });
  });

  it.each(['paciente', 'recepcion', 'profesional', 'administrador', 'administrativo'])('informa contraseña actual incorrecta para %s', async role => {
    mocks.role = role;
    mocks.request.mockRejectedValueOnce(new ApiError(403));
    render(<AccountPage />);
    fireEvent.change(screen.getByLabelText('Contraseña actual'), { target: { value: 'incorrecta' } });
    fireEvent.change(screen.getByLabelText('Contraseña nueva'), { target: { value: 'nueva-segura' } });
    fireEvent.change(screen.getByLabelText('Confirmar nueva contraseña'), { target: { value: 'nueva-segura' } });
    fireEvent.click(screen.getByRole('button', { name: 'Cambiar contraseña' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/contraseña actual no es correcta/i);
    expect(screen.queryByText('Contraseña actualizada')).not.toBeInTheDocument();
  });

  it('informa validación de la contraseña nueva', async () => {
    mocks.request.mockRejectedValueOnce(new ApiError(422, ['password_nueva']));
    render(<AccountPage />);
    fireEvent.change(screen.getByLabelText('Contraseña actual'), { target: { value: 'actual' } });
    fireEvent.change(screen.getByLabelText('Contraseña nueva'), { target: { value: 'corta' } });
    fireEvent.change(screen.getByLabelText('Confirmar nueva contraseña'), { target: { value: 'corta' } });
    fireEvent.click(screen.getByRole('button', { name: 'Cambiar contraseña' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/revisá la contraseña nueva/i);
  });

  it('no envía si la confirmación no coincide', async () => {
    render(<AccountPage />);
    fireEvent.change(screen.getByLabelText('Contraseña actual'), { target: { value: 'actual' } });
    fireEvent.change(screen.getByLabelText('Contraseña nueva'), { target: { value: 'nueva-segura' } });
    fireEvent.change(screen.getByLabelText('Confirmar nueva contraseña'), { target: { value: 'diferente' } });
    fireEvent.click(screen.getByRole('button', { name: 'Cambiar contraseña' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/no coinciden/i);
    expect(mocks.request).not.toHaveBeenCalled();
  });

  it('permite al paciente actualizar el teléfono', async () => {
    mocks.request.mockResolvedValueOnce({ mensaje: 'Cuenta actualizada' });
    render(<AccountPage />);
    fireEvent.change(screen.getByLabelText('Teléfono'), { target: { value: '1123456789' } });
    fireEvent.click(screen.getByRole('button', { name: 'Guardar contacto' }));
    expect(await screen.findByText('Contacto actualizado.')).toBeInTheDocument();
    expect(mocks.request).toHaveBeenCalledWith('/auth/actualizar-cuenta', { method: 'PATCH', body: { telefono: '1123456789' } });
  });

  it.each([
    ['nuevo@example.com', /verificá nuevamente/i],
    ['ANA@example.com', /^Contacto actualizado\.$/],
  ])('actualiza email %s con mensaje según el cambio real', async (email, notice) => {
    mocks.request.mockResolvedValueOnce({ mensaje: 'Cuenta actualizada' });
    render(<AccountPage />);
    fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: email } });
    fireEvent.click(screen.getByRole('button', { name: 'Guardar contacto' }));
    expect(await screen.findByText(notice)).toBeInTheDocument();
    expect(mocks.request).toHaveBeenCalledWith('/auth/actualizar-cuenta', { method: 'PATCH', body: { email } });
  });

  it('informa conflicto de correo sin confirmar éxito', async () => {
    mocks.request.mockRejectedValueOnce(new ApiError(409));
    render(<AccountPage />);
    fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: 'ocupado@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: 'Guardar contacto' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/correo.*utilizado/i);
    expect(screen.queryByText(/contacto actualizado/i)).not.toBeInTheDocument();
  });

  it.each(['recepcion', 'profesional', 'administrador', 'administrativo'])('no ofrece editar contacto a %s', role => {
    mocks.role = role;
    render(<AccountPage />);
    expect(screen.queryByRole('button', { name: 'Guardar contacto' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cambiar contraseña' })).toBeInTheDocument();
  });
});
