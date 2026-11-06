import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { AdminPage } from './AdminPage';
vi.mock('./Personal', () => ({ Personal: () => <p>Personal cargado</p> }));
vi.mock('./Profesionales', () => ({ Profesionales: () => <p>Profesionales cargados</p> }));
vi.mock('./Horarios', () => ({ Horarios: () => <p>Horarios cargados</p> }));
vi.mock('./Bloqueos', () => ({ Bloqueos: () => <p>Bloqueos cargados</p> }));
vi.mock('./Catalog', () => ({ Prestaciones: () => <p>Prestaciones cargadas</p>, Parametros: () => <p>Parámetros cargados</p> }));
it('ofrece navegación a las seis secciones de configuración', () => {
  render(<AdminPage />);
  for (const [label, id] of [['Personal', 'personal'], ['Profesionales y boxes', 'profesionales'], ['Horarios', 'horarios'], ['Bloqueos', 'bloqueos'], ['Prestaciones', 'prestaciones'], ['Parámetros', 'parametros']]) {
    expect(screen.getByRole('link', { name: label })).toHaveAttribute('href', `#${id}`);
    expect(document.getElementById(id)).toBeInTheDocument();
  }
});
