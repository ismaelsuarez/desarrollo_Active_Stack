"""Persistencia de fichas con pertenencia explícita al consultorio."""
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import PacienteModel, UsuarioModel


class RepositorioPacientesSQL:
    def __init__(self, sesion: AsyncSession) -> None:
        self.sesion = sesion

    async def obtener(self, consultorio_id: int, paciente_id: int, *, bloquear: bool = False):
        consulta = select(PacienteModel).where(
            PacienteModel.consultorio_id == consultorio_id, PacienteModel.id == paciente_id,
        ).execution_options(populate_existing=True)
        if bloquear:
            consulta = consulta.with_for_update()
        return await self.sesion.scalar(consulta)

    async def crear(self, consultorio_id: int, datos: dict, ahora: datetime) -> PacienteModel:
        ficha = PacienteModel(consultorio_id=consultorio_id, **datos, usuario_id=None,
                              activo=True, creado_en=ahora, actualizado_en=ahora)
        self.sesion.add(ficha)
        await self.sesion.flush()
        return ficha

    async def cuenta_de_paciente(self, consultorio_id: int, paciente_id: int):
        fila = (await self.sesion.execute(select(
            UsuarioModel.id, UsuarioModel.nombre_usuario, UsuarioModel.email, UsuarioModel.email_verificado,
        ).join(PacienteModel, PacienteModel.usuario_id == UsuarioModel.id).where(
            PacienteModel.consultorio_id == consultorio_id, PacienteModel.id == paciente_id,
            UsuarioModel.consultorio_id == consultorio_id,
        ))).mappings().one_or_none()
        return dict(fila) if fila is not None else None

    async def listar(self, consultorio_id: int, *, ids_permitidos=None, apellido=None,
                     dni=None, telefono=None, limit=20, offset=0):
        consulta = select(PacienteModel).where(PacienteModel.consultorio_id == consultorio_id)
        if ids_permitidos is not None:
            consulta = consulta.where(PacienteModel.id.in_(ids_permitidos))
        if apellido is not None:
            consulta = consulta.where(PacienteModel.apellido.icontains(apellido, autoescape=True))
        if dni is not None:
            consulta = consulta.where(PacienteModel.dni == dni)
        if telefono is not None:
            consulta = consulta.where(PacienteModel.telefono.contains(telefono, autoescape=True))
        total = await self.sesion.scalar(select(func.count()).select_from(consulta.subquery()))
        filas = (await self.sesion.scalars(consulta.order_by(
            PacienteModel.apellido, PacienteModel.nombre, PacienteModel.id,
        ).limit(limit).offset(offset))).all()
        return list(filas), total

    async def de_usuario(self, consultorio_id: int, usuario_id: int):
        return await self.sesion.scalar(select(PacienteModel).where(
            PacienteModel.consultorio_id == consultorio_id, PacienteModel.usuario_id == usuario_id,
        ).execution_options(populate_existing=True))

    async def reactivar(self, consultorio_id: int, paciente_id: int, ahora: datetime) -> bool:
        identificador = await self.sesion.scalar(update(PacienteModel).where(
            PacienteModel.consultorio_id == consultorio_id, PacienteModel.id == paciente_id,
            PacienteModel.activo.is_(False),
        ).values(activo=True).returning(PacienteModel.id))
        return identificador is not None

    async def editar(self, consultorio_id: int, paciente_id: int, datos: dict, ahora: datetime):
        return await self.sesion.scalar(update(PacienteModel).where(
            PacienteModel.consultorio_id == consultorio_id, PacienteModel.id == paciente_id,
        ).values(**datos, actualizado_en=ahora).returning(PacienteModel))
