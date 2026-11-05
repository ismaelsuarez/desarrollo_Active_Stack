"""Una composición de barrido por aplicación, compartida por sus adaptadores."""
from app.core.config import Settings
from app.domain.ports.reloj import Reloj
from app.infrastructure.db.sesion import crear_engine, crear_fabrica_de_sesiones


def componer_barrido(app, reloj: Reloj, settings: Settings):
    if not hasattr(app.state, "barrido"):
        from app.application.services.notificaciones import DespacharNotificacion
        from app.application.use_cases.ejecutar_barrido import EjecutarBarrido
        from app.infrastructure.correo.smtp import EnviadorSMTP
        if not hasattr(app.state, "session_factory"):
            app.state.engine = crear_engine(settings.database_url.get_secret_value())
            app.state.session_factory = crear_fabrica_de_sesiones(app.state.engine)
            app.state.sweep_owns_engine = True
        sesiones = app.state.session_factory
        despacho = DespacharNotificacion(sesiones, reloj, EnviadorSMTP(settings), settings)
        app.state.barrido = EjecutarBarrido(sesiones, reloj, despacho, settings)
    return app.state.barrido
