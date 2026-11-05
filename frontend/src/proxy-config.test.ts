import { describe, expect, it } from 'vitest';
import config, { proxyTarget } from '../vite.config';

describe('destino del proxy de desarrollo', () => {
  it('usa localhost cuando no se configura un destino', () => {
    expect(proxyTarget({})).toBe('http://localhost:8000');
  });
  it('usa el destino de Compose para enrutar /api', () => {
    expect(proxyTarget({ VITE_DEV_PROXY_TARGET: 'http://api:8000' })).toBe('http://api:8000');
    expect(config.server?.proxy).toHaveProperty('/api');
  });
  it('no expone las variables de proxy al código del navegador', () => {
    expect(config.envPrefix).toBe('PUBLIC_');
  });
});
