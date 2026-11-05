import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Button, Notice, PageTemplate, TextField } from './ui';

describe('componentes presentacionales', () => {
  it('invoca la acción del botón mediante su nombre accesible', () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Continuar</Button>);
    fireEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('no ejecuta acciones deshabilitadas', () => {
    const onClick = vi.fn();
    render(<Button disabled onClick={onClick}>Guardar</Button>);
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }));
    expect(onClick).not.toHaveBeenCalled();
  });

  it('asocia etiqueta y error con el campo', () => {
    render(<TextField label="Correo electrónico" name="email" error="Ingresá un correo válido" />);
    const field = screen.getByRole('textbox', { name: 'Correo electrónico' });
    expect(field).toHaveAttribute('aria-invalid', 'true');
    expect(field).toHaveAccessibleDescription('Ingresá un correo válido');
  });

  it('asocia ayuda con un campo sin error y permite editarlo', () => {
    const onChange = vi.fn();
    render(<TextField label="Nombre" name="nombre" hint="Como figura en tu DNI" onChange={onChange} />);
    const field = screen.getByRole('textbox', { name: 'Nombre' });
    expect(field).not.toHaveAttribute('aria-invalid');
    expect(field).toHaveAccessibleDescription('Como figura en tu DNI');
    fireEvent.change(field, { target: { value: 'Ana' } });
    expect(onChange).toHaveBeenCalledOnce();
  });

  it('conserva una descripción externa junto con el error', () => {
    render(<><p id="external">Dato obligatorio</p><TextField label="DNI" aria-describedby="external" error="Ingresá tu DNI" /></>);
    expect(screen.getByRole('textbox', { name: 'DNI' })).toHaveAccessibleDescription('Dato obligatorio Ingresá tu DNI');
  });

  it('presenta mensajes y contenido proporcionados por el contenedor', () => {
    render(<PageTemplate title="Tu cuenta"><Notice kind="error">No pudimos continuar.</Notice></PageTemplate>);
    expect(screen.getByRole('heading', { name: 'Tu cuenta' })).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('No pudimos continuar.');
  });

  it('presenta estado exitoso sin anunciarlo como error', () => {
    render(<PageTemplate title="Verificación" description="Seguimos con tu cuenta"><Notice kind="success">Correo verificado.</Notice></PageTemplate>);
    expect(screen.getByText('Seguimos con tu cuenta')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Correo verificado.');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
