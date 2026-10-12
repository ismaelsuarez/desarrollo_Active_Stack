# 13. Aviso de privacidad del registro (borrador)

> **Borrador sin revisión legal.** Lo redactó el equipo técnico a partir del texto de la Ley 25.326 (artículos 5, 6, 14 y 16). No debe mostrarse a pacientes reales hasta que lo revise un profesional del derecho y se completen los datos del responsable. Regla relacionada: RN-65. Decisión: DD-28 en [09](09_decisiones_y_supuestos.md).

Versión del aviso: `2026-10-borrador`. El servidor rechaza un registro que acepta otra versión. Cada cambio del texto cambia la versión.

Una sola fuente: el texto de abajo y su versión se copian al backend, que los sirve en `GET /api/v1/publico/aviso-privacidad`. El frontend muestra lo que devuelve la API y reenvía la versión que mostró; no guarda una copia del texto. El servidor reemplaza `[NOMBRE DEL CONSULTORIO]`, `[DOMICILIO]` y `[CONTACTO]` por `consultorio.nombre`, `consultorio.direccion` y `consultorio.telefono`; si alguno es nulo, el marcador queda en el texto servido, y una prueba con `APP_ENV=production` falla si el texto servido todavía contiene un marcador entre corchetes (RN-65).

## Datos que faltan

| Dato | Estado |
|------|--------|
| Nombre o razón social del responsable de la base de datos | Pendiente (Q-18 en [10](10_preguntas_abiertas.md)) |
| Domicilio del responsable | Pendiente (Q-18) |
| Medio de contacto para ejercer los derechos | Pendiente (Q-18) |
| Plazo de conservación de los datos | Pendiente (Q-17) |
| Redacción de la leyenda sobre el órgano de control | A confirmar en la revisión legal; no se verificó contra la norma que la exige |

## Texto que ve el paciente

**Aviso de privacidad**

Para crear tu cuenta y gestionar tus turnos, [NOMBRE DEL CONSULTORIO], con domicilio en [DOMICILIO], guarda los datos que cargás en este formulario en su base de datos de pacientes.

**Qué datos pedimos.** Nombre y apellido, DNI, teléfono, correo electrónico, usuario y contraseña son obligatorios: sin ellos no podemos crear tu cuenta ni darte turnos en línea. La obra social es opcional.

**Para qué los usamos.** Para identificarte, darte y gestionar turnos, y avisarte por correo o por WhatsApp sobre tus turnos (confirmaciones, recordatorios y cambios). No los usamos para otra finalidad.

**Quién los ve.** El personal del consultorio que los necesita para atenderte. No los vendemos ni los compartimos para otros fines; los guardamos y enviamos a través de los proveedores de infraestructura que usa el consultorio (alojamiento de la base de datos y envío de correo).

**Tus derechos.** Podés pedir acceder a tus datos, corregirlos o que se supriman escribiendo a [CONTACTO]. El acceso es gratuito a intervalos no menores de seis meses, salvo que acredites un interés legítimo (Ley 25.326, artículo 14).

La Agencia de Acceso a la Información Pública, órgano de control de la Ley 25.326, atiende las denuncias y reclamos por el incumplimiento de las normas de protección de datos personales.

☐ Leí el aviso de privacidad y acepto que el consultorio trate mis datos para gestionar mis turnos.

## Leyenda del campo de notas de la ficha

Usá este campo solo para datos de gestión del turno. No cargues diagnósticos, tratamientos ni otros datos de salud.
