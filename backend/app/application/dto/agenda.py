from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParametrosAgenda:
    id: int
    consultorio_id: int
    zona_horaria: str
    horas_confirmacion: int
    horas_limite_paciente: int
    minutos_granularidad: int
    modo_liberacion: str
    telefono: str | None = None
    dias_anticipacion_maxima: int = 60
    max_turnos_activos_paciente: int = 2


@dataclass(frozen=True, slots=True)
class FichaAgenda:
    id: int
    consultorio_id: int
    nombre: str
    apellido: str
