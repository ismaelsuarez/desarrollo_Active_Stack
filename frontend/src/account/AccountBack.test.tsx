import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { expect, it } from 'vitest';
import { AccountBack } from './AccountBack';

it('vuelve a la pantalla interna desde la que se abrió la cuenta', () => {
  render(<MemoryRouter initialEntries={[{pathname: '/cuenta', state: {returnTo: '/agenda'}}]}><Routes><Route path="/cuenta" element={<AccountBack role="recepcion" />} /><Route path="/agenda" element={<p>Agenda anterior</p>} /></Routes></MemoryRouter>);
  fireEvent.click(screen.getByRole('link', {name: /volver/i}));
  expect(screen.getByText('Agenda anterior')).toBeInTheDocument();
});

it('usa el panel del rol si se abre directamente o recibe un destino externo', () => {
  for (const state of [null, {returnTo: '//externo.test'}]) {
    const view = render(<MemoryRouter initialEntries={[{pathname: '/cuenta', state}]}><Routes><Route path="/cuenta" element={<AccountBack role="administrador" />} /><Route path="/administrador" element={<p>Panel administrador</p>} /></Routes></MemoryRouter>);
    fireEvent.click(screen.getByRole('link', {name: /volver/i}));
    expect(screen.getByText('Panel administrador')).toBeInTheDocument(); view.unmount();
  }
});

it('conserva el contexto interno cuando incluye parámetros', () => {
  function Previous() { return <p>{useLocation().search}</p>; }
  render(<MemoryRouter initialEntries={[{pathname: '/cuenta', state: {returnTo: '/agenda?turno=42'}}]}><Routes><Route path="/cuenta" element={<AccountBack role="recepcion" />} /><Route path="/agenda" element={<Previous />} /></Routes></MemoryRouter>);
  fireEvent.click(screen.getByRole('link', {name: /volver/i}));
  expect(screen.getByText('?turno=42')).toBeInTheDocument();
});
