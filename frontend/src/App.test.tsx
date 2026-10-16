import { render, screen } from '@testing-library/react';
import { Fragment, StrictMode } from 'react';
import { describe, expect, it } from 'vitest';
import App from './App';

describe('Application heading', () => {
  for (const Wrapper of [Fragment, StrictMode]) {
    it(`shows the system name with ${Wrapper === StrictMode ? 'strict' : 'normal'} rendering`, () => {
      render(<Wrapper><App /></Wrapper>);
      expect(screen.getByRole('heading', { level: 1, name: 'Sistema de Turnos y Agenda Odontológica' })).toBeInTheDocument();
    });
  }
});
