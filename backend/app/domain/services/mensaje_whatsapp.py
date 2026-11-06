from datetime import datetime
import re
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from app.domain.value_objects.telefono import normalizar_telefono


def construir_mensaje_whatsapp(
    *, telefono: str, paciente: str, fecha_hora: datetime,
    profesional: str, consultorio: str, accion: str,
    zona_horaria: str | None = None, liberacion_automatica: bool = False,
) -> tuple[str, str]:
    if re.fullmatch(r'[1-9][0-9]{7,14}', telefono, flags=re.ASCII):
        numero = telefono
    else:
        numero = normalizar_telefono(telefono)
    if numero is None:
        raise ValueError('Teléfono no utilizable')
    if zona_horaria is not None:
        if fecha_hora.utcoffset() is None:
            raise ValueError('Fecha sin zona horaria')
        fecha_hora = fecha_hora.astimezone(ZoneInfo(zona_horaria))
    hechos = {'liberacion': 'liberado', 'cancelacion_por_personal': 'cancelado',
              'reprogramacion_por_personal': 'reprogramado'}
    if accion in hechos:
        situacion = f'fue {hechos[accion]} y corresponde al'
    elif accion in {'confirmar', 'recordar'}:
        situacion = 'es el'
    else:
        raise ValueError('Acción de WhatsApp no admitida')
    mensaje = (
        f'Hola {paciente}, tu turno en {consultorio} con {profesional} {situacion} '
        f'{fecha_hora:%d/%m/%Y} a las {fecha_hora:%H:%M}.'
    )
    if accion == 'confirmar':
        mensaje += ' Por favor, confirmá tu turno.'
    elif accion == 'recordar':
        mensaje += ' Por favor, confirmá tu turno.'
        if liberacion_automatica:
            mensaje += ' Si no confirmás, tu turno podría ser liberado.'
    return mensaje, f'https://wa.me/{numero}?{urlencode({"text": mensaje})}'
