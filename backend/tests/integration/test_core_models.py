from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.ports.reloj import RelojSimulado
from app.infrastructure.db.models import (
    ConsultorioModel,
    PacienteModel,
    RefreshTokenModel,
    TokenUsuarioModel,
    UsuarioModel,
)

pytestmark = pytest.mark.integration

AHORA = datetime(2026, 10, 30, 12, 0, 0, tzinfo=timezone.utc)
RELOJ = RelojSimulado(AHORA)


def crear_consultorio_ejemplo(id: int = 1) -> ConsultorioModel:
    return ConsultorioModel(
        id=id,
        nombre="Consultorio Centro",
        telefono="1122334455",
        direccion="Av. Corrientes 1234",
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
        creado_en=RELOJ.ahora(),
        actualizado_en=RELOJ.ahora(),
    )


async def test_crear_consultorio_valido(sesiones: async_sessionmaker[AsyncSession]):
    async with sesiones() as sesion:
        consultorio = crear_consultorio_ejemplo(id=1)
        sesion.add(consultorio)
        await sesion.commit()

        resultado = await sesion.scalar(select(ConsultorioModel).where(ConsultorioModel.id == 1))
        assert resultado is not None
        assert resultado.nombre == "Consultorio Centro"
        assert resultado.horas_confirmacion == 48


async def test_consultorio_rechaza_horas_invalidas(sesiones: async_sessionmaker[AsyncSession]):
    async with sesiones() as sesion:
        # horas_liberacion (30) >= horas_recordatorio (24) violando ck_consultorio_horas_orden
        consultorio = crear_consultorio_ejemplo(id=2)
        consultorio.horas_recordatorio = 24
        consultorio.horas_liberacion = 30
        sesion.add(consultorio)
        with pytest.raises((IntegrityError, DBAPIError)):
            await sesion.commit()


async def test_consultorio_rechaza_granularidad_fuera_de_rango(sesiones: async_sessionmaker[AsyncSession]):
    async with sesiones() as sesion:
        consultorio = crear_consultorio_ejemplo(id=3)
        consultorio.minutos_granularidad = 3  # Menor que 5
        sesion.add(consultorio)
        with pytest.raises((IntegrityError, DBAPIError)):
            await sesion.commit()


async def test_usuario_unicidad_y_normalizacion(sesiones: async_sessionmaker[AsyncSession]):
    async with sesiones() as sesion:
        consultorio = crear_consultorio_ejemplo(id=1)
        sesion.add(consultorio)
        await sesion.commit()

    async with sesiones() as sesion:
        # Intento de insertar usuario sin normalizar (con mayúscula o espacio)
        usuario_invalido = UsuarioModel(
            consultorio_id=1,
            nombre_usuario="Admin ",
            email="admin@consultorio.com",
            password_hash="argon2-hash",
            rol="administrador",
            creado_en=RELOJ.ahora(),
            actualizado_en=RELOJ.ahora(),
        )
        sesion.add(usuario_invalido)
        with pytest.raises((IntegrityError, DBAPIError)):
            await sesion.commit()

    async with sesiones() as sesion:
        usuario_valido = UsuarioModel(
            consultorio_id=1,
            nombre_usuario="admin",
            email="admin@consultorio.com",
            password_hash="argon2-hash",
            rol="administrador",
            creado_en=RELOJ.ahora(),
            actualizado_en=RELOJ.ahora(),
        )
        sesion.add(usuario_valido)
        await sesion.commit()

    async with sesiones() as sesion:
        # Unicidad de nombre de usuario en mismo consultorio
        usuario_duplicado = UsuarioModel(
            consultorio_id=1,
            nombre_usuario="admin",
            email="otro@consultorio.com",
            password_hash="argon2-hash-2",
            rol="administrador",
            creado_en=RELOJ.ahora(),
            actualizado_en=RELOJ.ahora(),
        )
        sesion.add(usuario_duplicado)
        with pytest.raises((IntegrityError, DBAPIError)):
            await sesion.commit()


