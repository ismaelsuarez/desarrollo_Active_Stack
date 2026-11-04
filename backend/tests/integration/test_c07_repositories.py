from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.entities.historial import HechoDeTurno
from app.domain.value_objects.estado_turno import EstadoTurno
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
from tests.integration.fabricas import crear_profesional, crear_prestacion, crear_turno, hora

pytestmark = pytest.mark.integration


async def reserva(engine):
    profesional = await crear_profesional(engine)
    prestacion = await crear_prestacion(engine)
    return await crear_turno(engine, profesional_id=profesional, prestacion_id=prestacion, inicio=hora(10))


async def test_history_is_committed_with_turn_transaction_and_read_without_mutation(engine, sesiones):
    identificador = await reserva(engine)
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        await unidad.historial.agregar(HechoDeTurno(
            consultorio_id=1, turno_id=identificador, usuario_id=None,
            accion="crear", estado_anterior=None, estado_nuevo=EstadoTurno.PENDIENTE,
            detalle={"motivo": "RN-23"}, ocurrido_en=hora(8),
        ))
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        hechos = await unidad.historial.listar(1, identificador)
        assert len(hechos) == 1
        assert hechos[0].accion == "crear"
        assert hechos[0].detalle == {"motivo": "RN-23"}
        assert await unidad.historial.listar(2, identificador) == []
        assert not hasattr(unidad.historial, "borrar")
        assert not hasattr(unidad.historial, "actualizar")


@pytest.mark.parametrize("failure", ["history", "body", "commit", None])
async def test_turn_and_history_are_atomic_on_every_transaction_exit(engine, sesiones, failure):
    identificador = await reserva(engine)

    class CommitFallido(AsyncSession):
        async def commit(self):
            await self.flush()
            raise RuntimeError("commit controlado")

    factory = async_sessionmaker(engine, class_=CommitFallido, expire_on_commit=False) if failure == "commit" else sesiones

    async def transition():
        async with UnidadDeTrabajoSQL(factory) as unidad:
            await unidad._sesion.execute(text("UPDATE turno SET estado='confirmado' WHERE id=:id"), {"id": identificador})
            await unidad.historial.agregar(HechoDeTurno(
                consultorio_id=1, turno_id=identificador, usuario_id=None,
                accion="no-existe" if failure == "history" else "confirmar",
                estado_anterior=EstadoTurno.PENDIENTE, estado_nuevo=EstadoTurno.CONFIRMADO,
                detalle=None, ocurrido_en=hora(8),
            ))
            if failure == "body":
                raise RuntimeError("cuerpo controlado")

    if failure:
        with pytest.raises(IntegrityError if failure == "history" else RuntimeError):
            await transition()
    else:
        await transition()
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT estado::text FROM turno WHERE id=:id"), {"id": identificador}) == ("pendiente" if failure else "confirmado")
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial WHERE turno_id=:id"), {"id": identificador}) == (0 if failure else 1)


async def test_additional_history_keeps_existing_facts_and_empty_history(engine, sesiones):
    identificador = await reserva(engine)
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        assert await unidad.historial.listar(1, identificador) == []
        for indice, accion in enumerate(("crear", "confirmar")):
            await unidad.historial.agregar(HechoDeTurno(
                consultorio_id=1, turno_id=identificador, usuario_id=None,
                accion=accion, estado_anterior=None if indice == 0 else EstadoTurno.PENDIENTE,
                estado_nuevo=EstadoTurno.PENDIENTE if indice == 0 else EstadoTurno.CONFIRMADO,
                detalle=None, ocurrido_en=hora(8) + timedelta(seconds=indice),
            ))
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        hechos = await unidad.historial.listar(1, identificador)
        assert [h.accion for h in hechos] == ["crear", "confirmar"]
        assert hechos[0].estado_nuevo == EstadoTurno.PENDIENTE
