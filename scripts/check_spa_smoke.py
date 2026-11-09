"""Comprueba la SPA y sus límites contra la API que sirve el build."""
import json
import sys
from urllib.error import HTTPError
from urllib.request import urlopen


def verificar_spa(endpoint: str) -> None:
    def consultar(path: str) -> tuple[int, str, bytes]:
        try:
            response = urlopen(f'http://{endpoint}{path}', timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.headers.get_content_type(), response.read()

    for path in ('/', '/reservar'):
        status, content_type, body = consultar(path)
        assert status == 200 and content_type == 'text/html' and b'<html' in body.lower(), f'SPA inválida en {path}'
    status, content_type, body = consultar('/api/v1/no-existe')
    assert status == 404 and content_type == 'application/json', 'La API inexistente no devolvió 404 JSON'
    assert isinstance(json.loads(body), dict), 'Respuesta de API no es un objeto JSON'
    status, _, _ = consultar('/assets/no-existe.js')
    assert status == 404, 'Un recurso inexistente no devolvió 404'


if __name__ == '__main__':
    verificar_spa(sys.argv[1])
