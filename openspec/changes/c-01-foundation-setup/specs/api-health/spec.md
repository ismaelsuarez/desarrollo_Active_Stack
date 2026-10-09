# Spec Delta

## Purpose

Permite que el orquestador de contenedores, el hosting y los monitores sepan si el proceso de la API está vivo y atendiendo solicitudes, sin requerir autenticación.

## ADDED Requirements

### Requirement: Endpoint de salud de la API
La API SHALL exponer `GET /api/v1/health`, sin autenticación, que responde `200` con el cuerpo JSON `{"status": "ok"}` mientras el proceso atiende solicitudes.

#### Scenario: La API está en marcha
- **WHEN** un cliente sin credenciales envía `GET /api/v1/health`
- **THEN** la respuesta tiene estado `200`
- **AND** el cuerpo es exactamente `{"status": "ok"}` con tipo de contenido `application/json`

#### Scenario: Método no admitido
- **WHEN** un cliente envía `POST /api/v1/health`
- **THEN** la respuesta tiene estado `405`

### Requirement: La salud no depende de la base de datos
El endpoint de salud MUST responder sin abrir conexiones a PostgreSQL, para que un sondeo periódico no mantenga activo el cómputo de la base ni falle por una base suspendida.

#### Scenario: Base de datos inaccesible
- **WHEN** la `DATABASE_URL` configurada apunta a un servidor que no responde y un cliente envía `GET /api/v1/health`
- **THEN** la respuesta tiene estado `200` con `{"status": "ok"}`

### Requirement: La salud no expone información interna
La respuesta del endpoint de salud MUST NOT incluir versiones, variables de configuración, nombres de host ni datos de conexión.

#### Scenario: Contenido mínimo
- **WHEN** un cliente envía `GET /api/v1/health`
- **THEN** el cuerpo contiene únicamente la clave `status`
