import asyncio
import sys

from pwdlib import PasswordHash
from sqlalchemy import select, text

from app.core.config import SeedSettings
from app.domain.ports.reloj import RelojSistema
from app.infrastructure.db.models import ConsultorioModel, PrestacionModel, UsuarioModel
from app.infrastructure.db.sesion import crear_engine, crear_fabrica_de_sesiones

PASSWORD_HASH = PasswordHash.recommended()

PRESTACIONES_SUGERIDAS = (
    ("Primera consulta y diagnóstico", 30),
    ("Control de rutina", 20),
    ("Limpieza dental (profilaxis)", 40),
    ("Restauración (arreglo de caries)", 45),
    ("Endodoncia (tratamiento de conducto)", 60),
    ("Extracción simple", 30),
    ("Blanqueamiento", 60),
    ("Control de ortodoncia", 20),
    ("Urgencia o consulta por dolor", 30),
)


async def sembrar(settings: SeedSettings) -> None:
    reloj = RelojSistema()
    engine = crear_engine(settings.migration_url)
    fabrica_sesiones = crear_fabrica_de_sesiones(engine)

    try:
        async with fabrica_sesiones() as sesion:
            # 1. Provisión de consultorio activo (idempotente)
            consultorio = await sesion.scalar(
                select(ConsultorioModel).where(
                    ConsultorioModel.id == settings.consultorio_activo_id
                )
            )
            if consultorio is None:
                ahora = reloj.ahora()
                consultorio = ConsultorioModel(
                    id=settings.consultorio_activo_id,
                    nombre="Consultorio Odontológico",
                    telefono=None,
                    direccion=None,
                    zona_horaria=settings.app_timezone,
                    modo_liberacion="automatico",
                    horas_confirmacion=48,
                    horas_recordatorio=24,
                    horas_liberacion=12,
                    horas_limite_paciente=24,
                    minutos_granularidad=15,
                    dias_anticipacion_maxima=60,
                    max_turnos_activos_paciente=2,
                    activo=True,
                    creado_en=ahora,
                    actualizado_en=ahora,
                )
                sesion.add(consultorio)
                await sesion.flush()

                # Sincronizar secuencia consultorio_id_seq para que nuevas inserciones no colisionen (DD-23)
                await sesion.execute(
                    text(
                        "SELECT setval(pg_get_serial_sequence('consultorio', 'id'), "
                        "coalesce(max(id), 1)) FROM consultorio"
                    )
                )

            # 2. Provisión de usuario administrador inicial (idempotente)
            admin = await sesion.scalar(
                select(UsuarioModel).where(
                    UsuarioModel.consultorio_id == settings.consultorio_activo_id,
                    UsuarioModel.rol == "administrador",
                )
            )
            if admin is None:
                ahora = reloj.ahora()
                admin_email = settings.bootstrap_admin_email.strip().lower()
                admin_hash = PASSWORD_HASH.hash(
                    settings.bootstrap_admin_password.get_secret_value()
                )
                admin = UsuarioModel(
                    consultorio_id=settings.consultorio_activo_id,
                    nombre_usuario="admin",
                    email=admin_email,
                    password_hash=admin_hash,
                    rol="administrador",
                    email_verificado=True,
                    email_verificado_en=ahora,
                    aviso_privacidad_aceptado_en=None,
                    aviso_privacidad_version=None,
                    activo=True,
                    creado_en=ahora,
                    actualizado_en=ahora,
                )
                sesion.add(admin)

            # 3. Catálogo inicial sugerido: no alterar las decisiones del consultorio.
            tiene_prestaciones = await sesion.scalar(
                select(PrestacionModel.id)
                .where(PrestacionModel.consultorio_id == settings.consultorio_activo_id)
                .limit(1)
            )
            if tiene_prestaciones is None:
                sesion.add_all(
                    PrestacionModel(
                        consultorio_id=settings.consultorio_activo_id,
                        nombre=nombre,
                        duracion_min=duracion_min,
                        activa=True,
                        sugerida=True,
                    )
                    for nombre, duracion_min in PRESTACIONES_SUGERIDAS
                )

            await sesion.commit()
    finally:
        await engine.dispose()


def main() -> None:
    try:
        settings = SeedSettings()
        asyncio.run(sembrar(settings))
        print("Semilla completada exitosamente")
    except Exception as error:
        print(f"Error al ejecutar semilla: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
