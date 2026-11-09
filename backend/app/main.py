import logging
import asyncio
from pathlib import Path
from contextlib import suppress
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.agenda import router as agenda_router
from app.api.v1.routers.cuentas import router as cuentas_router
from app.api.v1.routers.consultorio import router as consultorio_router
from app.api.v1.routers.health import router as health_router
from app.api.v1.routers.prestaciones import router as prestaciones_router
from app.api.v1.routers.personal import router as personal_router
from app.api.v1.routers.turnos import router as turnos_router
from app.api.v1.routers.confirmacion_turno import router as confirmacion_turno_router
from app.api.v1.routers.agenda_turnos import router as agenda_turnos_router
from app.api.v1.routers.vinculacion import router as vinculacion_router
from app.api.v1.routers.pacientes import router as pacientes_router
from app.api.v1.routers.reactivacion import router as reactivacion_router
from app.api.v1.routers.publico import router as publico_router
from app.api.v1.routers.barrido import router as barrido_router
from app.api.v1.routers.notificaciones import router as notificaciones_router
from app.api.v1.routers.indicadores import router as indicadores_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.application.errors_turnos import RechazoDeTurno
from app.application.errors_pacientes import RechazoPaciente

SPA_DIR = Path(__file__).resolve().parent.parent / 'static'


def create_app(settings: Settings | None = None) -> FastAPI:
    configured = settings if settings is not None else get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        tarea = None
        if configured.sweep_in_process_enabled:
            from app.domain.ports.reloj import RelojSistema
            from app.infrastructure.barrido import componer_barrido
            from app.infrastructure.planificador import BucleBarrido
            planificador = componer_barrido(app, RelojSistema(), configured)
            tarea = asyncio.create_task(BucleBarrido(planificador,
                configured.consultorio_activo_id, configured.sweeper_interval_seconds).ejecutar())
            app.state.sweep_task = tarea
        try:
            yield
        finally:
            if tarea is not None:
                tarea.cancel()
                with suppress(asyncio.CancelledError):
                    await tarea
            if getattr(app.state, "sweep_owns_engine", False):
                await app.state.engine.dispose()

    app = FastAPI(title='Sistema de Turnos y Agenda Odontológica', lifespan=lifespan,
                  docs_url='/docs' if configured.openapi_docs_enabled else None,
                  redoc_url='/redoc' if configured.openapi_docs_enabled else None,
                  openapi_url='/openapi.json' if configured.openapi_docs_enabled else None)

    @app.exception_handler(RechazoDeTurno)
    async def rechazo_turno(request: Request, error: RechazoDeTurno) -> JSONResponse:
        return JSONResponse(status_code=error.codigo, content={"detail": error.motivo})

    @app.exception_handler(RechazoPaciente)
    async def rechazo_paciente(request: Request, error: RechazoPaciente) -> JSONResponse:
        return JSONResponse(status_code=error.codigo, content={"detail": error.motivo})

    @app.exception_handler(RequestValidationError)
    async def validacion_sin_datos_privados(request: Request, error: RequestValidationError) -> JSONResponse:
        # Pydantic's hide_input_in_errors affects text rendering, not FastAPI's
        # default errors() response. Never echo request bodies or error context.
        detalles = [{clave: detalle[clave] for clave in ('loc', 'msg', 'type')}
                    for detalle in error.errors()]
        for detalle in detalles:
            if detalle['type'] == 'extra_forbidden':
                detalle['loc'] = (*detalle['loc'][:-1], 'campo_no_permitido')
        return JSONResponse(status_code=422, content={'detail': detalles})

    app.state.settings = configured
    configure_logging(configured)
    logger = logging.getLogger('tpi.api')
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(cuentas_router)
    app.include_router(agenda_router)
    app.include_router(personal_router)
    app.include_router(consultorio_router)
    app.include_router(prestaciones_router)
    app.include_router(turnos_router)
    app.include_router(confirmacion_turno_router)
    app.include_router(agenda_turnos_router)
    app.include_router(vinculacion_router)
    app.include_router(pacientes_router)
    app.include_router(reactivacion_router)
    app.include_router(publico_router)
    app.include_router(barrido_router)
    app.include_router(notificaciones_router)
    app.include_router(indicadores_router)

    @app.middleware('http')
    async def spa(request: Request, call_next):
        response = await call_next(request)
        if request.method != 'GET' or response.status_code != 404 or request.scope.get('route'):
            return response
        path = request.url.path.lstrip('/')
        if not configured.openapi_docs_enabled and path in {'docs', 'redoc', 'openapi.json'}:
            return response
        root = SPA_DIR.resolve()
        target = (root / path).resolve()
        if not target.is_relative_to(root) or path.split('/')[0] in {'api', 'internal'}:
            return response
        if target.is_file():
            return FileResponse(target)
        if path.split('/')[0] == 'assets' or Path(path).suffix:
            return response
        index = root / 'index.html'
        if not index.is_file():
            return response
        return FileResponse(index)

    app.add_middleware(RequestIdMiddleware, logger=logger)
    return app
