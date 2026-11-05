import { afterEach, describe, expect, it, vi } from 'vitest';
import { Session } from './session';

afterEach(() => vi.unstubAllGlobals());
const profile = { id: 1, consultorio_id: 1, nombre_usuario: 'maria', email: 'm@example.com', rol: 'paciente', email_verificado: true };
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status });

describe('sesión', () => {
  it('inicia sesión y obtiene perfil sin persistir el token', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(json({ access_token: 'access' })).mockResolvedValueOnce(json(profile));
    vi.stubGlobal('fetch', fetcher);
    const session = new Session();
    await session.login('maria', 'clave');
    expect(session.getSnapshot().profile).toEqual(profile);
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(fetcher.mock.calls[1][1].headers.Authorization).toBe('Bearer access');
  });
  it('limpia la sesión incluso si falla el cierre remoto', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(json({ access_token: 'access' })).mockResolvedValueOnce(json(profile)).mockRejectedValueOnce(new Error('network'));
    vi.stubGlobal('fetch', fetcher);
    const session = new Session();
    await session.login('maria', 'clave');
    await expect(session.logout()).rejects.toThrow();
    expect(session.getSnapshot().profile).toBeNull();
    expect(session.getSnapshot().logoutUnconfirmed).toBe(true);
  });
  it('restaura una sesión válida mediante una sola renovación concurrente', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(json({ access_token: 'rotated' })).mockResolvedValueOnce(json(profile));
    vi.stubGlobal('fetch', fetcher);
    const session = new Session();
    await Promise.all([session.restore(), session.restore()]);
    expect(fetcher.mock.calls.filter(([url]) => url === '/api/v1/auth/refresh')).toHaveLength(1);
    expect(session.getSnapshot().profile).toEqual(profile);
  });
  it('termina la carga sin sesión cuando no hay cookie válida', async () => {
    const fetcher = vi.fn().mockResolvedValue(json({}, 401));
    vi.stubGlobal('fetch', fetcher);
    const session = new Session();
    await session.restore();
    expect(session.getSnapshot()).toEqual({ profile: null, loading: false });
    expect(fetcher).toHaveBeenCalledOnce();
  });
  it('mantiene la sesión cerrada cuando llega una renovación tardía', async () => {
    let resolveRefresh!: (response: Response) => void;
    const fetcher = vi.fn().mockImplementation((url: string) => url.endsWith('/refresh')
      ? new Promise<Response>(resolve => { resolveRefresh = resolve; }) : Promise.resolve(json({ mensaje: 'ok' })));
    vi.stubGlobal('fetch', fetcher);
    const session = new Session();
    const pending = session.restore();
    const closing = session.logout();
    resolveRefresh(json({ access_token: 'late' }));
    await Promise.all([pending, closing]);
    expect(session.getSnapshot().profile).toBeNull();
    expect(fetcher.mock.calls.filter(([url]) => url === '/api/v1/auth/me')).toHaveLength(0);
  });
  it('renueva una vez ante 401 concurrentes y reintenta cada pedido una vez', async () => {
    let oldCalls = 0;
    const fetcher = vi.fn().mockImplementation((url: string, init: RequestInit) => {
      if (url.endsWith('/login')) return Promise.resolve(json({ access_token: 'old' }));
      if (url.endsWith('/me')) return Promise.resolve(json(profile));
      if (url.endsWith('/refresh')) return Promise.resolve(json({ access_token: 'new' }));
      const headers = init.headers as Record<string, string>;
      if (headers.Authorization === 'Bearer old') { oldCalls++; return Promise.resolve(json({}, 401)); }
      return Promise.resolve(json({ ok: true }));
    });
    vi.stubGlobal('fetch', fetcher);
    const session = new Session();
    await session.login('maria', 'clave');
    await Promise.all([session.request('/uno'), session.request('/dos')]);
    expect(oldCalls).toBe(2);
    expect(fetcher.mock.calls.filter(([url]) => url.endsWith('/refresh'))).toHaveLength(1);
    expect(fetcher.mock.calls.filter(([url]) => url.endsWith('/uno') || url.endsWith('/dos'))).toHaveLength(4);
  });
  it('limpia la sesión si la renovación es rechazada y no entra en bucle', async () => {
    const fetcher = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith('/login')) return Promise.resolve(json({ access_token: 'old' }));
      if (url.endsWith('/me')) return Promise.resolve(json(profile));
      return Promise.resolve(json({}, 401));
    });
    vi.stubGlobal('fetch', fetcher);
    const session = new Session();
    await session.login('maria', 'clave');
    await expect(session.request('/privado')).rejects.toMatchObject({ status: 401 });
    expect(session.getSnapshot().profile).toBeNull();
    expect(fetcher.mock.calls.filter(([url]) => url.endsWith('/refresh'))).toHaveLength(1);
  });
  it('deja la sesión cerrada cuando falla el ingreso', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({}, 401)));
    const session = new Session();
    await expect(session.login('maria', 'incorrecta')).rejects.toMatchObject({ status: 401 });
    expect(session.getSnapshot()).toEqual({ profile: null, loading: false });
  });
  it('no reactiva la sesión si el ingreso responde después del cierre', async () => {
    let resolveLogin!: (response: Response) => void;
    const fetcher = vi.fn().mockImplementation((url: string) => url.endsWith('/login')
      ? new Promise<Response>(resolve => { resolveLogin = resolve; }) : Promise.resolve(json({ mensaje: 'ok' })));
    vi.stubGlobal('fetch', fetcher);
    const session = new Session();
    const login = session.login('maria', 'clave');
    const logout = session.logout();
    expect(fetcher.mock.calls.map(([url]) => url)).toEqual(['/api/v1/auth/login']);
    resolveLogin(json({ access_token: 'late' }));
    await Promise.all([login, logout]);
    expect(session.getSnapshot().profile).toBeNull();
    expect(fetcher.mock.calls.map(([url]) => url)).toEqual(['/api/v1/auth/login', '/api/v1/auth/logout']);
  });
  it('espera una renovación en curso antes de enviar nuevas credenciales', async () => {
    let resolveRefresh!: (response: Response) => void;
    const fetcher = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith('/refresh')) return new Promise<Response>(resolve => { resolveRefresh = resolve; });
      if (url.endsWith('/login')) return Promise.resolve(json({ access_token: 'new' }));
      return Promise.resolve(json(profile));
    });
    vi.stubGlobal('fetch', fetcher);
    const session = new Session();
    const restoring = session.restore();
    const login = session.login('maria', 'clave');
    expect(fetcher).toHaveBeenCalledTimes(1);
    resolveRefresh(json({ access_token: 'old' }));
    await Promise.all([restoring, login]);
    expect(session.getSnapshot().profile).toEqual(profile);
    expect(fetcher.mock.calls.map(([url]) => url)).toEqual(['/api/v1/auth/refresh', '/api/v1/auth/login', '/api/v1/auth/me']);
  });
  it('espera la revocación pendiente antes de iniciar una nueva sesión', async () => {
    let resolveLogout!: (response: Response) => void;
    const fetcher = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith('/logout')) return new Promise<Response>(resolve => { resolveLogout = resolve; });
      if (url.endsWith('/login')) return Promise.resolve(json({ access_token: 'new' }));
      return Promise.resolve(json(profile));
    });
    vi.stubGlobal('fetch', fetcher);
    const session = new Session();
    const closing = session.logout();
    const login = session.login('maria', 'clave');
    expect(fetcher).toHaveBeenCalledTimes(1);
    resolveLogout(json({ mensaje: 'ok' }));
    await Promise.all([closing, login]);
    expect(session.getSnapshot().profile).toEqual(profile);
    expect(fetcher.mock.calls.map(([url]) => url)).toEqual(['/api/v1/auth/logout', '/api/v1/auth/login', '/api/v1/auth/me']);
  });
});
