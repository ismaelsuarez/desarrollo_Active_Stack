# Verificación visual de correcciones

Fecha: 2026-11-09. Comparación del mockup aprobado `../estados.html` con la aplicación en Chromium, usando API simulada y datos ficticios. Se capturaron e inspeccionaron las siete pantallas en 390 × 844 y 1440 × 900. La prueba revisó errores de JavaScript, solicitudes fallidas y respuestas HTTP inesperadas; las respuestas 500/503 mostradas en los estados de error fueron simuladas intencionalmente.

## Diferencias

- Las diferencias mayores iniciales de distribución en reserva e inicio del paciente se corrigieron y volvieron a capturar e inspeccionar en ambos tamaños.
- **Menor — Mis turnos, ambos tamaños:** el mockup representa el reintento como enlace y añade «Ver detalle» ilustrativo; la implementación usa un botón de reintento y conserva las acciones reales de la pantalla. Reproducción: fallar `/publico/profesionales` y abrir `/mis-turnos`. Ver `turnos-parciales-*.png`.
- **Menor — Pantallas completas:** el mockup es una lámina de estados y no reproduce la cabecera ni todos los componentes previos de cada pantalla. Las capturas muestran la estructura real de la aplicación.

## Cobertura

Revisados: búsqueda y búsqueda al reprogramar, error de catálogo, turnos con información parcial y foco, restablecimiento incierto, inicio del paciente, indicador y error de WhatsApp. La revisión con lector de pantalla y la interacción de las demás variantes de rol no se automatizaron.
