# Verificación visual de C-18

Sistema visual aprobado: revisión 2. Prueba: 2026-11-06 en Edge mediante Playwright con respuestas de API simuladas. Servidor temporal detenido al finalizar.

## Pantallas inspeccionadas

| Pantalla o estado | 390×844 | 1440×900 |
| --- | --- | --- |
| WhatsApp preparado | `mobile.png` | `desktop.png` |
| Correo fallido con fila | `correo-mobile.png` | `correo-desktop.png` |
| Correo vacío | `correo-vacio-mobile.png` | `correo-vacio-desktop.png` |
| Sin confirmar con fila | `turnos-mobile.png` | `turnos-desktop.png` |
| Detalle con acciones | `detalle-mobile.png` | `detalle-desktop.png` |
| Salud, barrido antiguo y alerta | `salud-mobile.png` | `salud-desktop.png` |
| Error de lectura | `error-mobile.png` | `error-desktop.png` |
| Ventana bloqueada | `popup-mobile.png` | `popup-desktop.png` |
| Conflicto de envío | `conflicto-mobile.png` | `conflicto-desktop.png` |
| Resultado de escritura incierto | `incierto-mobile.png` | `incierto-desktop.png` |
| Carga de notificaciones | `carga-mobile.png` | `carga-desktop.png` |
| Salud sin barrido | `salud-sin-barrido-mobile.png` | `salud-sin-barrido-desktop.png` |
| Error de salud | `salud-error-mobile.png` | `salud-error-desktop.png` |

No se observó desbordamiento horizontal en las pantallas principales en ambos tamaños. Las capturas son simuladas y no validan datos ni permisos del servidor en vivo.

## Diferencias frente al mockup

- **Diferencia aceptada por el usuario (2026-11-06) — navegación, ambos tamaños:** el mockup presenta WhatsApp, correo, turnos y salud como secciones de un mismo documento. La implementación usa pestañas para las bandejas y rutas separadas para turnos y salud, siguiendo la decisión 1 de `design.md`. Reproducción: abrir Notificaciones y elegir «Sin confirmar» o «Estado operativo». Las secciones no aparecen todas al desplazarse en una sola página. El usuario eligió mantener las páginas separadas después de conocer esta diferencia.
- **Menor — detalle, ambos tamaños:** se reutiliza el detalle existente; muestra «Cerrar» y un campo opcional de motivo, mientras el mockup usa «Volver a turnos» y dispone las acciones de otra manera. Reproducción: Sin confirmar → Ver turno y acciones.
- **Menor — salud, ambos tamaños:** las edades se expresan en segundos y la fecha del último barrido se muestra en lugar del texto relativo del mockup. La alerta depende del valor del servidor.

## Pendiente de inspección visual

- Confirmar con API real y recorrer todas las interacciones por teclado. La prueba de consola y red instrumentó notificaciones, correo, turnos y salud en los recorridos normales, sin errores; las respuestas 409 y 500 y el corte de red en los escenarios de error fueron simulados intencionalmente. No se inspeccionaron los estados de carga de cada pantalla.
- No se afirma coincidencia visual completa; la diferencia de navegación fue aceptada por el usuario y los estados y comprobaciones descritos arriba siguen pendientes.

## Ampliación de revisión (2026-11-06)

Se inspeccionaron las doce capturas de ventana bloqueada, conflicto, escritura incierta, carga de notificaciones, salud sin barridos y error de salud, cada una en ambos tamaños. Las pruebas Playwright en Edge finalizaron 8/8 con respuestas simuladas; el servidor temporal se detuvo. En las capturas no se observaron superposiciones. Se detectó y corrigió que el enlace alternativo permanecía visible al cambiar el estado; las capturas de conflicto e incertidumbre se regeneraron e inspeccionaron tras la corrección.
