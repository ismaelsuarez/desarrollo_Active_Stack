import { ApiError } from '../api/client';

export const failure = (error: unknown) => error instanceof ApiError && error.status === 429
  ? 'Demasiados intentos. Intentá más tarde.'
  : 'No pudimos continuar. Revisá los datos e intentá nuevamente.';
