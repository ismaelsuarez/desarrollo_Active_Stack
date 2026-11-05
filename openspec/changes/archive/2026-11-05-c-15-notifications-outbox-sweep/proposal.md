# Proposal

## Why

C-05 ya entrega correos de cuenta de forma durable, pero no existe un barrido que recupere trabajo pendiente tras una caída o suspensión de la API. Con C-07 y C-09 completos, hace falta esa base operativa para avisar cambios del personal y habilitar los hitos de C-16, sin un worker separado.

## What Changes

- Reutilizar `DespacharNotificacion` y ampliar la vigencia por tipo de turno/ciclo, manteniendo reclamaciones por fila, cupos y entrega al menos una vez.
- Agregar `EjecutarBarrido`, disparado por `POST /internal/barrido` autenticado con secreto y por un bucle opcional en el lifespan, con limpieza periódica y resumen de resultados.
- Agregar `ciclo` y deduplicación de notificaciones por turno/tipo/canal/ciclo, sin impedir los correos de cuenta con turno nulo.
- Programar avisos de cancelación y reprogramación por el personal dentro de la transacción del turno, con plantillas sin información de salud.
- Exponer bandeja y métricas para Recepción y Administrador, con el estado del último barrido persistido en PostgreSQL.

## Capabilities

### New Capabilities

- `notification-sweep`: ejecución acotada y concurrente del barrido, disparadores externo/en proceso y limpieza periódica.
- `notification-operations`: consulta autorizada de notificaciones e indicadores operativos persistentes.

### Modified Capabilities

- `notification-dispatch`: extender la recuperación a la vigencia de turnos, programación deduplicada por ciclo y avisos transaccionales del personal, preservando el despacho de cuenta y los cupos existentes.

## Impact

- Backend: servicios de notificaciones, puertos y UoW, `GestionTurnos`/`CicloTurnos`, repositorios, routers, schemas y lifespan; sin UI.
- Datos: una migración posterior al head `0008_turnos_core`, que incorpora el ciclo, su clave única y el registro acotado del último barrido; sin pérdida de filas históricas.
- Configuración y operación: variables `SWEEP_*`, documentación local con Mailpit y pruebas PostgreSQL/SMTP reales; sin Redis obligatorio ni dependencias pagas.
- Governance ALTO; la autenticación del disparador y la purga de credenciales requieren revisión explícita antes de apply. Q-23/Q-24/Q-25/Q-27 permanecen riesgos de producción; no bloquean local/CI (DD-31). C-16 programa hitos y correos del paciente; C-17/C-18 aportan WhatsApp e interfaz operativa; C-20 resuelve hosting y correo real.
