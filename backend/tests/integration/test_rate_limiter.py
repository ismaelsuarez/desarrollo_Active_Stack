from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.services.rate_limiter import LoginRateLimiter
from app.domain.ports.reloj import RelojSimulado
from app.infrastructure.db.models import ConsultorioModel, IntentoIngresoModel

pytestmark = pytest.mark.integration

SECRET = "origin-hash-secret-for-rate-limiter-123456"
AHORA = datetime(2026, 10, 30, 16, 0, 0, tzinfo=timezone.utc)


def crear_consultorio(id: int = 1) -> ConsultorioModel:
    ahora = AHORA
    return ConsultorioModel(
        id=id,
        nombre="Consultorio Rate Limit",
        telefono="1122334455",
        direccion="Av. Belgrano 123",
        zona_horaria="America/Argentina/Buenos_Aires",
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


async def test_cinco_intentos_no_bloquean_sexto_bloquea_par(sesiones: async_sessionmaker[AsyncSession]):
    reloj = RelojSimulado(AHORA)
    async with sesiones() as sesion:
        consultorio = crear_consultorio(id=20)
        sesion.add(consultorio)
        await sesion.commit()

        limiter = LoginRateLimiter(
            sesion=sesion,
            reloj=reloj,
            origin_hash_secret=SECRET,
            login_max_attempts=5,
            login_lockout_minutes=15,
            login_max_attempts_per_origin=20,
            trusted_proxy_hops=0,
        )

        # Primeros 5 intentos: no bloqueados
        for i in range(5):
            bloqueado, _, _ = await limiter.registrar_intento_y_verificar_bloqueo(
                consultorio_id=20,
                identificador="admin",
                client_host="192.168.1.50",
                x_forwarded_for=None,
            )
            assert bloqueado is False, f"Intento {i+1} no debió bloquear"

        # 6to intento: bloqueado
        bloqueado, _, _ = await limiter.registrar_intento_y_verificar_bloqueo(
            consultorio_id=20,
            identificador="admin",
            client_host="192.168.1.50",
            x_forwarded_for=None,
        )
        assert bloqueado is True, "El sexto intento debe resultar bloqueado"

        # Avanzar el reloj 16 minutos: se libera el bloqueo
        reloj.avanzar(timedelta(minutes=16))
        bloqueado, _, _ = await limiter.registrar_intento_y_verificar_bloqueo(
            consultorio_id=20,
            identificador="admin",
            client_host="192.168.1.50",
            x_forwarded_for=None,
        )
        assert bloqueado is False, "Tras salir de la ventana de 15 min, el intento no debe estar bloqueado"


async def test_origen_distinto_no_esta_bloqueado(sesiones: async_sessionmaker[AsyncSession]):
    reloj = RelojSimulado(AHORA)
    async with sesiones() as sesion:
        consultorio = crear_consultorio(id=21)
        sesion.add(consultorio)
        await sesion.commit()

        limiter = LoginRateLimiter(
            sesion=sesion,
            reloj=reloj,
            origin_hash_secret=SECRET,
            login_max_attempts=5,
            login_lockout_minutes=15,
            login_max_attempts_per_origin=20,
            trusted_proxy_hops=0,
        )

        # 6 intentos desde IP 192.168.1.50
        for _ in range(6):
            await limiter.registrar_intento_y_verificar_bloqueo(
                consultorio_id=21,
                identificador="admin",
                client_host="192.168.1.50",
                x_forwarded_for=None,
            )

        # Intento con la misma cuenta pero desde otra IP: no bloqueado
        bloqueado, _, _ = await limiter.registrar_intento_y_verificar_bloqueo(
            consultorio_id=21,
            identificador="admin",
            client_host="192.168.1.99",
            x_forwarded_for=None,
        )
        assert bloqueado is False


async def test_veinte_intentos_de_distintas_cuentas_bloquean_origen(sesiones: async_sessionmaker[AsyncSession]):
    reloj = RelojSimulado(AHORA)
    async with sesiones() as sesion:
        consultorio = crear_consultorio(id=22)
        sesion.add(consultorio)
        await sesion.commit()

        limiter = LoginRateLimiter(
            sesion=sesion,
            reloj=reloj,
            origin_hash_secret=SECRET,
            login_max_attempts=5,
            login_lockout_minutes=15,
            login_max_attempts_per_origin=20,
            trusted_proxy_hops=0,
        )

        # 20 intentos de cuentas distintas desde la misma IP
        for i in range(20):
            bloqueado, _, _ = await limiter.registrar_intento_y_verificar_bloqueo(
                consultorio_id=22,
                identificador=f"user_{i}",
                client_host="10.0.0.1",
                x_forwarded_for=None,
            )
            assert bloqueado is False

        # El intento 21 desde la misma IP, para cualquier cuenta, debe ser bloqueado por origen
        bloqueado, _, _ = await limiter.registrar_intento_y_verificar_bloqueo(
            consultorio_id=22,
            identificador="otra_cuenta",
            client_host="10.0.0.1",
            x_forwarded_for=None,
        )
        assert bloqueado is True


async def test_origen_nulo_es_contado_con_semantica_segura(sesiones: async_sessionmaker[AsyncSession]):
    reloj = RelojSimulado(AHORA)
    async with sesiones() as sesion:
        consultorio = crear_consultorio(id=23)
        sesion.add(consultorio)
        await sesion.commit()

        limiter = LoginRateLimiter(
            sesion=sesion,
            reloj=reloj,
            origin_hash_secret=SECRET,
            login_max_attempts=5,
            login_lockout_minutes=15,
            login_max_attempts_per_origin=20,
            trusted_proxy_hops=0,
        )

        # 5 intentos con client_host=None (origen no determinado)
        for _ in range(5):
            bloqueado, _, _ = await limiter.registrar_intento_y_verificar_bloqueo(
                consultorio_id=23,
                identificador="usuario_anon",
                client_host=None,
                x_forwarded_for=None,
            )
            assert bloqueado is False

        # 6to intento: bloqueado para el par con origen nulo
        bloqueado, _, _ = await limiter.registrar_intento_y_verificar_bloqueo(
            consultorio_id=23,
            identificador="usuario_anon",
            client_host=None,
            x_forwarded_for=None,
        )
        assert bloqueado is True


async def test_login_exitoso_limpia_intentos_del_par(sesiones: async_sessionmaker[AsyncSession]):
    reloj = RelojSimulado(AHORA)
    async with sesiones() as sesion:
        consultorio = crear_consultorio(id=24)
        sesion.add(consultorio)
        await sesion.commit()

        limiter = LoginRateLimiter(
            sesion=sesion,
            reloj=reloj,
            origin_hash_secret=SECRET,
            login_max_attempts=5,
            login_lockout_minutes=15,
            login_max_attempts_per_origin=20,
            trusted_proxy_hops=0,
        )

        # Acumular 4 intentos
        for _ in range(4):
            _, id_hash, orig_hash = await limiter.registrar_intento_y_verificar_bloqueo(
                consultorio_id=24,
                identificador="paciente1",
                client_host="192.168.1.20",
                x_forwarded_for=None,
            )

        # Limpiar tras login exitoso
        await limiter.limpiar_intentos_exitosos(
            consultorio_id=24,
            identificador_hash=id_hash,
            origen_hash=orig_hash,
        )

        conteo = await sesion.scalar(
            select(func.count(IntentoIngresoModel.id)).where(
                IntentoIngresoModel.consultorio_id == 24
            )
        )
        assert conteo == 0


async def test_purga_oportunista_elimina_intentos_mayores_a_24h(sesiones: async_sessionmaker[AsyncSession]):
    reloj = RelojSimulado(AHORA)
    async with sesiones() as sesion:
        consultorio = crear_consultorio(id=25)
        sesion.add(consultorio)
        await sesion.commit()

        limiter = LoginRateLimiter(
            sesion=sesion,
            reloj=reloj,
            origin_hash_secret=SECRET,
            login_max_attempts=5,
            login_lockout_minutes=15,
            login_max_attempts_per_origin=20,
            trusted_proxy_hops=0,
        )

        # Registrar un intento hace 25 horas
        hace_25h = AHORA - timedelta(hours=25)
        intento_viejo = IntentoIngresoModel(
            consultorio_id=25,
            identificador_hash="hash-antiguo",
            origen_hash="hash-origen",
            creado_en=hace_25h,
        )
        sesion.add(intento_viejo)
        await sesion.commit()

        # Nuevo intento ahora debe purgar el viejo
        await limiter.registrar_intento_y_verificar_bloqueo(
            consultorio_id=25,
            identificador="nuevo_intento",
            client_host="192.168.1.1",
            x_forwarded_for=None,
        )

        total = (
            await sesion.scalar(
                select(func.count(IntentoIngresoModel.id)).where(
                    IntentoIngresoModel.consultorio_id == 25
                )
            )
        ) or 0
        assert total == 1
