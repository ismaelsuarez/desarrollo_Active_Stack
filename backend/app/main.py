import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.cuentas import router as cuentas_router
from app.api.v1.routers.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    configured = settings if settings is not None else get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield

    app = FastAPI(title='Sistema de Turnos y Agenda Odontológica', lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def validacion_sin_datos_privados(request: Request, error: RequestValidationError) -> JSONResponse:
        # Pydantic's hide_input_in_errors affects text rendering, not FastAPI's
        # default errors() response. Never echo request bodies or error context.
        detalles = [{clave: detalle[clave] for clave in ('loc', 'msg', 'type')}
                    for detalle in error.errors()]
        return JSONResponse(status_code=422, content={'detail': detalles})

    app.state.settings = configured
    configure_logging(configured)
    logger = logging.getLogger('tpi.api')
    app.add_middleware(RequestIdMiddleware, logger=logger)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(cuentas_router)
    return app
