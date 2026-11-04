"""Resolución manual de vínculos; cada acción confirma una sola UoW."""
from app.application.errors_pacientes import RechazoPaciente, conflicto_paciente
from app.domain.entities.auth import Principal
from app.domain.policies.acceso import autorizar
from app.domain.ports.reloj import Reloj
from app.domain.value_objects.accion import Accion
from app.domain.value_objects.contexto_acceso import ContextoAcceso
from app.infrastructure.correo.plantillas_vinculacion import correo_vinculacion_rechazada


class VinculosPacientes:
    def __init__(self, unidades, reloj: Reloj):
        self._unidades = unidades
        self._reloj = reloj

    async def desvincular(self, principal: Principal, paciente_id: int, motivo: str):
        self._autorizar(principal, Accion.PACIENTE_DESVINCULAR)
        try:
            async with self._unidades() as unidad:
                cid = principal.consultorio_id
                ficha = await unidad.vinculos.bloquear_ficha(cid, paciente_id)
                if ficha is None:
                    raise RechazoPaciente(404, "Ficha no encontrada")
                if ficha.usuario_id is None:
                    raise RechazoPaciente(409, "La ficha no tiene cuenta vinculada")
                usuario_id, ahora = ficha.usuario_id, self._reloj.ahora()
                if not await unidad.vinculos.desvincular_ficha(cid, ficha.id, usuario_id):
                    raise RechazoPaciente(409, "El vínculo cambió")
                if not await unidad.vinculos.registrar_desvinculacion(
                        cid, usuario_id, ficha.id, ficha.dni, principal.usuario_id, ahora, motivo):
                    raise RechazoPaciente(409, "La solicitud cambió")
                usuario = await unidad.cuentas.usuario_por_id(cid, usuario_id)
                if usuario is None:
                    raise RechazoPaciente(409, "Cuenta no disponible")
                await unidad.cuentas.revocar_sesiones(cid, usuario_id, ahora)
        except Exception as error:
            if conflicto_paciente(error):
                raise RechazoPaciente(409, "Conflicto al desvincular") from None
            raise

    def _autorizar(self, principal: Principal, accion: Accion, recurso=None):
        decision = autorizar(principal, accion, recurso,
                             ContextoAcceso(ahora=self._reloj.ahora()))
        if not decision.permitido:
            raise RechazoPaciente(decision.codigo_http, decision.motivo)

    @staticmethod
    def _ficha_minima(ficha):
        return None if ficha is None else {"id": ficha.id, "nombre": ficha.nombre,
                                           "apellido": ficha.apellido}

    async def listar(self, principal: Principal, estado=None, limit=20, offset=0):
        self._autorizar(principal, Accion.PACIENTE_VINCULAR)
        async with self._unidades() as unidad:
            filas, total = await unidad.vinculos.listar_solicitudes(
                principal.consultorio_id, estado, limit, offset)
            items = []
            for solicitud, usuario, coincidente, vinculada in filas:
                item = {"id": solicitud.id, "estado": solicitud.estado,
                        "dni_declarado": solicitud.dni_declarado, "email": usuario.email,
                        "email_verificado": usuario.email_verificado,
                        "ficha_existente": self._ficha_minima(coincidente),
                        "creada_en": solicitud.creada_en, "resuelta_en": solicitud.resuelta_en,
                        "resuelta_por_id": solicitud.resuelta_por_id,
                        "motivo_rechazo": solicitud.motivo_rechazo}
                if solicitud.estado == "vinculada":
                    item["ficha_vinculada"] = self._ficha_minima(vinculada)
                items.append(item)
            return {"items": items, "total": total, "limit": limit, "offset": offset}

    async def vincular(self, principal: Principal, solicitud_id: int, paciente_id: int):
        self._autorizar(principal, Accion.PACIENTE_VINCULAR)
        try:
            async with self._unidades() as unidad:
                cid = principal.consultorio_id
                solicitud = await unidad.vinculos.obtener_solicitud(cid, solicitud_id)
                if solicitud is None:
                    raise RechazoPaciente(404, "Solicitud no encontrada")
                self._autorizar(principal, Accion.PACIENTE_VINCULAR, solicitud)
                ficha = await unidad.vinculos.bloquear_ficha(cid, paciente_id)
                if ficha is None:
                    raise RechazoPaciente(404, "Ficha no encontrada")
                ahora = self._reloj.ahora()
                if not await unidad.vinculos.vincular_solicitud(
                        cid, solicitud.id, solicitud.estado, ficha.id, principal.usuario_id, ahora):
                    raise RechazoPaciente(409, "La solicitud cambió o ya está vinculada")
                usuario = await unidad.cuentas.usuario_por_id(cid, solicitud.usuario_id)
                if usuario is None or not usuario.email_verificado:
                    raise RechazoPaciente(409, "La cuenta no está disponible para vincular")
                if not await unidad.vinculos.vincular_ficha(cid, ficha.id, usuario.id, ahora):
                    raise RechazoPaciente(409, "La ficha no está disponible para vincular")
        except Exception as error:
            if conflicto_paciente(error):
                raise RechazoPaciente(409, "Conflicto al resolver el vínculo") from None
            raise

    async def rechazar(self, principal: Principal, solicitud_id: int,
                       motivo: str | None = None) -> int | None:
        self._autorizar(principal, Accion.PACIENTE_VINCULAR)
        notificacion_id = None
        try:
            async with self._unidades() as unidad:
                cid = principal.consultorio_id
                solicitud = await unidad.vinculos.obtener_solicitud(cid, solicitud_id)
                if solicitud is None:
                    raise RechazoPaciente(404, "Solicitud no encontrada")
                self._autorizar(principal, Accion.PACIENTE_VINCULAR, solicitud)
                ahora = self._reloj.ahora()
                if not await unidad.vinculos.rechazar_solicitud(
                        cid, solicitud.id, solicitud.estado, principal.usuario_id, ahora, motivo):
                    raise RechazoPaciente(409, "La solicitud cambió o ya fue resuelta")
                usuario = await unidad.cuentas.usuario_por_id(cid, solicitud.usuario_id)
                if usuario is None:
                    raise RechazoPaciente(409, "Cuenta no disponible")
                if usuario.email_verificado:
                    notificacion_id = await unidad.vinculos.programar_rechazo(
                        cid, usuario.id, usuario.email, correo_vinculacion_rechazada(), ahora)
        except Exception as error:
            if conflicto_paciente(error):
                raise RechazoPaciente(409, "Conflicto al resolver la solicitud") from None
            raise
        return notificacion_id
