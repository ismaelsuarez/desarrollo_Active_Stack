import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, request } from './client';

afterEach(() => vi.unstubAllGlobals());

describe('cliente HTTP', () => {
  it('conserva alternativas válidas de conflicto de horario sin guardar el resto del cuerpo', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: {
      motivo: 'horario ocupado', alternativas: [{ inicio: '2026-11-12T09:30:00-03:00', fin: '2026-11-12T10:00:00-03:00', secreto: 'privado' }], secreto: 'privado',
    } }), { status: 409 })));
    const error = await request('/turnos', { method: 'POST', body: {} }).catch((value: unknown) => value);
    expect(error).toMatchObject({ status: 409, bookingDetail: { kind: 'occupied', alternatives: [{ inicio: '2026-11-12T09:30:00-03:00', fin: '2026-11-12T10:00:00-03:00' }] } });
    expect(JSON.stringify(error)).not.toContain('privado');
  });
  it('descarta alternativas malformadas y reconoce una lista vacía', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: {
      motivo: 'horario ocupado', alternativas: [{ inicio: 'dato privado', fin: 'incorrecto' }, { inicio: '2026-11-12T09:30:00-03:00' }],
    } }), { status: 409 })));
    const error = await request('/turnos', { method: 'POST', body: {} }).catch((value: unknown) => value);
    expect(error).toMatchObject({ bookingDetail: { kind: 'occupied', alternatives: [] } });
    expect(JSON.stringify(error)).not.toContain('dato privado');
  });
  it('identifica el límite de turnos sin conservar texto arbitrario', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Máximo de 2 turnos futuros activos' }), { status: 409 })));
    const error = await request('/turnos', { method: 'POST', body: {} }).catch((value: unknown) => value);
    expect(error).toMatchObject({ bookingDetail: { kind: 'limit', maximum: 2 } });
  });
  it('identifica el rechazo fuera de plazo sin retener el teléfono del mensaje', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Fuera de plazo. Comuníquese con el consultorio: 12345678' }), { status: 403 })));
    const error = await request('/turnos/1', { method: 'PATCH', body: {} }).catch((value: unknown) => value);
    expect(error).toMatchObject({ bookingDetail: { kind: 'deadline' } });
    expect(JSON.stringify(error)).not.toContain('12345678');
  });
  it('no atribuye fuera de plazo a un 403 arbitrario', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'no permitido' }), { status: 403 })));
    const error = await request('/turnos/1', { method: 'PATCH', body: {} }).catch((value: unknown) => value);
    expect(error).toMatchObject({ status: 403, bookingDetail: undefined });
  });
  it('envía credenciales, autorización y cuerpo a la ruta relativa', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal('fetch', fetcher);
    await expect(request('/auth/login', { method: 'POST', body: { usuario: 'persona' }, token: 'access' })).resolves.toEqual({ ok: true });
    expect(fetcher).toHaveBeenCalledOnce();
    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe('/api/v1/auth/login');
    expect(init.credentials).toBe('include');
    expect(init.headers.Authorization).toBe('Bearer access');
    expect(JSON.parse(init.body)).toEqual({ usuario: 'persona' });
  });
  it('informa el código sin exponer respuestas potencialmente sensibles', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'secreto' }), { status: 403 })));
    await expect(request('/private')).rejects.toMatchObject({ status: 403 });
    await expect(request('/private')).rejects.toBeInstanceOf(ApiError);
  });
  it.each([401, 403, 404, 422, 429])('preserva estado %i sin incluir el cuerpo en el error', async status => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'secreto' }), { status })));
    const error = await request('/private').catch((value: unknown) => value);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status });
    expect(String(error)).not.toContain('secreto');
  });
  it('identifica los campos inválidos sin retener valores o mensajes del servidor', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: [
      { loc: ['body', 'email'], msg: 'dato privado', input: 'dato privado' },
      { loc: ['body', 'secreto'], msg: 'dato privado' },
    ] }), { status: 422 })));
    const error = await request('/auth/registro', { method: 'POST', body: {} }).catch((value: unknown) => value);
    expect(error).toMatchObject({ status: 422, invalidFields: ['email'] });
    expect(JSON.stringify(error)).not.toContain('dato privado');
  });
  it('reintenta una lectura transitoria e informa la espera', async () => {
    const fetcher = vi.fn().mockRejectedValueOnce(new TypeError('network')).mockResolvedValueOnce(new Response('{}', { status: 200 }));
    const waiting = vi.fn();
    vi.stubGlobal('fetch', fetcher);
    await request('/publico/aviso-privacidad', { onWait: waiting });
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(waiting).toHaveBeenCalled();
  });
  it('no repite una escritura de resultado incierto', async () => {
    const fetcher = vi.fn().mockRejectedValue(new TypeError('network'));
    vi.stubGlobal('fetch', fetcher);
    await expect(request('/auth/login', { method: 'POST', body: {} })).rejects.toThrow();
    expect(fetcher).toHaveBeenCalledOnce();
  });
  it('limita los intentos cuando el servicio no está disponible', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('{}', { status: 503 }));
    vi.stubGlobal('fetch', fetcher);
    await expect(request('/publico/aviso-privacidad')).rejects.toMatchObject({ status: 503 });
    expect(fetcher).toHaveBeenCalledTimes(3);
  });
  it('interrumpe una escritura al alcanzar el tiempo límite y no la reintenta', async () => {
    const fetcher = vi.fn().mockImplementation((_url, init: RequestInit) => new Promise((_resolve, reject) => {
      init.signal?.addEventListener('abort', () => reject(new DOMException('timeout', 'AbortError')));
    }));
    vi.stubGlobal('fetch', fetcher);
    await expect(request('/auth/login', { method: 'POST', body: {}, timeoutMs: 1 })).rejects.toThrow();
    expect(fetcher).toHaveBeenCalledOnce();
  });
});
