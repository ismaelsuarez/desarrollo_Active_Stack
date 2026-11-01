# Design: c-04-abac-policies

## Context

La autenticación base y el modelo de identidad `Principal` (con `usuario_id`, `consultorio_id` y `rol`) fueron implementados en C-03. En la capa de dominio ya existen las entidades `Turno` y el enumerado `EstadoTurno`.

Para asegurar los requisitos de seguridad y las reglas del consultorio odontológico, el sistema requiere una capa de autorización basada en atributos (ABAC) que evalúe las particularidades de cada recurso (propiedad de agenda, titularidad de turno, aislamiento multi-inquilino, estados del turno y ventanas temporales).

Restricciones que rigen este diseño:
- **DD-04**: Se implementa como funciones puras en la capa de dominio, no como un motor genérico complejo (ni OPA ni Casbin).
- **Regla dura 4**: NUNCA usar `datetime.now()` ni `utcnow()` en el dominio o políticas; el instante `ahora` se inyecta mediante el contexto de acceso.
- **Regla dura 6**: NUNCA autorizar ad hoc dentro de un router; RBAC en dependencias y ABAC como funciones puras en casos de uso.
- **Regla dura 13**: NUNCA registrar ni devolver datos personales sin necesidad; los motivos de rechazo se minimizan y nunca exponen DNI ni datos sensibles.

## Goals / Non-Goals

**Goals:**
- Implementar funciones de política puras y deterministas para los cuatro atributos de la v1 (A1, A2, A3, A4) según KB 11.
- Proveer un punto de entrada centralizado `autorizar(usuario, accion, recurso, contexto)` con política estricta de denegación por defecto (default-deny).
- Producir un objeto inmutable `Decision` con código HTTP sugerido (404 para evitar revelación de existencia, 403 para acciones denegadas dentro del consultorio conocido).
- Cobertura de pruebas unitarias al 100% sobre la matriz de roles, acciones y atributos, incluyendo límites exactos de tiempo (a $\pm 1$ segundo).

**Non-Goals:**
- No incluye integración directa con controladores HTTP / routers de FastAPI (eso lo consumen los casos de uso en C-05, C-06, C-07).
- No realiza consultas a base de datos ni interactúa con SQLAlchemy (la capa de aplicación carga los datos y los pasa a las funciones puras).
- No resuelve conflictos de solapamiento de horarios (eso pertenece al repositorio y a la restricción PostgreSQL en C-07).

## Decisions

### D1. Organización modular del paquete `app.domain.policies`

Se divide la lógica de políticas en módulos cohesivos según el atributo y la entidad evaluada:

```text
backend/app/domain/
├── policies/
│   ├── __init__.py          # Exporta autorizar, Accion, Decision, ContextoAcceso
│   ├── consultorio.py       # A2: mismo_consultorio (siempre se evalúa primero)
│   ├── turno.py             # A1, A3, A4: titularidad, modificabilidad, transiciones y ventanas
│   ├── sobreturno.py        # Autorización y respuesta de sobreturnos
│   ├── paciente.py          # Visualización y edición de fichas, vinculación
│   ├── indicadores.py       # Acceso a métricas de ausentismo
│   └── acceso.py            # Punto de entrada 'autorizar' y matriz de permisos
└── value_objects/
    ├── accion.py            # Catálogo de acciones (Accion Enum)
    ├── decision.py          # Objeto inmutable Decision
    ├── intervalo.py         # Value object Intervalo de tiempo
    └── contexto_acceso.py   # ContextoAcceso inyectado
```

*Alternativa descartada*: Monolito `policies.py`. Un único archivo se volvería difícil de mantener a medida que se agreguen las reglas de todos los módulos.

### D2. Modelo de `Decision` y `ContextoAcceso`

Se define la estructura `Decision` como dataclass inmutable:
```python
@dataclass(frozen=True, slots=True)
class Decision:
    permitido: bool
    motivo: str | None = None
    codigo_http: int | None = None
```

