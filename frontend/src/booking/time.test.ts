import { describe, expect, it } from 'vitest';
import { formatClinicDate, formatClinicTime } from './time';

describe('hora del consultorio', () => {
  it('formatea el instante en la zona del consultorio y no en la del dispositivo', () => {
    expect(formatClinicTime('2026-11-12T13:30:00Z', 'America/Argentina/Buenos_Aires')).toBe('10:30');
  });
  it('respeta cambios de día y la zona elegida', () => {
    expect(formatClinicTime('2026-11-12T01:15:00Z', 'America/Argentina/Buenos_Aires')).toBe('22:15');
    expect(formatClinicTime('2026-11-12T01:15:00Z', 'UTC')).toBe('01:15');
    expect(formatClinicDate('2026-11-12T01:15:00Z', 'America/Argentina/Buenos_Aires')).toBe('11/11/2026');
  });
});
