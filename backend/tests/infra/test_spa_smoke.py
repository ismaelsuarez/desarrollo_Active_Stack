from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from threading import Thread

import pytest


def modulo_smoke():
    path = Path(__file__).resolve().parents[3] / 'scripts' / 'check_spa_smoke.py'
    spec = spec_from_file_location('check_spa_smoke', path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('defecto', [None, 'ruta', 'api', 'asset'])
def test_verifica_spa_y_preserva_errores_api(defecto):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/api/v1/no-existe':
                status, content_type, body = (200, 'text/html', '<html>SPA</html>') if defecto == 'api' else (404, 'application/json', '{"detail":"Not Found"}')
            elif self.path == '/assets/no-existe.js':
                status, content_type, body = (200, 'text/html', '<html>SPA</html>') if defecto == 'asset' else (404, 'application/json', '{}')
            elif self.path == '/reservar' and defecto == 'ruta':
                status, content_type, body = (404, 'application/json', '{}')
            else:
                status, content_type, body = (200, 'text/html', '<html>SPA</html>')
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.end_headers()
            self.wfile.write(body.encode())

        def log_message(self, *args):
            pass

    servidor = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    hilo = Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    try:
        modulo = modulo_smoke()
        if defecto is None:
            modulo.verificar_spa(f'127.0.0.1:{servidor.server_port}')
        else:
            with pytest.raises(AssertionError):
                modulo.verificar_spa(f'127.0.0.1:{servidor.server_port}')
    finally:
        servidor.shutdown()
        hilo.join()
        servidor.server_close()
