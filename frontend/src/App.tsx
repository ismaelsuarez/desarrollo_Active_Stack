import { BrowserRouter, Link } from 'react-router-dom';
import { SessionProvider } from './auth/provider';
import { AppRoutes } from './shell/routes';
import './app.css';

export default function App() {
  return <BrowserRouter><SessionProvider>
    <header className="app-header"><Link to="/" className="app-brand"><span className="app-logo" aria-hidden="true">☰</span><span className="app-logo-label">LOGO<br />PROVISIONAL</span><h1>Sistema de Turnos y Agenda Odontológica</h1></Link></header>
    <AppRoutes />
  </SessionProvider></BrowserRouter>;
}
