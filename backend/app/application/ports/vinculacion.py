from datetime import datetime
from typing import Protocol


class SolicitudVinculacion(Protocol):
    id: int
    consultorio_id: int
    usuario_id: int
    estado: str
    dni_declarado: str
    paciente_id: int | None


class FichaVinculo(Protocol):
    id: int
    consultorio_id: int
    usuario_id: int | None
    activo: bool
    dni: str


class RepositorioVinculacion(Protocol):
    async def desvincular_ficha(self, consultorio_id: int, paciente_id: int,
                               usuario_id: int) -> bool: ...

    async def registrar_desvinculacion(self, consultorio_id: int, usuario_id: int,
                                     paciente_id: int, dni: str, actor_id: int,
                                     ahora: datetime, motivo: str) -> bool: ...

    async def listar_solicitudes(self, consultorio_id: int, estado: str | None,
                                limit: int, offset: int) -> tuple[list, int]: ...

    async def obtener_solicitud(self, consultorio_id: int,
                               solicitud_id: int) -> SolicitudVinculacion | None: ...

    async def bloquear_ficha(self, consultorio_id: int,
                            paciente_id: int) -> FichaVinculo | None: ...

    async def vincular_solicitud(self, consultorio_id: int, solicitud_id: int,
                                estado_leido: str, paciente_id: int,
                                actor_id: int, ahora: datetime) -> bool: ...

    async def vincular_ficha(self, consultorio_id: int, paciente_id: int,
                            usuario_id: int, ahora: datetime) -> bool: ...

    async def rechazar_solicitud(self, consultorio_id: int, solicitud_id: int,
                                estado_leido: str, actor_id: int, ahora: datetime,
                                motivo: str | None) -> bool: ...

    async def programar_rechazo(self, consultorio_id: int, usuario_id: int,
                               destinatario: str, cuerpo: str, ahora: datetime) -> int: ...
