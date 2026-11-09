import { render, screen } from '@testing-library/react';
import { Fragment, StrictMode } from 'react';
import { describe, expect, it } from 'vitest';
import App from './App';

describe('Application session restoration', () => {
  for (const Wrapper of [Fragment, StrictMode]) {
    it(`announces session restoration with ${Wrapper === StrictMode ? 'strict' : 'normal'} rendering`, () => {
      render(<Wrapper><App /></Wrapper>);
      expect(screen.getByRole('status')).toHaveTextContent('verificando tu sesión');
    });
  }
});
