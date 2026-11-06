import { useEffect, useState } from 'react';
import { request } from '../api/client';

export function displayClinicTime(value: string, zone: string | null): string {
  if (!zone || !Number.isFinite(Date.parse(value))) return value;
  try { return new Intl.DateTimeFormat('es-AR', { timeZone: zone, day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(value)); }
  catch { return value; }
}
export function useClinicZone(): string | null {
  const [zone, setZone] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    request<{ zona_horaria: string }>('/publico/consultorio').then(value => { if (active) setZone(value.zona_horaria); }).catch(() => {});
    return () => { active = false; };
  }, []);
  return zone;
}
