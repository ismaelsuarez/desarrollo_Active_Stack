"""Configuración de los dos disparadores, sin secretos en diagnósticos."""
import pytest
from pydantic import ValidationError

from app.core.config import Settings


def settings(**extra):
    return Settings(database_url="postgresql+asyncpg://test:test@localhost/test",
                    jwt_secret_key="j" * 32, origin_hash_secret="o" * 32,
                    app_env="test", consultorio_activo_id=1, **extra)


def test_sweep_defaults_leave_both_triggers_opt_in():
    config = settings()
    assert config.sweep_shared_secret is None
    assert config.sweep_in_process_enabled is False
    assert config.sweeper_interval_seconds == 300


@pytest.mark.parametrize("interval", [0, -1])
def test_sweep_interval_must_be_positive_without_echoing_secret(interval):
    with pytest.raises(ValidationError) as error:
        settings(sweeper_interval_seconds=interval, sweep_shared_secret="private-sweep-test")
    assert "SWEEPER_INTERVAL_SECONDS" in str(error.value)
    assert "private-sweep-test" not in str(error.value)


@pytest.mark.parametrize("secret", [None, ""])
def test_empty_http_secret_does_not_disable_local_loop(secret):
    config = settings(sweep_shared_secret=secret, sweep_in_process_enabled=True)
    assert config.sweep_in_process_enabled
    assert config.sweep_shared_secret is None or config.sweep_shared_secret.get_secret_value() == ""


def test_sweep_secret_is_redacted_and_aliases_are_supported():
    config = settings(SWEEP_SHARED_SECRET="private-sweep-test", SWEEPER_INTERVAL_SECONDS=12,
                      SWEEP_IN_PROCESS_ENABLED=True)
    assert config.sweep_shared_secret.get_secret_value() == "private-sweep-test"
    assert "private-sweep-test" not in repr(config)
    assert config.sweeper_interval_seconds == 12


@pytest.mark.parametrize("timeout,ttl", [(120, 120), (121, 120)])
def test_existing_smtp_timeout_guard_applies_to_sweep(timeout, ttl):
    with pytest.raises(ValidationError):
        settings(smtp_timeout_seconds=timeout, notification_claim_ttl_seconds=ttl)
