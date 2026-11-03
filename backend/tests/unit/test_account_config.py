import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.fixture
def settings_values(monkeypatch, tmp_path):
    # Isolate environment-backed account configuration from the developer's mail.
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    monkeypatch.setenv('SECRETS_DIR', str(tmp_path))
    return {
        'database_url': 'postgresql+asyncpg://test:private@localhost/test',
        'jwt_secret_key': 'j' * 32,
        'origin_hash_secret': 'o' * 32,
        'app_env': 'test',
        'consultorio_activo_id': 1,
    }


def test_account_defaults_allow_local_start_without_new_required_secrets(settings_values):
    settings = Settings(**settings_values)
    assert settings.email_verification_ttl_hours == 24
    assert settings.password_reset_ttl_minutes == 30
    assert settings.email_daily_limit == 500
    assert settings.email_daily_limit_account == 150
    assert settings.email_daily_alert_ratio == 0.8
    assert settings.registration_limit_per_origin == 10
    assert settings.registration_limit_global == 50
    assert settings.registration_limit_window_minutes == 60
    assert settings.account_email_limit == 3
    assert settings.account_email_window_minutes == 15
    assert settings.notification_max_attempts == 3
    assert settings.notification_claim_ttl_seconds == 120
    assert settings.smtp_timeout_seconds == 30
    assert settings.smtp_host == 'mailpit'
    assert settings.smtp_port == 587
    assert settings.smtp_starttls is True
    assert settings.smtp_user is None
    assert settings.smtp_password is None
    assert settings.smtp_from == 'Consultorio <no-reply@example.test>'
    assert settings.frontend_base_url == 'http://localhost:5173'


@pytest.mark.parametrize('account_limit', [500, 501])
def test_account_quota_must_leave_room_for_appointment_mail(settings_values, account_limit):
    with pytest.raises(ValidationError, match='EMAIL_DAILY_LIMIT_ACCOUNT'):
        Settings(**settings_values, email_daily_limit_account=account_limit)


@pytest.mark.parametrize('timeout', [120, 121])
def test_smtp_timeout_must_finish_before_claim_expires(settings_values, timeout):
    with pytest.raises(ValidationError, match='SMTP_TIMEOUT_SECONDS'):
        Settings(**settings_values, smtp_timeout_seconds=timeout)


@pytest.mark.parametrize('window', [0, 1441])
def test_registration_window_must_fit_retention(settings_values, window):
    with pytest.raises(ValidationError, match='REGISTRATION_LIMIT_WINDOW_MINUTES'):
        Settings(**settings_values, registration_limit_window_minutes=window)


@pytest.mark.parametrize('field', [
    'email_verification_ttl_hours', 'password_reset_ttl_minutes',
    'email_daily_limit', 'email_daily_limit_account',
    'registration_limit_per_origin', 'registration_limit_global',
    'account_email_limit', 'account_email_window_minutes',
    'notification_max_attempts', 'notification_claim_ttl_seconds',
    'smtp_timeout_seconds', 'smtp_port',
])
def test_account_thresholds_must_be_positive(settings_values, field):
    with pytest.raises(ValidationError):
        Settings(**settings_values, **{field: 0})


@pytest.mark.parametrize('ratio', [0, 1.1])
def test_daily_alert_ratio_is_a_positive_fraction(settings_values, ratio):
    with pytest.raises(ValidationError):
        Settings(**settings_values, email_daily_alert_ratio=ratio)


def test_mailpit_environment_and_secret_redaction(settings_values, monkeypatch):
    from app.core.logging import JsonFormatter
    import logging

    monkeypatch.setenv('SMTP_PORT', '1025')
    monkeypatch.setenv('SMTP_STARTTLS', 'false')
    monkeypatch.setenv('SMTP_PASSWORD', 'private-smtp-password')
    monkeypatch.setenv('EMAIL_DAILY_LIMIT', '200')
    settings = Settings(**settings_values, email_daily_limit_account=199,
                        registration_limit_window_minutes=1440)
    assert settings.smtp_port == 1025
    assert settings.smtp_starttls is False
    assert settings.email_daily_limit == 200
    assert settings.email_daily_limit_account == 199
    assert settings.registration_limit_window_minutes == 1440
    assert settings.smtp_password.get_secret_value() == 'private-smtp-password'
    assert 'private-smtp-password' not in repr(settings)
    record = logging.LogRecord('test', logging.INFO, __file__, 1,
                               'transport %s', ('private-smtp-password',), None)
    assert 'private-smtp-password' not in JsonFormatter(settings).format(record)
