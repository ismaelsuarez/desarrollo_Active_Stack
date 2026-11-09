import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, request } from '../api/client';
import { Notice, PageTemplate } from '../components/ui';
import { consumeFragment } from './tokenFragment';
import './public.css';
export function TokenActionPage({ action }: { action: 'verify' | 'confirm' }) {
  const pending = useRef<Promise<unknown> | null>(null);
  const [result, setResult] = useState<'loading' | 'success' | 'error' | 'unavailable'>('loading');
  useEffect(() => {
    if (!pending.current) {
      const token = consumeFragment();
      pending.current = token ? request(action === 'verify' ? '/auth/verificar-email' : '/turnos/confirmar-por-enlace', { method: 'POST', body: { token } }) : Promise.reject(new Error('Enlace ausente'));
    }
    let active = true;
    pending.current.then(() => { if (active) setResult('success'); }, error => { if (active) setResult(action === 'confirm' && error instanceof ApiError && error.status === 409 ? 'unavailable' : 'error'); });
    return () => { active = false; };
  }, [action]);
  const title = action === 'verify' ? 'Verificar correo' : 'Confirmar turno';
  return <PageTemplate title={title}><div className="public-card">{result === 'loading' ? <Notice>Procesando enlace…</Notice> : result === 'success' ? <Notice kind="success">{action === 'verify' ? 'Correo verificado' : 'Turno confirmado'}</Notice> : result === 'unavailable' ? <Notice kind="error">Este turno ya no se puede confirmar. <Link to="/reservar">Reservar de nuevo</Link></Notice> : <Notice kind="error">El enlace no es válido, venció o ya fue utilizado. Solicitá uno nuevo.</Notice>}<p><Link to="/ingresar">Ir a ingresar</Link></p></div></PageTemplate>;
}

