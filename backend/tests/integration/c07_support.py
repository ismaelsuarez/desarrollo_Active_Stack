from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.api.deps import get_reloj
from app.application.services.token_service import AuthTokenService
from app.core.config import Settings
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import RelojSimulado
from app.infrastructure.db.models import (
    BoxModel, HorarioSemanalModel, PacienteModel, PrestacionModel,
    ProfesionalModel, UsuarioModel,
)
from app.main import create_app
from tests.integration.test_core_models import crear_consultorio_ejemplo

ZONA = ZoneInfo("America/Argentina/Buenos_Aires")
AHORA = datetime(2026, 11, 6, 8, tzinfo=ZONA)
INICIO = datetime(2026, 11, 9, 10, tzinfo=ZONA)


@dataclass
class Escenario:
    app: object
    reloj: RelojSimulado
    pacientes: dict[int, int]
    profesionales: dict[int, int]
    prestaciones: dict[int, int]
    usuarios: dict[tuple[int, str], int]

    def headers(self, rol="recepcion", consultorio=1):
        principal = Principal(self.usuarios[consultorio, rol], consultorio, RolUsuario(rol))
        token = AuthTokenService(self.reloj, "j" * 32).emitir_access_token(principal)
        return {"Authorization": f"Bearer {token}"}

    def payload(self, inicio=INICIO, consultorio=1, **extras):
        return {"paciente_id": self.pacientes[consultorio],
                "profesional_id": self.profesionales[consultorio],
                "prestacion_id": self.prestaciones[consultorio],
                "inicio": inicio.isoformat(), **extras}


async def preparar_escenario(sesiones, url_base):
    pacientes, profesionales, prestaciones, usuarios = {}, {}, {}, {}
    async with sesiones() as sesion:
        for cid in (1, 2):
            sesion.add(crear_consultorio_ejemplo(cid))
            await sesion.flush()
            for rol in ("recepcion", "administrador", "profesional", "paciente", "administrativo"):
                usuario = UsuarioModel(
                    consultorio_id=cid, nombre_usuario=f"{rol}{cid}", email=f"{rol}{cid}@example.test",
                    password_hash="sintetico", rol=rol, activo=True,
                    creado_en=AHORA, actualizado_en=AHORA,
                    aviso_privacidad_aceptado_en=AHORA if rol == "paciente" else None,
                    aviso_privacidad_version="prueba" if rol == "paciente" else None,
                )
                sesion.add(usuario)
                await sesion.flush()
                usuarios[cid, rol] = usuario.id
            box = BoxModel(consultorio_id=cid, nombre=f"Box {cid}")
            prestacion = PrestacionModel(consultorio_id=cid, nombre="Consulta", duracion_min=30)
            paciente = PacienteModel(
                consultorio_id=cid, nombre="Ana", apellido="Prueba", dni=f"1234567{cid}",
                usuario_id=None, creado_en=AHORA, actualizado_en=AHORA,
            )
            sesion.add_all((box, prestacion, paciente))
            await sesion.flush()
            profesional = ProfesionalModel(
                consultorio_id=cid, usuario_id=usuarios[cid, "profesional"],
                box_id=box.id, nombre="Patricia", apellido="Dental",
            )
            sesion.add(profesional)
            await sesion.flush()
            sesion.add_all(HorarioSemanalModel(
                consultorio_id=cid, profesional_id=profesional.id, dia_semana=dia,
                hora_inicio=time(9), hora_fin=time(17),
            ) for dia in range(1, 8))
            pacientes[cid], profesionales[cid], prestaciones[cid] = paciente.id, profesional.id, prestacion.id
        await sesion.commit()
    reloj = RelojSimulado(AHORA)
    app = create_app(Settings(
        database_url=url_base, jwt_secret_key="j" * 32, origin_hash_secret="o" * 32,
        app_env="test", consultorio_activo_id=1, cookie_secure=False,
    ))
    app.state.session_factory = sesiones
    app.dependency_overrides[get_reloj] = lambda: reloj
    return Escenario(app, reloj, pacientes, profesionales, prestaciones, usuarios)
