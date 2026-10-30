from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def crear_engine(url: str, **kwargs: Any) -> AsyncEngine:
    connect_args = kwargs.pop("connect_args", {})
    connect_args.setdefault("prepared_statement_cache_size", 0)
    return create_async_engine(url, connect_args=connect_args, **kwargs)


def crear_fabrica_de_sesiones(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Una sesión nueva por operación; nunca se comparte entre tareas."""
    return async_sessionmaker(engine, expire_on_commit=False)
