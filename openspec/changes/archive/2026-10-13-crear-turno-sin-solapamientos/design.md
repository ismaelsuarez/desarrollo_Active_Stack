# Design: C-00 crear-turno-sin-solapamientos

## Context

Motivación y alcance: ver `proposal.md`. Requisitos: ver `specs/appointment-booking/spec.md`.

El repositorio no tiene código. Este change crea la primera carpeta `backend/` y la primera revisión de Alembic, así que sus decisiones de estructura condicionan a `c-01-foundation-setup` (propuesto, sin implementar), a C-02 y a C-07, que lo reutilizan o lo absorben.

Restricciones que dan forma al diseño:

- La garantía de no solapamiento vive en la base de datos (DD-08) y la restricción se crea a mano (regla dura 7).
- Las pruebas de repositorios y de restricciones corren contra PostgreSQL real (regla dura 3).
- Estructura y capas de `knowledge-base/08_arquitectura_propuesta.md`: `domain` no importa nada; `application` depende de `domain` y de puertos; `infrastructure` es la única capa que conoce SQLAlchemy.
- SQLAlchemy 2.x asíncrono con asyncpg, una `AsyncSession` por operación y `expire_on_commit=False` (regla dura 10).
- Máquina de desarrollo: `uv`, Docker con la imagen `postgres:17` y el puerto 5432 libre. No hay cliente `psql` en el host.

## Goals / Non-Goals

**Goals:**

- Que el rechazo de un solapamiento lo decida PostgreSQL y no una lectura previa de la aplicación.
- Que el dominio y el caso de uso no conozcan SQLAlchemy ni el código `23P01`.
- Que C-01, C-02 y C-07 puedan absorber este código sin mover archivos ni recrear la restricción.
- Que cada escenario de la especificación tenga una prueba que pase por el caso de uso.

**Non-Goals:**

- Configuración de la aplicación con `pydantic-settings`, logging, Docker Compose, imágenes y CI (C-01).
- Unidad de trabajo general, sesión por solicitud de FastAPI y semilla (C-02).
- El puerto `Reloj`: este change no toma ninguna decisión que dependa de la hora actual.
- Optimizar la consulta de disponibilidad ni crear los índices de agenda (C-07).

## Decisions

### D1. Estructura en `backend/app` con las capas de la KB 08
Se crean solo las carpetas que este change usa:

```text
backend/
├── pyproject.toml
├── alembic.ini
├── alembic/versions/
├── app/
│   ├── domain/         entities/turno.py, value_objects/estado_turno.py, errors.py
│   ├── application/    use_cases/crear_turno.py, ports/, dto/
│   └── infrastructure/ db/ (base, modelos, sesión, repositorios)
└── tests/              unit/, integration/
```

Alternativa descartada: `src/` y `tests/` en la raíz. Más corta para un único change, pero C-01 tendría que mover todo y reescribir imports y rutas de Alembic. Decisión confirmada por el dueño del proyecto.

### D2. La restricción de exclusión es el único control de solapamiento
El caso de uso no consulta los turnos existentes antes de insertar: inserta y deja que la restricción decida.

```sql
ALTER TABLE turno ADD CONSTRAINT turno_sin_solapamiento
  EXCLUDE USING gist (
    consultorio_id WITH =,
    profesional_id WITH =,
    tstzrange(inicio, fin, '[)') WITH &&
  )
  WHERE (es_sobreturno = false
         AND estado IN ('pendiente', 'confirmado', 'atendido', 'ausente'));
```

Alternativa descartada: `SELECT` previo más inserción. Dos sesiones simultáneas pasan las dos la lectura y guardan las dos; además duplica la regla en dos lugares que pueden divergir. Alternativa descartada: bloqueo explícito de la fila del profesional (`SELECT ... FOR UPDATE`): serializa correctamente, pero es una regla imperativa que cada escritura futura (reprogramar, sobreturnos) tendría que recordar; la restricción es declarativa y vale para toda escritura (DD-08).

El predicado es idéntico al de `knowledge-base/04_modelo_de_datos.md` §turno, con los seis estados de RN-18, aunque este change solo escribe `pendiente`. Con un predicado recortado C-07 tendría que eliminar y recrear la restricción. El rango `'[)'` resuelve los turnos contiguos sin lógica en la aplicación.

### D3. Traducción de `23P01` en el adaptador del repositorio
El repositorio de turnos captura `sqlalchemy.exc.IntegrityError`, lee el SQLSTATE del error original del controlador y, si es `23P01` y la restricción violada es `turno_sin_solapamiento`, lanza el error de dominio `HorarioOcupado`. Cualquier otro error de integridad se propaga sin traducir. Se comprueba también el nombre de la restricción para que una futura restricción de exclusión sobre otra tabla no se informe como "horario ocupado".

La KB 08 registra como suposición que el código es `23P01`; la primera prueba de integración del solapamiento la confirma contra PostgreSQL real.

