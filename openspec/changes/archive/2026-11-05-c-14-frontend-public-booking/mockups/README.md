# Mockups C-14

Approval: approved (2026-11-05, by user; enlaces y vistas de registro e ingreso corregidos)

## Brief

Paciente en celular o escritorio: consultar horarios sin sesión, ingresar o registrarse, revisar y confirmar una reserva y gestionar sus turnos. Incluye selección, formularios ilustrativos de registro e ingreso, reserva exitosa, lista, confirmación, cancelación, reprogramación, conflicto, ausencia de horarios, espera, resultado incierto, cuenta sin habilitar, límite y turno liberado. Los datos, teléfono, dirección y marca comercial son de ejemplo o `(TBD)`.

Fuente: propuesta, especificación y diseño de C-14; sistema visual aprobado revisión 2 (`design-system/`). El diseño importa los tokens, logo provisional y `brand.js` compartidos sin duplicarlos. Los botones y enlaces son referencias visuales; no ejecutan operaciones reales.

## Revisión manual

Abrir [index.html](index.html) en Edge u otro navegador y usar los enlaces superiores para recorrer cada vista. Revisar en una ventana de 390 × 844 y otra de 1440 × 900, incluyendo desplazamiento, foco de teclado, legibilidad, los mensajes y las acciones. No se generaron capturas: Playwright no pudo iniciar porque el navegador Chrome configurado no está instalado. No se afirma inspección renderizada automatizada.

El listado de horarios de reprogramación es orientativo: el servidor verifica el cambio y el turno anterior se conserva ante rechazo. Esta limitación merece revisión de producto.