Y el contenedor de contexto inyectado `ContextoAcceso`:
```python
@dataclass(frozen=True, slots=True)
class ContextoAcceso:
    ahora: datetime
    ficha_vigente_id: int | None = None
    horas_limite_cancelacion: int = 24
    consultorio_modo_manual: bool = False
    turno_sin_confirmar: bool = False
    turnos_del_profesional: frozenset[int] = frozenset()
```

*Razón*: El token de acceso nunca incluye la ficha del paciente (RN-06), ni la base de datos se consulta dentro de las políticas puras. La capa de aplicación inyecta el `ahora` del puerto `Reloj` y la `ficha_vigente_id` cargada previamente de la base de datos.

### D3. Regla canónica de códigos de respuesta HTTP

Se establece la correspondencia fija dictada por KB 11:
1. **404 Not Found**:
   - Cuando falla A2 (`mismo_consultorio`), independientemente del rol.
   - Cuando un paciente intenta acceder a un turno o ficha ajena (`es_titular_del_turno` o `puede_ver_paciente` falso).
   - *Justificación*: Evita ataques de enumeración donde un atacante pueda inferir la existencia de turnos o pacientes ajenos o de otro inquilino.
2. **403 Forbidden**:
   - Cuando la existencia del recurso ya es conocida dentro del consultorio pero el usuario no tiene privilegios (ej. profesional intentando editar turno de otro profesional).
   - Cuando falla una regla por estado (A3, ej. turno inmutable o transición prohibida).
   - Cuando falla una regla por ventana de tiempo (A4, ej. cancelación fuera del plazo de 24h o marcar atendido antes del inicio).
   - Cuando un rol no autorizado intenta una acción (ej. paciente intentando crear sobreturno o rol administrativo).
3. **409 Conflict**:
   - NO es un código de política ABAC. Se reserva para colisiones de concurrencia al persistir (horario ocupado, exclusión en DB).

### D4. Matriz de transiciones de estado de turnos (RN-18)

Las transiciones válidas se representan de forma inmutable mediante un grafo dirigido en `app.domain.policies.turno`:
```python
TRANSICIONES_PERMITIDAS: dict[EstadoTurno, frozenset[EstadoTurno]] = {
    EstadoTurno.PENDIENTE: frozenset({
        EstadoTurno.CONFIRMADO,
        EstadoTurno.ATENDIDO,
        EstadoTurno.AUSENTE,
        EstadoTurno.CANCELADO,
        EstadoTurno.LIBERADO,
    }),
    EstadoTurno.CONFIRMADO: frozenset({
        EstadoTurno.ATENDIDO,
        EstadoTurno.AUSENTE,
        EstadoTurno.CANCELADO,
    }),
    EstadoTurno.AUSENTE: frozenset({
        EstadoTurno.ATENDIDO,  # Únicamente corregir_ausente
    }),
    EstadoTurno.ATENDIDO: frozenset(),   # Estado terminal
    EstadoTurno.CANCELADO: frozenset(),  # Estado terminal
    EstadoTurno.LIBERADO: frozenset(),   # Estado terminal
}
```

## Risks / Trade-offs

- **[Riesgo] Contexto incompleto en la capa de aplicación**: Si un caso de uso no provee `ahora` o la `ficha_vigente_id` cuando la política lo requiere, la evaluación podría fallar o comportarse incorrectamente.
  → *Mitigación*: Validación explícita en `ContextoAcceso` o en las funciones específicas, denegando por defecto si falta información requerida para tomar una decisión segura.
- **[Riesgo] Discrepancia entre RBAC del endpoint y ABAC del caso de uso**: Que un endpoint permita un rol por RBAC pero la matriz ABAC no lo contemple.
  → *Mitigación*: Pruebas cruzadas y contrato unificado: el catálogo de acciones es el único lenguaje compartido entre la capa de presentación y el dominio.

## Migration Plan

No requiere migraciones de base de datos ni cambios de esquema. Al ser código puro de dominio, se despliega junto con el backend y queda listo para ser consumido inmediatamente por los casos de uso a implementarse en C-05, C-06 y C-07.