Alternativa descartada: capturar el error en el caso de uso. Rompe la regla de capas: `application` conocería SQLAlchemy.

### D4. Esquema mínimo, con las columnas de los vecinos sin clave foránea
| Tabla | Columnas | Restricciones |
|-------|----------|---------------|
| `profesional` | `id`, `consultorio_id`, `box_id`, `nombre`, `apellido` | `UNIQUE (box_id)` (RN-10) |
| `prestacion` | `id`, `consultorio_id`, `nombre`, `duracion_min` | `UNIQUE (consultorio_id, nombre)`, `CHECK (duracion_min > 0)` |
| `turno` | `id`, `consultorio_id`, `paciente_id`, `profesional_id`, `box_id`, `prestacion_id`, `inicio`, `fin`, `estado`, `es_sobreturno`, `creado_en` | `CHECK (inicio < fin)`, `turno_sin_solapamiento` |

- Claves primarias `bigint` con identidad (DD-23). `inicio`, `fin` y `creado_en` son `timestamptz`.
- `turno.profesional_id` y `turno.prestacion_id` son claves foráneas reales. `consultorio_id`, `paciente_id` y `box_id` son `bigint NOT NULL` sin clave foránea, porque `consultorio`, `paciente` y `box` no existen todavía; la clave foránea la agregan C-02 y C-07. Es el patrón que `CHANGES.md` ya define para `token_usuario.turno_id`.
- `estado` usa un tipo enumerado de PostgreSQL con los seis valores de RN-18, valor por defecto `pendiente`. `es_sobreturno` tiene valor por defecto `false`.
- `creado_en` tiene `DEFAULT now()` en la base. La regla dura 4 prohíbe leer la hora en el dominio y en las políticas; este valor es un dato de auditoría que escribe la base y que ninguna regla de este change consulta.
- Quedan para C-02 y C-07: `usuario_id` y `activo` en `profesional`; `descripcion`, `activa` y `creada_en` en `prestacion`; hitos de confirmación, `origen`, datos de cancelación, `notas`, `creado_por_id`, `actualizado_en` e índices de agenda en `turno`.

Alternativa descartada: crear también `consultorio`, `paciente` y `box` mínimas. Da integridad referencial completa, pero absorbe medio C-02 y el change deja de ser una funcionalidad. Decisión confirmada por el dueño del proyecto. Costo aceptado: este change no valida que el paciente exista.

### D5. Modelos declarados y migración escrita a mano
Los modelos usan `DeclarativeBase`, `Mapped[...]` y `mapped_column`. `turno` declara la restricción con `ExcludeConstraint` (`using="gist"`, `where`, `name`) para que el modelo documente el esquema, pero la revisión de Alembic se escribe a mano, sin autogenerate (regla dura 7): `CREATE EXTENSION IF NOT EXISTS btree_gist`, el tipo enumerado, las tres tablas y la restricción con `op.execute`.

Una sola revisión, `0001_turnos_sin_solapamiento`, con identificador legible. El `downgrade` elimina la restricción, las tablas y el tipo enumerado, y no elimina la extensión, que puede existir antes de la migración.

Alembic se inicializa con `alembic init -t async` (DD-14). `env.py` toma la URL de la variable de entorno `DATABASE_URL` y falla con un mensaje explícito si falta; no la lee de `alembic.ini`. C-01 reemplaza esa lectura por su `DatabaseSettings` y rebasa su migración base sobre esta revisión.

Alternativa descartada: crear el esquema en las pruebas con `Base.metadata.create_all`. No ejercita la migración, que es el artefacto que llega a producción, y dejaría sin probar la restricción escrita a mano.

### D6. Puertos y transacción del caso de uso
`application` define tres puertos de lectura y escritura (`RepositorioProfesionales`, `RepositorioPrestaciones`, `RepositorioTurnos`) y un puerto `UnidadDeTrabajo`, un gestor de contexto asíncrono que expone los tres repositorios y confirma al salir sin error. El caso de uso `CrearTurno` recibe una fábrica de unidades de trabajo y en cada ejecución:

1. Valida que `inicio` tenga zona horaria.
2. Lee el profesional y la prestación filtrando por `consultorio_id`; si falta alguno lanza `ProfesionalInexistente` o `PrestacionInexistente`.
3. Calcula `fin` con una función pura del dominio.
4. Guarda el turno con el `box_id` del profesional y confirma.

El adaptador de `infrastructure/db` abre una `AsyncSession` nueva por unidad de trabajo con `async_sessionmaker(engine, expire_on_commit=False)`, de modo que dos ejecuciones simultáneas nunca comparten sesión (regla dura 10). La inserción se envía con `flush` dentro del repositorio para que el error de exclusión aparezca donde se traduce (D3).

Alternativa descartada: que el caso de uso reciba una `AsyncSession`. Es más corto, pero `application` importaría SQLAlchemy y C-02 tendría que reescribir la firma.

