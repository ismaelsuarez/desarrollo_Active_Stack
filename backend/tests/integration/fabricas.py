"""Datos de prueba insertados directamente en la base, sin pasar por casos de uso."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")


def hora(horas: int, minutos: int = 0) -> datetime:
    """Un instante del lunes 2026-11-02 en hora de Buenos Aires."""
    return datetime(2026, 11, 2, horas, minutos, tzinfo=BUENOS_AIRES)


async def crear_profesional(
    engine: AsyncEngine, *, consultorio_id: int = 1, box_id: int = 1
) -> int:
    async with engine.begin() as conexion:
        return await conexion.scalar(
            text(
                "INSERT INTO profesional (consultorio_id, box_id, nombre, apellido) "
                "VALUES (:consultorio_id, :box_id, 'Ana', 'Paz') RETURNING id"
            ),
            {"consultorio_id": consultorio_id, "box_id": box_id},
        )


async def crear_prestacion(
    engine: AsyncEngine, *, consultorio_id: int = 1, duracion_min: int = 30
) -> int:
    async with engine.begin() as conexion:
        return await conexion.scalar(
            text(
                "INSERT INTO prestacion (consultorio_id, nombre, duracion_min) "
                "VALUES (:consultorio_id, :nombre, :duracion_min) RETURNING id"
            ),
            {
                "consultorio_id": consultorio_id,
                "nombre": f"Consulta de {duracion_min} minutos",
                "duracion_min": duracion_min,
            },
        )


async def crear_turno(
    engine: AsyncEngine,
    *,
    profesional_id: int,
    prestacion_id: int,
    inicio: datetime,
    duracion_min: int = 30,
    estado: str = "pendiente",
    consultorio_id: int = 1,
) -> int:
    """Inserta un turno en el estado pedido; ningún caso de uso cancela ni libera todavía."""
    async with engine.begin() as conexion:
        return await conexion.scalar(
            text(
                "INSERT INTO turno (consultorio_id, paciente_id, profesional_id, "
                "box_id, prestacion_id, inicio, fin, estado) "
                "VALUES (:consultorio_id, 1, :profesional_id, 1, :prestacion_id, "
                ":inicio, :fin, CAST(:estado AS estado_turno)) RETURNING id"
            ),
            {
                "consultorio_id": consultorio_id,
                "profesional_id": profesional_id,
                "prestacion_id": prestacion_id,
                "inicio": inicio,
                "fin": inicio + timedelta(minutes=duracion_min),
                "estado": estado,
            },
        )


async def contar_turnos(engine: AsyncEngine, profesional_id: int | None = None) -> int:
    async with engine.connect() as conexion:
        if profesional_id is None:
            return await conexion.scalar(text("SELECT count(*) FROM turno"))
        return await conexion.scalar(
            text("SELECT count(*) FROM turno WHERE profesional_id = :id"),
            {"id": profesional_id},
        )
