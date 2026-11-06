import { ApiError, request, type RequestOptions } from '../api/client';

export type Role = 'paciente' | 'recepcion' | 'profesional' | 'administrador' | 'administrativo';
export type Profile = { id: number; consultorio_id: number; nombre_usuario: string; email: string; rol: Role; email_verificado: boolean };
export type SessionState = { profile: Profile | null; loading: boolean; logoutUnconfirmed?: boolean };

export class Session {
  private token: string | null = null;
  private epoch = 0;
  private refreshing: Promise<string | null> | null = null;
  private restoring: Promise<void> | null = null;
  private loggingIn: Promise<void> | null = null;
  private loggingOut: Promise<void> | null = null;
  private state: SessionState = { profile: null, loading: true };
  private listeners = new Set<() => void>();
  getSnapshot = (): SessionState => this.state;
  subscribe = (listener: () => void): (() => void) => { this.listeners.add(listener); return () => this.listeners.delete(listener); };
  private update(state: SessionState): void { this.state = state; this.listeners.forEach(listener => listener()); }

  login(identificador: string, password: string): Promise<void> {
    const running = this.performLogin(identificador, password)
      .finally(() => { if (this.loggingIn === running) this.loggingIn = null; });
    this.loggingIn = running;
    return running;
  }

  private async performLogin(identificador: string, password: string): Promise<void> {
    const epoch = ++this.epoch;
    this.token = null;
    this.update({ profile: null, loading: false });
    try {
      if (this.loggingOut) await this.loggingOut.catch(() => undefined);
      if (this.refreshing) await this.refreshing.catch(() => null);
      if (epoch !== this.epoch) return;
      const result = await request<{ access_token: string }>('/auth/login', { method: 'POST', body: { identificador, password } });
      if (epoch !== this.epoch) return;
      this.token = result.access_token;
      const profile = await request<Profile>('/auth/me', { token: result.access_token });
      if (epoch !== this.epoch) return;
      this.update({ profile, loading: false });
    } catch (error) {
      if (epoch === this.epoch) {
        this.token = null;
        this.update({ profile: null, loading: false });
      }
      throw error;
    }
  }
  logout(): Promise<void> {
    if (this.loggingOut) return this.loggingOut;
    this.epoch++;
    this.token = null;
    this.update({ profile: null, loading: false });
    const pendingLogin = this.loggingIn;
    const pendingRefresh = this.refreshing;
    const running = (async () => {
      if (pendingLogin) await pendingLogin.catch(() => undefined);
      if (pendingRefresh) await pendingRefresh.catch(() => null);
      try {
        await request('/auth/logout', { method: 'POST' });
      } catch (error) {
        this.update({ ...this.state, logoutUnconfirmed: true });
        throw error;
      }
    })().finally(() => { if (this.loggingOut === running) this.loggingOut = null; });
    this.loggingOut = running;
    return running;
  }

  private refresh(): Promise<string | null> {
    if (this.refreshing) return this.refreshing;
    const epoch = this.epoch;
    const running = request<{ access_token: string }>('/auth/refresh', { method: 'POST' })
      .then(result => {
        if (this.epoch !== epoch) return null;
        this.token = result.access_token;
        return result.access_token;
      })
      .finally(() => { if (this.refreshing === running) this.refreshing = null; });
    this.refreshing = running;
    return running;
  }

  restore(): Promise<void> {
    if (this.restoring) return this.restoring;
    const epoch = this.epoch;
    const running = (async () => {
      try {
        const token = await this.refresh();
        if (!token || this.epoch !== epoch) return;
        const profile = await request<Profile>('/auth/me', { token });
        if (this.epoch === epoch) this.update({ profile, loading: false });
      } catch {
        if (this.epoch === epoch) { this.token = null; this.update({ profile: null, loading: false }); }
      }
    })().finally(() => { if (this.restoring === running) this.restoring = null; });
    this.restoring = running;
    return running;
  }

  async request<T = unknown>(path: string, options: Omit<RequestOptions, 'token'> = {}): Promise<T> {
    const previous = this.token;
    const epoch = this.epoch;
    if (!previous) throw new ApiError(401);
    try {
      return await request<T>(path, { ...options, token: previous });
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401 || epoch !== this.epoch) throw error;
      try {
        const token = this.token !== previous ? this.token : await this.refresh();
        if (!token || epoch !== this.epoch) throw new ApiError(401);
        return await request<T>(path, { ...options, token });
      } catch (retryError) {
        if (epoch === this.epoch && retryError instanceof ApiError && retryError.status === 401) {
          this.token = null;
          this.update({ profile: null, loading: false });
        }
        throw retryError;
      }
    }
  }
}
