export function formatClinicTime(instant: string, zone: string): string {
  return new Intl.DateTimeFormat('es-AR', { timeZone: zone, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(instant));
}
export function formatClinicDate(instant: string, zone: string): string {
  return new Intl.DateTimeFormat('es-AR', { timeZone: zone, day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(instant));
}
