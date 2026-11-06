import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { PageTemplate } from '../components/ui';
import { useSession } from './provider';
import type { Role } from './session';

export function Guard({ children, roles }: { children: ReactNode; roles?: Role[] }) {
  const { state } = useSession();
  if (state.loading) return <main><p role="status">Estamos verificando tu sesión. Esperá un momento.</p></main>;
  if (!state.profile) return <Navigate to="/ingresar" replace />;
  if (roles && !roles.includes(state.profile.rol)) return <PageTemplate title="Acceso restringido"><p>No tenés permiso para ver esta sección.</p></PageTemplate>;
  return <>{children}</>;
}
