import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit

from pydantic import SecretStr

from app.core.config import DatabaseSettings

request_id: ContextVar[str | None] = ContextVar('request_id', default=None)

_STANDARD_FIELDS = frozenset(logging.makeLogRecord({}).__dict__) | {'message', 'asctime'}


class SecretRedactionFilter:
    def __init__(self, settings: DatabaseSettings | None) -> None:
        values = set()
        if settings is not None:
            for field in type(settings).model_fields:
                value = getattr(settings, field)
                if isinstance(value, SecretStr):
                    raw = value.get_secret_value()
                    values.add(raw)
                    if '://' in raw:
                        try:
                            password = urlsplit(raw).password
                        except ValueError:
                            continue
                        if password:
                            values.add(password)
                            values.add(unquote(password))
        self.values = sorted((value for value in values if len(value) >= 4), key=len, reverse=True)

    def redact(self, encoded: str) -> str:
        for value in self.values:
            encoded = encoded.replace(json.dumps(value, ensure_ascii=False)[1:-1], '***')
        return encoded


class JsonFormatter(logging.Formatter):
    def __init__(self, settings: DatabaseSettings | None = None) -> None:
        super().__init__()
        self.redactor = SecretRedactionFilter(settings)

    def format(self, record: logging.LogRecord) -> str:
        fields = {key: value for key, value in record.__dict__.items() if key not in _STANDARD_FIELDS}
        fields.update({
            'timestamp': datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        })
        identifier = request_id.get()
        if identifier is not None:
            fields['request_id'] = identifier
        if record.exc_info:
            fields['exception'] = self.formatException(record.exc_info)
        return self.redactor.redact(json.dumps(fields, default=str, ensure_ascii=False))


def configure_logging(settings: DatabaseSettings) -> None:
    """Configure application and server output once per process configuration.

    Uvicorn installs separate access/error handlers before loading the factory.
    Replace those handlers too, so its lifecycle and access records use the same
    redaction and request context as ordinary application module loggers.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(settings))
    for name in ('app', 'tpi', 'uvicorn'):
        logger = logging.getLogger(name)
        logger.handlers[:] = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False
    for name in ('tpi.api', 'uvicorn.error', 'uvicorn.access'):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.setLevel(logging.NOTSET)
        logger.propagate = True
