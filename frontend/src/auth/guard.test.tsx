import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Guard } from './guard';

const mockSession = vi.hoisted(() => ({ state: { loading: false, profile: null as null | { rol: string } } }));
vi.mock('./provider', () => ({ useSession: () => mockSession }));

function renderGuard() {
  return render(<MemoryRouter initialEntries={['/recepcion']}><Routes>
    <Route path="/ingresar" element={<p>Ingresar a la cuenta</p>} />
    <Route path="/recepcion" element={<Guard roles={['recepcion']}><p>Contenido privado</p></Guard>} />
  </Routes></MemoryRouter>);
}

describe('guarda de sesión y rol', () => {
  beforeEach(() => { mockSession.state = { loading: false, profile: null }; });
  it('redirige a ingreso sin mostrar contenido privado cuando no hay sesión', () => {
    renderGuard();
    expect(screen.getByText('Ingresar a la cuenta')).toBeInTheDocument();
    expect(screen.queryByText('Contenido privado')).not.toBeInTheDocument();
  });
  it('rechaza roles ajenos y permite el rol autorizado', () => {
    mockSession.state.profile = { rol: 'paciente' };
    const view = renderGuard();
    expect(screen.getByText(/no tenés permiso/i)).toBeInTheDocument();
    expect(screen.queryByText('Contenido privado')).not.toBeInTheDocument();
    view.unmount();
    mockSession.state.profile = { rol: 'recepcion' };
    renderGuard();
    expect(screen.getByText('Contenido privado')).toBeInTheDocument();
  });
  it('espera a la restauración sin mostrar contenido privado', () => {
    mockSession.state.loading = true;
    renderGuard();
    expect(screen.getByText(/verificando tu sesión/i)).toBeInTheDocument();
    expect(screen.queryByText('Contenido privado')).not.toBeInTheDocument();
  });
});
