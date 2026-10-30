import pytest

from app.domain.services.auth_crypto import (
    calcular_identificador_hash,
    calcular_origen_hash,
    calcular_token_hash,
    generar_token_opaco,
    hashear_password,
    resolver_ip_origen,
    verificar_dummy,
    verificar_password,
)

SECRET = "super-secret-key-32-bytes-minimum-012345"


def test_calcular_identificador_hash_normaliza_y_genera_hmac():
    hash1 = calcular_identificador_hash(" Admin ", SECRET)
    hash2 = calcular_identificador_hash("admin", SECRET)
    hash3 = calcular_identificador_hash("ADMIN", SECRET)
    assert hash1 == hash2 == hash3
    assert len(hash1) == 64
    assert int(hash1, 16) > 0

    hash_otro_secret = calcular_identificador_hash("admin", "otra-clave-diferente-32-bytes-minimo")
    assert hash1 != hash_otro_secret


def test_calcular_origen_hash():
    hash_ip = calcular_origen_hash("192.168.1.100", SECRET)
    assert hash_ip is not None
    assert len(hash_ip) == 64

    # None origina None
    assert calcular_origen_hash(None, SECRET) is None


def test_resolver_ip_origen_direct_hops_cero():
    assert resolver_ip_origen("192.168.1.50", "203.0.113.195", trusted_hops=0) == "192.168.1.50"
    assert resolver_ip_origen("testclient", "203.0.113.195", trusted_hops=0) == "testclient"
    assert resolver_ip_origen(None, None, trusted_hops=0) is None


def test_resolver_ip_origen_trusted_hops():
    # 1 hop: toma el último
    header = "203.0.113.1, 198.51.100.2"
    assert resolver_ip_origen("127.0.0.1", header, trusted_hops=1) == "198.51.100.2"

    # 2 hops: toma el anteúltimo
    assert resolver_ip_origen("127.0.0.1", header, trusted_hops=2) == "203.0.113.1"

    # Faltan saltos
    assert resolver_ip_origen("127.0.0.1", header, trusted_hops=3) is None

    # IP inválida en el salto confiable
    assert resolver_ip_origen("127.0.0.1", "203.0.113.1, not-an-ip", trusted_hops=1) is None

    # Sin cabecera
    assert resolver_ip_origen("127.0.0.1", None, trusted_hops=1) is None


def test_calcular_token_hash_y_generar_opaco():
    raw = generar_token_opaco(32)
    assert len(raw) >= 32
    h1 = calcular_token_hash(raw)
    h2 = calcular_token_hash(raw)
    assert h1 == h2
    assert len(h1) == 64


def test_hashear_y_verificar_password():
    password = "MiPasswordSegura123!"
    h = hashear_password(password)
    assert "$argon2id$" in h
    assert verificar_password(password, h) is True
    assert verificar_password("PasswordIncorrecta", h) is False


def test_verificar_dummy_ejecuta_y_siempre_es_falso():
    # Debe ejecutar verify con el hash dummy precalculado sin fallar y retornar False
    resultado = verificar_dummy("cualquier_password")
    assert resultado is False
