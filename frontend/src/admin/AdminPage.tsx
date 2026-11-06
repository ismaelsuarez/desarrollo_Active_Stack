import { Personal } from './Personal';
import { Profesionales } from './Profesionales';
import { Horarios } from './Horarios';
import { Bloqueos } from './Bloqueos';
import { Prestaciones, Parametros } from './Catalog';
import './admin.css';

export function AdminPage() {
  return <main className="admin-page"><p className="admin-eyebrow">Administración / Configuración</p><h1>Configuración del consultorio</h1><p>Organizá el equipo, la agenda y las reglas de atención desde un mismo lugar.</p>
    <nav className="admin-tabs" aria-label="Secciones de configuración"><a href="#personal">Personal</a><a href="#profesionales">Profesionales y boxes</a><a href="#horarios">Horarios</a><a href="#bloqueos">Bloqueos</a><a href="#prestaciones">Prestaciones</a><a href="#parametros">Parámetros</a></nav>
    <div id="personal" className="admin-section"><Personal /></div><div id="profesionales" className="admin-section"><Profesionales /></div><div id="horarios" className="admin-section"><Horarios /></div><div id="bloqueos" className="admin-section"><Bloqueos /></div><div id="prestaciones" className="admin-section"><Prestaciones /></div><div id="parametros" className="admin-section"><Parametros /></div>
  </main>;
}
