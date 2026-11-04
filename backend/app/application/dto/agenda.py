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


@dataclass(frozen=True, slots=True)
class FichaAgenda:
    id: int
    consultorio_id: int
    nombre: str
    apellido: str