### D7. Entrada y salida del caso de uso
Entrada: `consultorio_id`, `paciente_id`, `profesional_id`, `prestacion_id` e `inicio`, en un DTO inmutable. Salida: la entidad `Turno` con su identificador, `fin`, `estado` y `box_id`. No hay esquema Pydantic porque no hay API; la regla dura 11 se aplica cuando C-07 exponga el endpoint.

Los errores de dominio (`HorarioOcupado`, `ProfesionalInexistente`, `PrestacionInexistente`, `InicioSinZonaHoraria`) heredan de una base común en `domain/errors.py`. Sus mensajes no incluyen datos del paciente (regla dura 13).

### D8. Pruebas contra PostgreSQL por `TEST_DATABASE_URL`
Mismo contrato que el diseño de C-01 (su D9), para que ese change lo adopte sin cambios:

- Las pruebas de integración llevan el marcador `integration` y usan la URL de `TEST_DATABASE_URL`. Si no está definida, la fixture falla con un mensaje explícito; no se omiten en silencio.
- En local, la base es un contenedor descartable de `postgres:17` publicado en el puerto 55432, documentado en el `README.md`.
- Una fixture de sesión crea una base propia (`CREATE DATABASE c00_<uuid>`), ejecuta `alembic upgrade head` sobre ella y la elimina al terminar. Así la restricción que se prueba es la de la migración.
- Las pruebas confirman de verdad sus transacciones, porque el escenario de concurrencia necesita datos visibles entre sesiones. El aislamiento entre pruebas se logra con `TRUNCATE ... RESTART IDENTITY CASCADE` después de cada una, no con una transacción revertida.
- `pytest-asyncio` en modo `auto`.

Alternativa descartada: `testcontainers`. Suma una dependencia y exige Docker dentro del proceso de pruebas; se puede adoptar después sin cambiar los tests.

### D9. Prueba de concurrencia sin dependencia del reloj
La prueba lanza dos ejecuciones de `CrearTurno` con `asyncio.gather(..., return_exceptions=True)`, cada una con su propia unidad de trabajo, y afirma tres cosas: exactamente un resultado es un `Turno`, exactamente uno es `HorarioOcupado` y la tabla tiene una sola fila para ese profesional.

El resultado no depende del orden de intercalado: si la segunda inserción llega mientras la primera no confirmó, PostgreSQL la deja esperando y la rechaza cuando la primera confirma; si llega después, la rechaza de inmediato. No hacen falta esperas ni `sleep`.

Los turnos previos en `cancelado` o `liberado` del escenario correspondiente se insertan desde la fixture de la prueba, porque ningún caso de uso de este change produce esos estados.

### D10. Dependencias y versión de Python
`backend/pyproject.toml` gestionado con `uv` y con `uv.lock` versionado. Dependencias: `sqlalchemy[asyncio]` 2.x, `asyncpg` y `alembic`; grupo de desarrollo: `pytest` y `pytest-asyncio`. `requires-python = ">=3.13"`, la versión que usa el diseño de C-01. No se agregan FastAPI, Pydantic ni `pydantic-settings`: este change no tiene API ni configuración de aplicación.

## Risks / Trade-offs

- **[Dos diseños de migración base]** `c-01-foundation-setup` define `0001_base_extensions` y este change crea `0001_turnos_sin_solapamiento` → C-01 debe rebasar su revisión sobre esta, o dejarla vacía porque la extensión ya está creada, antes de aplicarse. Queda señalado en `proposal.md` §Impact.
- **[Turnos fuera del horario de atención]** Sin RN-14 se puede crear un turno a cualquier hora → aceptado y declarado; C-06 y C-07 lo cierran.
- **[Paciente y consultorio sin integridad referencial]** `paciente_id` y `consultorio_id` aceptan cualquier entero → C-02 y C-07 agregan las claves foráneas; hasta entonces no hay datos reales.
- **[`consultorio_id` como parámetro]** Hoy lo decide quien llama → no hay ruta HTTP que lo exponga; C-03 lo toma del token (regla dura 1).
- **[Compatibilidad de asyncpg con el Python instalado]** La máquina tiene Python 3.14 → la primera tarea verifica que `uv sync` resuelve; si asyncpg no publica una rueda para esa versión, se fija Python 3.13 con `uv python pin`.
- **[SQLSTATE supuesto]** `23P01` no está verificado en fuente primaria → lo confirma la primera prueba de integración (D3).
- **[Sobreturno encima de un turno regular]** La restricción ignora los sobreturnos por diseño → no hay forma de crear uno en este change; el control de aplicación de RN-17 llega con C-12.

## Migration Plan

Primera revisión del proyecto: se aplica con `alembic upgrade head` sobre una base vacía. Reversión: `alembic downgrade base` elimina la restricción, las tablas y el tipo enumerado, y conserva la extensión `btree_gist`. No hay datos previos que migrar ni entorno publicado.
