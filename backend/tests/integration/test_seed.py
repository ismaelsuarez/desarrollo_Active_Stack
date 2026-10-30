import os
import subprocess
import sys
from pathlib import Path

import pytest
from pwdlib import PasswordHash
from pydantic import SecretStr
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import SeedSettings
from app.infrastructure.db.models import ConsultorioModel, UsuarioModel
from tests.integration.conftest import BACKEND

pytestmark = pytest.mark.integration

PASSWORD_HASH = PasswordHash.recommended()


async def test_seed_ejecucion_idempotente(url_base: str, sesiones: async_sessionmaker[AsyncSession]):
    from app.seed import sembrar

    settings = SeedSettings(
        database_url=url_base,
        consultorio_activo_id=1,
        bootstrap_admin_email="admin@test.com",
        bootstrap_admin_password=SecretStr("admin-secure-password-123"),
    )

    # 1. Primera ejecución: crea consultorio y usuario
    await sembrar(settings)

    async with sesiones() as sesion:
        consultorio = await sesion.scalar(select(ConsultorioModel).where(ConsultorioModel.id == 1))
        assert consultorio is not None
        assert consultorio.id == 1
        assert consultorio.nombre == "Consultorio Odontológico"
        assert consultorio.horas_confirmacion == 48

        admin = await sesion.scalar(
            select(UsuarioModel).where(UsuarioModel.consultorio_id == 1, UsuarioModel.rol == "administrador")
        )
        assert admin is not None
        assert admin.email == "admin@test.com"
        assert admin.nombre_usuario == "admin"
        assert admin.email_verificado is True
        assert admin.aviso_privacidad_aceptado_en is None
        assert PASSWORD_HASH.verify("admin-secure-password-123", admin.password_hash)

        # Verificar que la secuencia de consultorio no choca con inserciones futuras
        nuevo_id = await sesion.scalar(
            text(
                "INSERT INTO consultorio (nombre, zona_horaria, modo_liberacion, horas_confirmacion, "
                "horas_recordatorio, horas_liberacion, horas_limite_paciente, minutos_granularidad, "
                "dias_anticipacion_maxima, max_turnos_activos_paciente, activo, creado_en, actualizado_en) "
                "VALUES ('Otro Consultorio', 'America/Argentina/Buenos_Aires', 'automatico', 48, 24, 12, 24, 15, 60, 2, true, now(), now()) "
                "RETURNING id"
            )
        )
        assert nuevo_id > 1

    # 2. Segunda ejecución: idempotente, no duplica ni falla
    await sembrar(settings)

    async with sesiones() as sesion:
        conteo_consultorios = await sesion.scalar(
            text("SELECT count(*) FROM consultorio WHERE id = 1")
        )
        assert conteo_consultorios == 1

        conteo_admins = await sesion.scalar(
            text("SELECT count(*) FROM usuario WHERE consultorio_id = 1 AND rol = 'administrador'")
        )
        assert conteo_admins == 1


def test_seed_cli_ejecucion_aislada(url_base: str, tmp_path: Path):
    """Verifica que 'python -m app.seed' funciona sin variables de API (JWT_SECRET_KEY, APP_ENV)."""
    env = {
        "PATH": os.environ.get("PATH", ""),
        "DATABASE_URL": url_base,
        "CONSULTORIO_ACTIVO_ID": "1",
        "BOOTSTRAP_ADMIN_EMAIL": "cli-admin@consultorio.com",
        "BOOTSTRAP_ADMIN_PASSWORD": "cli-super-password-456",
    }
    resultado = subprocess.run(
        [sys.executable, "-m", "app.seed"],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, f"Error: {resultado.stderr}"
    assert "Semilla completada exitosamente" in resultado.stdout
