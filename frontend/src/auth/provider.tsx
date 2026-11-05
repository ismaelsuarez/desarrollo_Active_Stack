import { createContext, useContext, useEffect, useState, useSyncExternalStore, type ReactNode } from 'react';
import { Session, type SessionState } from './session';

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session] = useState(() => new Session());
  useEffect(() => { void session.restore(); }, [session]);
  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}

export function useSession(): { session: Session; state: SessionState } {
  const session = useContext(SessionContext);
  if (!session) throw new Error('SessionProvider requerido');
  const state = useSyncExternalStore(session.subscribe, session.getSnapshot, session.getSnapshot);
  return { session, state };
}
