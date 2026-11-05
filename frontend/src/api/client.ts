export class ApiError extends Error {
  constructor(public readonly status: number, public readonly invalidFields: string[] = []) {
    super(`Error HTTP ${status}`);
    this.name = 'ApiError';
  }
}

export type RequestOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  body?: unknown;
  token?: string;
  signal?: AbortSignal;
  timeoutMs?: number;
  onWait?: () => void;
};

const knownFields = new Set(['nombre', 'apellido', 'email', 'telefono', 'dni', 'nombre_usuario',
  'password', 'password_actual', 'password_nueva', 'obra_social', 'acepta_aviso_privacidad',
  'aviso_privacidad_version', 'identificador', 'token']);

export async function request<T = unknown>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers['Content-Type'] = 'application/json';
  if (options.token) headers.Authorization = `Bearer ${options.token}`;
  const method = options.method ?? 'GET';
  const maxAttempts = method === 'GET' ? 3 : 1;
  let response: Response | undefined;
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const controller = new AbortController();
    const abort = () => controller.abort();
    options.signal?.addEventListener('abort', abort, { once: true });
    if (options.signal?.aborted) controller.abort();
    const timer = setTimeout(() => { options.onWait?.(); controller.abort(); }, options.timeoutMs ?? 8000);
    try {
      response = await fetch(`/api/v1${path}`, {
        method, credentials: 'include', headers,
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
        signal: controller.signal,
      });
      if (![502, 503, 504].includes(response.status) || attempt === maxAttempts - 1) break;
      options.onWait?.();
    } catch (error) {
      if (options.signal?.aborted || attempt === maxAttempts - 1) throw error;
      options.onWait?.();
    } finally {
      clearTimeout(timer);
      options.signal?.removeEventListener('abort', abort);
    }
  }
  if (!response) throw new Error('Servicio no disponible');
  if (!response.ok) {
    const fields: string[] = [];
    if (response.status === 422) {
      const payload: unknown = await response.json().catch(() => undefined);
      if (payload && typeof payload === 'object' && 'detail' in payload && Array.isArray(payload.detail)) {
        for (const item of payload.detail as unknown[]) {
          if (item && typeof item === 'object' && 'loc' in item && Array.isArray(item.loc)) {
            const field: unknown = item.loc.at(-1);
            if (typeof field === 'string' && knownFields.has(field)) fields.push(field);
          }
        }
      }
    }
    throw new ApiError(response.status, fields);
  }
  if (response.status === 204) return undefined as T;
  return await response.json() as T;
}
