import { BrowserRouter, Link, useLocation } from 'react-router-dom';
import { SessionProvider, useSession } from './auth/provider';
import { AppRoutes } from './shell/routes';
import './app.css';

function AppHeader() {
  const { pathname } = useLocation(); const { state } = useSession();
  if (pathname === '/' && !state.profile) return null;
  return <header className="app-header"><Link to="/" className="app-brand"><span className="app-logo" aria-hidden="true">☰</span><span className="app-logo-label">LOGO<br />PROVISIONAL</span><h1>Sistema de Turnos y Agenda Odontológica</h1></Link></header>;
}

export default function App() {
  return <BrowserRouter><SessionProvider>
    <AppHeader />
    <AppRoutes />
  </SessionProvider></BrowserRouter>;
}
