import logging
import re
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import request_id

_VALID_IDENTIFIER = re.compile(r'[A-Za-z0-9._-]{1,128}')


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp, logger: logging.Logger) -> None:
        self.app = app
        self.logger = logger

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        supplied = Headers(scope=scope).get('x-request-id', '')
        identifier = supplied if _VALID_IDENTIFIER.fullmatch(supplied) else uuid4().hex
        token = request_id.set(identifier)
        status = 500

        async def send_with_identifier(message: Message) -> None:
            nonlocal status
            if message['type'] == 'http.response.start':
                status = message['status']
                MutableHeaders(scope=message)['X-Request-ID'] = identifier
            await send(message)

        try:
            await self.app(scope, receive, send_with_identifier)
        finally:
            self.logger.info('HTTP request completed', extra={'status_code': status})
            request_id.reset(token)
