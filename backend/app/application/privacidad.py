"""Copia versionada del borrador de KB 13; no implica aprobación legal."""

VERSION_AVISO = '2026-10-borrador'

TEXTO_AVISO = """**Aviso de privacidad**

Para crear tu cuenta y gestionar tus turnos, [NOMBRE DEL CONSULTORIO], con domicilio en [DOMICILIO], guarda los datos que cargás en este formulario en su base de datos de pacientes.

**Qué datos pedimos.** Nombre y apellido, DNI, teléfono, correo electrónico, usuario y contraseña son obligatorios: sin ellos no podemos crear tu cuenta ni darte turnos en línea. La obra social es opcional.

**Para qué los usamos.** Para identificarte, darte y gestionar turnos, y avisarte por correo o por WhatsApp sobre tus turnos (confirmaciones, recordatorios y cambios). No los usamos para otra finalidad.

**Quién los ve.** El personal del consultorio que los necesita para atenderte. No los vendemos ni los compartimos para otros fines; los guardamos y enviamos a través de los proveedores de infraestructura que usa el consultorio (alojamiento de la base de datos y envío de correo).

**Tus derechos.** Podés pedir acceder a tus datos, corregirlos o que se supriman escribiendo a [CONTACTO]. El acceso es gratuito a intervalos no menores de seis meses, salvo que acredites un interés legítimo (Ley 25.326, artículo 14).

La Agencia de Acceso a la Información Pública, órgano de control de la Ley 25.326, atiende las denuncias y reclamos por el incumplimiento de las normas de protección de datos personales.

☐ Leí el aviso de privacidad y acepto que el consultorio trate mis datos para gestionar mis turnos."""


def renderizar_aviso(nombre: str, direccion: str | None, telefono: str | None) -> dict[str, str]:
    texto = TEXTO_AVISO.replace('[NOMBRE DEL CONSULTORIO]', nombre)
    texto = texto.replace('[DOMICILIO]', direccion or '[DOMICILIO]')
    texto = texto.replace('[CONTACTO]', telefono or '[CONTACTO]')
    return {'texto': texto, 'version': VERSION_AVISO}


def aviso_completo(texto: str) -> bool:
    """Detecta marcadores pendientes antes de habilitar el aviso publicado."""
    return '[' not in texto and ']' not in texto
