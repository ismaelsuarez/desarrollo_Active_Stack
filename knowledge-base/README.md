# Sistema de Turnos y Agenda Odontológica — Base de Conocimiento

Base de conocimiento generada a partir del Discovery confirmado (`discovery/discovery.md`, actualizado el 2026-10-05) y de las decisiones confirmadas por el usuario en la fase de base de conocimiento. Cubre un sistema web de turnos y agenda para un consultorio odontológico de 2 a 5 profesionales. La v1 atiende un único consultorio y se entrega el 2026-10-12.

## Índice de Archivos

| Archivo | Contenido |
|---------|-----------|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Propósito, prioridades de calidad, objetivos por actor, cinco casos de uso confirmados, alcance v1, fuera de alcance y métricas de éxito. |
| [02_descripcion_general.md](02_descripcion_general.md) | Stack obligatorio, arquitectura general, integraciones externas y resumen de la API REST. |
| [03_actores_y_roles.md](03_actores_y_roles.md) | Actores, matriz RBAC de cinco roles, permisos y rutas públicas. |
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | Entidades con `consultorio_id`, ERD en Mermaid, restricciones (solapamientos, DNI único), datos semilla y catálogo inicial de prestaciones. |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | Reglas RN-01 a RN-58 por dominio: cuentas, agenda, turnos, confirmación y liberación, cancelación, sobreturnos, ausentismo, pacientes, comunicación y protección de datos. |
| [06_funcionalidades.md](06_funcionalidades.md) | Historias de usuario por épica, con versión (v1 o backlog), criterios de aceptación y trazabilidad con los casos de uso. |
| [07_flujos_principales.md](07_flujos_principales.md) | Diez flujos extremo a extremo con diagramas de secuencia y estados: registro, ingreso, reserva, confirmación, liberación, cancelación, sobreturno, ausencias, WhatsApp e indicador. |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Patrones, estructura de directorios, trabajos en segundo plano, seguridad, variables de entorno y estrategia de pruebas. |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | Decisiones confirmadas (DD), supuestos sin confirmar (SU), riesgos y conflictos entre fuentes resueltos. |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | Inconsistencias y preguntas abiertas priorizadas, con qué bloquean y quién decide. |
| [11_politicas_de_acceso_abac.md](11_politicas_de_acceso_abac.md) | Extra: cuatro atributos ABAC, catálogo de funciones de política y matriz de decisión rol por acción por atributo. |
| [12_devops_y_despliegue.md](12_devops_y_despliegue.md) | Extra: servicios de Docker Compose, enfoque de hosting gratuito, configuración SMTP, trabajos programados, respaldo y lista de verificación. |

## Quick Start para Desarrolladores

1. Entender el dominio → [01](01_vision_y_objetivos.md), [03](03_actores_y_roles.md)
2. Entender los datos → [04](04_modelo_de_datos.md)
3. Entender las reglas → [05](05_reglas_de_negocio.md), [11](11_politicas_de_acceso_abac.md)
4. Entender la arquitectura → [02](02_descripcion_general.md), [08](08_arquitectura_propuesta.md), [12](12_devops_y_despliegue.md)
5. Implementar → [07](07_flujos_principales.md), [06](06_funcionalidades.md)
6. Antes de codificar → [09](09_decisiones_y_supuestos.md), [10](10_preguntas_abiertas.md)

## Convenciones

- Códigos de reglas: `RN-NN`. Historias: `US-NNN`. Casos de uso confirmados: `CU-1` a `CU-5`. Decisiones: `DD-NN`. Supuestos sin confirmar: `SU-NN`. Preguntas: `Q-NN`.
- Roles en el código: `administrador`, `recepcion`, `profesional`, `paciente`, `administrativo`.
- Estados del turno: `pendiente`, `confirmado`, `ausente`, `atendido`, `cancelado`, `liberado`.
- Idioma: español neutro. Los identificadores técnicos pueden estar en inglés.

## Resumen Ejecutivo

Sistema web (React, TypeScript, Vite; FastAPI, PostgreSQL; Redis opcional) para que un consultorio odontológico reduzca las ausencias, automatice la confirmación de turnos y controle los sobreturnos. El paciente se registra desde un enlace público, verifica su correo y gestiona sus turnos hasta 24 horas antes. El sistema pide confirmación a las 48 horas, recuerda a las 24 y libera el turno sin confirmar a las 12 horas (o lo deja "sin confirmar" en modo manual). El correo es automático y el WhatsApp es semimanual. La autorización combina cinco roles con políticas por atributos. El modelo de datos está preparado para varios consultorios, pero la v1 opera con uno. Presupuesto cero y entrega el 2026-10-12.
