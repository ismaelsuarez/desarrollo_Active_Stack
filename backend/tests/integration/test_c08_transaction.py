import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.account_models import SolicitudVinculacionModel
from app.infrastructure.db.models import PacienteModel, RefreshTokenModel
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
from tests.integration.c07_support import AHORA, preparar_escenario

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("fallo", [None, "body", "flush", "commit"])
async def test_uow_comparte_repos_y_revierte_ficha_solicitud_y_sesion(engine, sesiones, url_base, fallo):
    escenario = await preparar_escenario(sesiones, url_base)
    uid = escenario.usuarios[1, "paciente"]
    actor = escenario.usuarios[1, "recepcion"]
    async with sesiones() as sesion:
        solicitud = SolicitudVinculacionModel(
            consultorio_id=1, usuario_id=uid, dni_declarado="29999999",
            estado="pendiente", creada_en=AHORA,
        )
        sesion.add_all((solicitud, RefreshTokenModel(
            consultorio_id=1, usuario_id=uid, token_hash="b" * 64,
            expira_en=AHORA.replace(year=2027), creado_en=AHORA,
        )))
        await sesion.commit()
        sid = solicitud.id

    eventos, instancias = [], []

    class SesionObservada(AsyncSession):
        falla_flush = False

        async def flush(self, *args, **kwargs):
            await super().flush(*args, **kwargs)
            if self.falla_flush:
                raise RuntimeError("flush C08 controlado")

        async def commit(self):
            if fallo == "commit":
                await self.flush()
                raise RuntimeError("commit C08 controlado")
            await super().commit()

        async def rollback(self):
            eventos.append("rollback")
            await super().rollback()

        async def close(self):
            eventos.append("close")
            await super().close()

    fabrica = async_sessionmaker(engine, class_=SesionObservada, expire_on_commit=False)

    async def operar():
        async with UnidadDeTrabajoSQL(fabrica) as unidad:
            instancias.append(unidad._sesion)
            ficha = await unidad.pacientes.crear(1, {
                "nombre": "Nueva", "apellido": "Transacción", "telefono": "1112345678",
                "email": "ficha@example.test", "dni": "29999999",
            }, AHORA)
            assert await unidad.vinculos.vincular_solicitud(1, sid, "pendiente", ficha.id, actor, AHORA)
            assert await unidad.vinculos.vincular_ficha(1, ficha.id, uid, AHORA)
            await unidad.cuentas.revocar_sesiones(1, uid, AHORA)
            if fallo == "body":
                raise RuntimeError("body C08 controlado")
            if fallo == "flush":
                unidad._sesion.falla_flush = True
                await unidad._sesion.flush()

    if fallo:
        with pytest.raises(RuntimeError, match="C08 controlado"):
            await operar()
        assert eventos == ["rollback", "close"]
    else:
        await operar()
        assert eventos == ["close"]
    async with sesiones() as sesion:
        ficha = await sesion.scalar(select(PacienteModel).where(PacienteModel.dni == "29999999"))
        solicitud = await sesion.get(SolicitudVinculacionModel, sid)
        token = await sesion.scalar(select(RefreshTokenModel).where(RefreshTokenModel.usuario_id == uid))
        assert (ficha is not None) is (fallo is None)
        assert solicitud.estado == ("vinculada" if fallo is None else "pendiente")
        assert token.revocado_en == (AHORA if fallo is None else None)
    async with UnidadDeTrabajoSQL(sesiones) as siguiente:
        assert siguiente._sesion is not instancias[0]
        assert siguiente._sesion.sync_session.expire_on_commit is False
