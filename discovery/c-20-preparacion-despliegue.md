# C-20 — Preparación del despliegue

Fecha: 2026-11-07. Informe de preparación; no es una propuesta OpenSpec ni acredita un despliegue probado.

## Arquitectura elegida

El usuario eligió una demostración académica con un servicio para la API y el frontend, PostgreSQL administrado y un disparador externo (DD-34). El requisito académico de stack completo sigue sin comprobarse (Q-29). El Dockerfile actual ya construye el frontend y lo copia a `/app/static`; Compose actual es para desarrollo y conserva un servicio frontend separado.

## Candidatos para la demostración

Como punto de partida se propone **Render Free para la aplicación, Neon Free para PostgreSQL y GitHub Actions para el disparador**, sujetos a comprobación en cuentas disponibles. Son candidatos, no decisiones de proveedor ni pruebas exitosas. Para correo se propone explorar Resend Free por HTTPS; depende de disponer de un dominio verificable y de adaptar el límite del sistema a 100 diarios y 3.000 mensuales. Si no hay dominio, hay que elegir otro proveedor viable, no usar una dirección de prueba para pacientes reales.

El disparador debe vivir en un repositorio y bajo un responsable definidos; el secreto debe residir en el almacén de secretos y rotarse con un procedimiento documentado. La desactivación de Actions tras inactividad en repositorios públicos y los retrasos posibles obligan a monitorear el último barrido. La opción no ofrece garantía de puntualidad. El requisito de medición de Q-27 no queda resuelto por elegir Neon.

La demostración no autoriza por sí sola a introducir datos reales de pacientes ni a publicar el enlace de uso del consultorio. Se recomienda usar datos ficticios en un proyecto descartable y separar la publicación para uso real, su revisión de privacidad y las verificaciones operativas.

## Opciones a verificar

| Decisión | Candidato y condiciones | Verificación pendiente |
|---|---|---|
| Q-24: host | Render Free permite servicio web, pero duerme tras 15 minutos, puede tardar alrededor de un minuto en despertar, ofrece 750 horas gratuitas mensuales y su documentación desaconseja producción. [Documentación](https://render.com/docs/free) | Viabilidad para el uso previsto, cuenta, límites, arranque, HTTPS y proxies; no seleccionado ni probado. |
| Q-23: correo | Render Free bloquea SMTP 25/465/587. Resend ofrece API HTTPS y límite gratuito de 100 correos por día y 3.000 por mes, inferior al tope actual de 500 diarios. [Render](https://render.com/docs/free), [Resend](https://resend.com/pricing) | Confirmar disponibilidad de dominio y DNS, implementar adaptador y ajustar límite si se elige; prueba real de entrega. |
| Q-25: disparador | GitHub Actions admite intervalos de cinco minutos; los workflows programados de repositorios públicos se desactivan tras 60 días sin actividad. [Programación](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax), [desactivación](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows). Cloudflare Workers es otra opción. | Elegir operador y plataforma, custodia y rotación del secreto, monitoreo y medir retrasos; no asumir puntualidad. |
| Q-26: extensión | Neon muestra `CREATE EXTENSION btree_gist` en un [ejemplo oficial](https://neon.com/blog/btree_gist). | Ejecutar la migración y comprobar exclusión en una instancia descartable del proveedor seleccionado. |
| Q-27: cuota | Neon publica 100 CU-h/mes por proyecto; 0,25 CU activos continuamente implicarían 180–186 CU-h en 30–31 días: cálculo estimado, no medición. [Fuente](https://neon.com/blog/neon-free-plan-1-gb-per-project). | Medir consumo y suspensión con el intervalo de barrido y conexiones reales; acordar mitigación y precisión aceptable si excede la cuota. |
| Q-29: consigna | Usuario eligió la arquitectura anterior. | Comprobar si la asignatura exige API, PostgreSQL, Redis y proceso persistente juntos; si lo exige, reevaluar alternativa Compose en VM. |

## Secuencia de preparación

1. Confirmar la consigna; identificar cuentas y dominio disponibles para la demostración, sin solicitar contraseñas por chat. El destino de demostración académica ya fue confirmado.
2. Elegir candidatos de host, correo, base y operador del disparador; verificar condiciones actuales, límites y acceso antes de comprometerlos.
3. En recursos descartables autorizados, probar `btree_gist`, migraciones, salida de correo, disparador y consumo medido de base. Documentar resultados y decisiones sin incluir secretos.
4. Resolver las preguntas de prioridad alta en la KB antes de crear la propuesta formal, conforme a la puerta de preguntas de `CHANGES.md`.
5. La propuesta deberá cubrir arranque y build de un origen, migraciones y semilla, secretos, proxies, copias y restauración, pruebas de extremo a extremo y revisión de datos del consultorio antes de publicar.

Los candidatos son exploratorios. No se crearon cuentas, no se configuraron servicios externos ni se verificó un despliegue.
