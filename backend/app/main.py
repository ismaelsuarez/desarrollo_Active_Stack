import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.routers.health import router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    configured = settings if settings is not None else get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield

    app = FastAPI(title='Sistema de Turnos y Agenda Odontológica', lifespan=lifespan)
    app.state.settings = configured
    configure_logging(configured)
    logger = logging.getLogger('tpi.api')
    app.add_middleware(RequestIdMiddleware, logger=logger)
    app.include_router(router)
    return app