async def test_usuario_paciente_aviso_privacidad(sesiones: async_sessionmaker[AsyncSession]):
    async with sesiones() as sesion:
        consultorio = crear_consultorio_ejemplo(id=1)
        sesion.add(consultorio)
        await sesion.commit()

    async with sesiones() as sesion:
        # Paciente sin consentimiento debe fallar
        paciente_sin_consentimiento = UsuarioModel(
            consultorio_id=1,
            nombre_usuario="paciente1",
            email="paciente1@consultorio.com",
            password_hash="argon2-hash",
            rol="paciente",
            aviso_privacidad_aceptado_en=None,
            aviso_privacidad_version=None,
            creado_en=RELOJ.ahora(),
            actualizado_en=RELOJ.ahora(),
        )
        sesion.add(paciente_sin_consentimiento)
        with pytest.raises((IntegrityError, DBAPIError)):
            await sesion.commit()

    async with sesiones() as sesion:
        # Inconsistencia entre fecha y versión
        paciente_inconsistente = UsuarioModel(
            consultorio_id=1,
            nombre_usuario="paciente1",
            email="paciente1@consultorio.com",
            password_hash="argon2-hash",
            rol="paciente",
            aviso_privacidad_aceptado_en=RELOJ.ahora(),
            aviso_privacidad_version=None,
            creado_en=RELOJ.ahora(),
            actualizado_en=RELOJ.ahora(),
        )
        sesion.add(paciente_inconsistente)
        with pytest.raises((IntegrityError, DBAPIError)):
            await sesion.commit()

    async with sesiones() as sesion:
        # Paciente válido con consentimiento
        paciente_valido = UsuarioModel(
            consultorio_id=1,
            nombre_usuario="paciente1",
            email="paciente1@consultorio.com",
            password_hash="argon2-hash",
            rol="paciente",
            aviso_privacidad_aceptado_en=RELOJ.ahora(),
            aviso_privacidad_version="1.0",
            creado_en=RELOJ.ahora(),
            actualizado_en=RELOJ.ahora(),
        )
        sesion.add(paciente_valido)
        await sesion.commit()


async def test_paciente_dni_numerico_y_unicidad(sesiones: async_sessionmaker[AsyncSession]):
    async with sesiones() as sesion:
        consultorio = crear_consultorio_ejemplo(id=1)
        sesion.add(consultorio)
        await sesion.commit()

    async with sesiones() as sesion:
        # DNI con puntos debe fallar por check constraint
        paciente_dni_invalido = PacienteModel(
            consultorio_id=1,
            nombre="Juan",
            apellido="Perez",
            dni="12.345.678",
            creado_en=RELOJ.ahora(),
            actualizado_en=RELOJ.ahora(),
        )
        sesion.add(paciente_dni_invalido)
        with pytest.raises((IntegrityError, DBAPIError)):
            await sesion.commit()

    async with sesiones() as sesion:
        paciente_valido = PacienteModel(
            consultorio_id=1,
            nombre="Juan",
            apellido="Perez",
            dni="12345678",
            creado_en=RELOJ.ahora(),
            actualizado_en=RELOJ.ahora(),
        )
        sesion.add(paciente_valido)
        await sesion.commit()

    async with sesiones() as sesion:
        # DNI duplicado en el mismo consultorio
        paciente_duplicado = PacienteModel(
            consultorio_id=1,
            nombre="Otro",
            apellido="Perez",
            dni="12345678",
            creado_en=RELOJ.ahora(),
            actualizado_en=RELOJ.ahora(),
        )
        sesion.add(paciente_duplicado)
        with pytest.raises((IntegrityError, DBAPIError)):
            await sesion.commit()


async def test_tokens_y_refresh_tokens(sesiones: async_sessionmaker[AsyncSession]):
    async with sesiones() as sesion:
        consultorio = crear_consultorio_ejemplo(id=1)
        sesion.add(consultorio)
        usuario = UsuarioModel(
            consultorio_id=1,
            nombre_usuario="usuario1",
            email="usuario1@consultorio.com",
            password_hash="argon2-hash",
            rol="recepcion",
            creado_en=RELOJ.ahora(),
            actualizado_en=RELOJ.ahora(),
        )
        sesion.add(usuario)
        await sesion.commit()

        # TokenUsuario con turno_id nulo sin FK
        token = TokenUsuarioModel(
            consultorio_id=1,
            usuario_id=usuario.id,
            tipo="verificar_email",
            token_hash="hash-token-unico-123",
            expira_en=RELOJ.ahora(),
            creado_en=RELOJ.ahora(),
        )
        sesion.add(token)

        # RefreshToken
        refresh = RefreshTokenModel(
            consultorio_id=1,
            usuario_id=usuario.id,
            token_hash="hash-refresh-unico-456",
            expira_en=RELOJ.ahora(),
            creado_en=RELOJ.ahora(),
        )
        sesion.add(refresh)
        await sesion.commit()

        assert token.id is not None
        assert refresh.id is not None
