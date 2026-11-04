"""Gestión de fichas con autorización centralizada y pertenencia explícita."""
from types import SimpleNamespace
from functools import wraps

from sqlalchemy.exc import DBAPIError

from app.application.errors_pacientes import RechazoPaciente, conflicto_paciente
from app.application.services.cuentas import ErrorCuenta, actualizar_contacto_transaccional
from app.domain.entities.auth import RolUsuario
from app.domain.policies.acceso import autorizar
from app.domain.value_objects.accion import Accion
from app.domain.value_objects.contexto_acceso import ContextoAcceso


def _traducir_conflictos(funcion):
    @wraps(funcion)
    async def ejecutar(*args, **kwargs):
        try:
            return await funcion(*args, **kwargs)
        except DBAPIError as error:
            if conflicto_paciente(error):
                raise RechazoPaciente(409, "Los datos de la ficha cambiaron o no están disponibles") from None
            raise
    return ejecutar


class GestionarPacientes:
    def __init__(self, unidades, reloj, settings):
        self._unidades = unidades
        self._reloj = reloj
        self._settings = settings

    @staticmethod
    def _autorizar(principal, accion, ficha, contexto):
        decision = autorizar(principal, accion, ficha, contexto)
        if not decision.permitido:
            raise RechazoPaciente(decision.codigo_http, decision.motivo)

    @_traducir_conflictos
    async def crear(self, principal, datos):
        ahora = self._reloj.ahora()
        self._autorizar(principal, Accion.PACIENTE_EDITAR,
                        SimpleNamespace(id=0, consultorio_id=principal.consultorio_id),
                        ContextoAcceso(ahora=ahora))
        async with self._unidades() as unidad:
            ficha = await unidad.pacientes.crear(principal.consultorio_id, datos, ahora)
            identificador = ficha.id
        return {"id": identificador}

    async def detalle(self, principal, paciente_id):
        async with self._unidades() as unidad:
            pacientes_profesional = frozenset()
            if principal.rol == RolUsuario.PROFESIONAL:
                profesional_id = await unidad.agenda.profesional_vinculado(
                    principal.consultorio_id, principal.usuario_id, incluir_inactivos=True)
                if profesional_id is not None:
                    pacientes_profesional = await unidad.agenda.pacientes_de_profesional(
                        principal.consultorio_id, profesional_id)
                if paciente_id not in pacientes_profesional:
                    raise RechazoPaciente(404, "Ficha no encontrada")
            ficha = await unidad.pacientes.obtener(principal.consultorio_id, paciente_id)
            if ficha is None:
                raise RechazoPaciente(404, "Ficha no encontrada")
            self._autorizar(principal, Accion.PACIENTE_VER, ficha,
                            ContextoAcceso(ahora=self._reloj.ahora(), ficha_usuario_id=ficha.usuario_id,
                                           turnos_del_profesional=pacientes_profesional))
            datos = {"id": ficha.id, "nombre": ficha.nombre, "apellido": ficha.apellido,
                     "telefono": ficha.telefono, "email": ficha.email, "dni": ficha.dni,
                     "obra_social": ficha.obra_social, "notas": ficha.notas, "activo": ficha.activo}
            if principal.rol in (RolUsuario.RECEPCION, RolUsuario.ADMINISTRADOR):
                datos["cuenta"] = await unidad.pacientes.cuenta_de_paciente(principal.consultorio_id, paciente_id)
            return datos

    async def listar(self, principal, **filtros):
        async with self._unidades() as unidad:
            ids_permitidos = None
            pacientes_profesional = frozenset()
            if principal.rol == RolUsuario.PROFESIONAL:
                profesional_id = await unidad.agenda.profesional_vinculado(
                    principal.consultorio_id, principal.usuario_id, incluir_inactivos=True)
                if profesional_id is not None:
                    pacientes_profesional = await unidad.agenda.pacientes_de_profesional(principal.consultorio_id, profesional_id)
                ids_permitidos = pacientes_profesional
            elif principal.rol == RolUsuario.PACIENTE:
                ficha = await unidad.pacientes.de_usuario(principal.consultorio_id, principal.usuario_id)
                ids_permitidos = frozenset([ficha.id]) if ficha else frozenset()
            else:
                self._autorizar(principal, Accion.PACIENTE_VER,
                                SimpleNamespace(id=0, consultorio_id=principal.consultorio_id),
                                ContextoAcceso(ahora=self._reloj.ahora()))
            fichas, total = await unidad.pacientes.listar(principal.consultorio_id, ids_permitidos=ids_permitidos, **filtros)
            for ficha in fichas:
                self._autorizar(principal, Accion.PACIENTE_VER, ficha,
                                ContextoAcceso(ahora=self._reloj.ahora(), ficha_usuario_id=ficha.usuario_id,
                                               turnos_del_profesional=pacientes_profesional))
            items = [{"id": f.id, "nombre": f.nombre, "apellido": f.apellido,
                      "telefono": f.telefono, "activo": f.activo} for f in fichas]
        return {"items": items, "total": total, "limit": filtros.get("limit", 20), "offset": filtros.get("offset", 0)}

    @_traducir_conflictos
    async def editar(self, principal, paciente_id, datos):
        async with self._unidades() as unidad:
            ficha = await unidad.pacientes.obtener(principal.consultorio_id, paciente_id, bloquear=True)
            if ficha is None:
                raise RechazoPaciente(404, "Ficha no encontrada")
            self._autorizar(principal, Accion.PACIENTE_EDITAR, ficha,
                            ContextoAcceso(ahora=self._reloj.ahora(), ficha_usuario_id=ficha.usuario_id))
            await unidad.pacientes.editar(principal.consultorio_id, paciente_id, datos, self._reloj.ahora())
        return {"id": paciente_id}

    @_traducir_conflictos
    async def editar_contacto(self, principal, paciente_id, datos):
        if datos.keys() - {"telefono", "email"}:
            raise RechazoPaciente(422, "Sólo se permite actualizar teléfono y correo propios")
        async with self._unidades() as unidad:
            ficha = await unidad.pacientes.obtener(principal.consultorio_id, paciente_id)
            if ficha is None:
                raise RechazoPaciente(404, "Ficha no encontrada")
            self._autorizar(principal, Accion.PACIENTE_EDITAR, ficha,
                            ContextoAcceso(ahora=self._reloj.ahora(), ficha_usuario_id=ficha.usuario_id))
            try:
                notificacion_id = await actualizar_contacto_transaccional(
                    unidad.cuentas, self._reloj, self._settings, principal,
                    datos.get("telefono"), datos.get("email"), paciente_id_esperado=paciente_id,
                )
            except ErrorCuenta as error:
                raise RechazoPaciente(error.status_code, str(error)) from None
        return notificacion_id
