import { expect, it } from 'vitest';
import { displayClinicTime } from './time';

it('muestra fecha y hora en la zona del consultorio', () => {
  expect(displayClinicTime('2026-11-06T12:00:00Z', 'America/Argentina/Buenos_Aires')).toContain('09:00');
  expect(displayClinicTime('2026-11-06T12:00:00Z', 'UTC')).toContain('12:00');
});
it('mantiene la hora original cuando falta zona o fecha válida', () => {
  expect(displayClinicTime('fecha', 'UTC')).toBe('fecha');
  expect(displayClinicTime('2026-11-06T12:00:00Z', null)).toBe('2026-11-06T12:00:00Z');
});
