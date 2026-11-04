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
        await conexion.execute(text("""
            INSERT INTO consultorio (id, nombre, zona_horaria, modo_liberacion,
              horas_confirmacion, horas_recordatorio, horas_liberacion,
              horas_limite_paciente, minutos_granularidad, dias_anticipacion_maxima,
              max_turnos_activos_paciente, activo, creado_en, actualizado_en)
            OVERRIDING SYSTEM VALUE
            VALUES (:cid, 'Consultorio de prueba', 'America/Argentina/Buenos_Aires',
              'automatico', 48, 24, 12, 24, 15, 60, 2, true, now(), now())
            ON CONFLICT (id) DO NOTHING
        """), {"cid": consultorio_id})
        await conexion.execute(text("""
            INSERT INTO box (id, consultorio_id, nombre)
            OVERRIDING SYSTEM VALUE VALUES (:bid, :cid, :nombre)
            ON CONFLICT (id) DO NOTHING
        """), {"bid": box_id, "cid": consultorio_id, "nombre": f"Box {box_id}"})
        await conexion.execute(text("""
            SELECT setval(pg_get_serial_sequence('box', 'id'),
              GREATEST((SELECT coalesce(max(id), 1) FROM box), 1))
        """))
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
        await conexion.execute(text("""
            INSERT INTO consultorio (id, nombre, zona_horaria, modo_liberacion,
              horas_confirmacion, horas_recordatorio, horas_liberacion,
              horas_limite_paciente, minutos_granularidad, dias_anticipacion_maxima,
              max_turnos_activos_paciente, activo, creado_en, actualizado_en)
            OVERRIDING SYSTEM VALUE
            VALUES (:cid, 'Consultorio de prueba', 'America/Argentina/Buenos_Aires',
              'automatico', 48, 24, 12, 24, 15, 60, 2, true, now(), now())
            ON CONFLICT (id) DO NOTHING
        """), {"cid": consultorio_id})
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


async def crear_paciente(engine: AsyncEngine, *, consultorio_id: int = 1) -> int:
    """Ficha sintética sin cuenta para pruebas que antes usaban un id sin FK."""
    async with engine.begin() as conexion:
        await conexion.execute(text("""
            INSERT INTO consultorio (id,nombre,zona_horaria,modo_liberacion,
              horas_confirmacion,horas_recordatorio,horas_liberacion,horas_limite_paciente,
              minutos_granularidad,dias_anticipacion_maxima,max_turnos_activos_paciente,
              activo,creado_en,actualizado_en)
            VALUES (:cid,'Consultorio de prueba','America/Argentina/Buenos_Aires','automatico',
              48,24,12,24,15,60,2,true,:ahora,:ahora) ON CONFLICT (id) DO NOTHING
        """), {"cid": consultorio_id, "ahora": hora(8)})
        return await conexion.scalar(text("""
            INSERT INTO paciente (consultorio_id,nombre,apellido,dni,activo,creado_en,actualizado_en)
            VALUES (:cid,'Paciente','Sintetico','30123456',true,:ahora,:ahora)
            ON CONFLICT (consultorio_id,dni) DO UPDATE SET dni=EXCLUDED.dni RETURNING id
        """), {"cid": consultorio_id, "ahora": hora(8)})


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
        paciente_id = await conexion.scalar(text("""
            SELECT id FROM paciente WHERE consultorio_id=:cid AND dni='30123456'
        """), {"cid": consultorio_id})
        if paciente_id is None:
            paciente_id = await conexion.scalar(text("""
                INSERT INTO paciente (consultorio_id,nombre,apellido,dni,activo,creado_en,actualizado_en)
                VALUES (:cid,'Paciente','Sintetico','30123456',true,:ahora,:ahora) RETURNING id
            """), {"cid": consultorio_id, "ahora": hora(8)})
        box_id = await conexion.scalar(text("SELECT box_id FROM profesional WHERE id=:id"), {"id": profesional_id})
        return await conexion.scalar(
            text(
                "INSERT INTO turno (consultorio_id, paciente_id, profesional_id, "
                "box_id, prestacion_id, inicio, fin, estado, creado_en) "
                "VALUES (:consultorio_id, :paciente_id, :profesional_id, :box_id, :prestacion_id, "
                ":inicio, :fin, CAST(:estado AS estado_turno), :ahora) RETURNING id"
            ),
            {
                "consultorio_id": consultorio_id,
                "paciente_id": paciente_id,
                "box_id": box_id,
                "ahora": hora(8),
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
