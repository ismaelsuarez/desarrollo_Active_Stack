import { Link, useLocation } from 'react-router-dom';
import type { Role } from '../auth/session';

export function AccountBack({ role }: { role: Role }) {
  const { state } = useLocation();
  const candidate: unknown = state && typeof state === 'object' && 'returnTo' in state ? state.returnTo : null;
  const safe = typeof candidate === 'string' && /^\/(?!\/)[a-z0-9/-]+(?:\?[^#\\]*)?$/i.test(candidate) && candidate.split('?')[0] !== '/cuenta' ? candidate : `/${role}`;
  return <div className="account-back"><Link to={safe}>← Volver</Link></div>;
}
