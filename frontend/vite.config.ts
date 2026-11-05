import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { loadEnv } from 'vite';

export function proxyTarget(env: Record<string, string | undefined>): string {
  return env.VITE_DEV_PROXY_TARGET || 'http://localhost:8000';
}

export default defineConfig({
  plugins: [react()],
  envPrefix: 'PUBLIC_',
  server: {
    proxy: {
      '/api': { target: proxyTarget({ ...loadEnv(process.env.NODE_ENV || 'development', process.cwd(), ''), ...process.env }), changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
  },
});
