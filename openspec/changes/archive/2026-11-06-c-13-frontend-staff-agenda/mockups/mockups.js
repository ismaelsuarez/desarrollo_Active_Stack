(() => {
  const views = [...document.querySelectorAll('[data-view]')];
  const titles = {agenda:'Agenda',detalle:'Detalle del turno',nuevo:'Dar turno',conflicto:'Horario ocupado',autorizar:'Autorizar sobreturno',sobreturno:'Sobreturno',mover:'Mover turno',cancelar:'Cancelar turno',pacientes:'Pacientes','ficha-nueva':'Crear ficha',ficha:'Ficha de paciente',desvincular:'Desvincular',reactivar:'Reactivar',solicitudes:'Solicitudes',resolver:'Resolver solicitud',profesional:'Mi agenda','profesional-turno':'Turno','ficha-profesional':'Ficha',responder:'Responder aviso'};
  function render() {
    const requested = location.hash.slice(1) || 'agenda';
    const current = views.some(view => view.dataset.view === requested) ? requested : 'agenda';
    views.forEach(view => { view.hidden = view.dataset.view !== current; });
    document.getElementById('crumb').textContent = titles[current];
    document.querySelectorAll('nav a').forEach(link => {
      const section = ['pacientes','ficha','ficha-nueva','ficha-profesional','desvincular','reactivar'].includes(current) ? 'pacientes' : ['solicitudes','resolver'].includes(current) ? 'solicitudes' : ['profesional','profesional-turno','responder'].includes(current) ? 'profesional' : 'agenda';
      if (link.hash === '#' + section) link.setAttribute('aria-current','page'); else link.removeAttribute('aria-current');
    });
    window.scrollTo(0, 0);
  }
  window.addEventListener('hashchange', render); render();
})();
