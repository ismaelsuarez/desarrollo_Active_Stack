from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def crear_engine(url: str) -> AsyncEngine:
    return create_async_engine(url)


def crear_fabrica_de_sesiones(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Una sesión nueva por operación; nunca se comparte entre tareas."""
    return async_sessionmaker(engine, expire_on_commit=False)
