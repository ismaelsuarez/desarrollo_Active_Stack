# Evidencia de verificación C-11

## Pruebas y ciclo TDD

Línea de base: frontend 2/2 y typecheck; backend 454 pruebas unitarias y 103 pruebas de autenticación, cuenta y API sobre PostgreSQL real. La aprobación de autenticación y seguridad quedó registrada en `design.md`.

| Tarea | Pruebas / capa | RED y GREEN | Triangulación y refactor |
|---|---|---|---|
| 2.1 | `frontend/src/proxy-config.test.ts`, unidad | Exportación de destino y proxy ausentes; implementación verde | Local, Compose y exclusión del entorno cliente: 3 casos |
| 2.2 | `backend/tests/api/test_spa_distribution.py`, HTTP | Deep link falló antes de agregar SPA; pasó después | Archivos, rutas API, 404 y métodos; corrección posterior del orden de middleware y aislamiento de tests |
| 2.3 | `backend/tests/infra/test_compose_contract.py`, imagen y HTTP | Contrato de build falló con contexto anterior; pasó al corregirlo | Imagen real, raíz, deep link, API y 404; CI corregida y 4 pruebas de contrato verdes |
| 3.1–3.2 | `frontend/src/api/client.test.ts`, unidad | Cliente ausente; implementación verde; reintento primero falló | 12 casos: credenciales, errores, validación, timeout, éxito tardío y límite; sin repetir escrituras |
| 3.3–3.4 | `frontend/src/auth/session.test.ts` y `provider.test.tsx`, unidad/React | Sesión y proveedor ausentes; implementación verde | Login, logout, rechazo, StrictMode, refresh concurrente, 401 y carreras entre cookie/login/logout; 12 casos |
| 4.1–4.2 | `frontend/src/shell/routes.test.tsx`, `layout.test.tsx` y `auth/guard.test.tsx`, React | Rutas, layout y guarda ausentes; implementación verde | Roles, acceso denegado, sesión ausente, carga, rutas directas y 404 |
| 4.3 | `frontend/src/components/ui.test.tsx`, React | Componentes ausentes; 3 casos verdes | 7 casos con etiquetas, estados e interacciones; refactor sin cambio funcional |
| 5.1–5.4 | `frontend/src/pages/public.test.tsx`, React | Páginas ausentes; 5 casos verdes | Registro, aviso, login, límites y enlaces; aviso de demora y formato legal agregados RED/GREEN, 21 casos |
| 6.1–6.2 | `frontend/src/account/AccountPage.test.tsx`, React | Pantalla y campo de teléfono ausentes; implementados en verde | Contraseña incorrecta, campos, roles, correo distinto/equivalente y conflicto: 16 casos |

Verificación final del 2026-11-05: frontend 82/82 pruebas, typecheck y build correctos; backend afectado 118/118 pruebas sobre PostgreSQL real. La suite combinada detectó y permitió corregir la pérdida de `request_id` del middleware y un aislamiento de imports en los tests SPA. No se registran como pruebas de producto las tareas administrativas de aprobación ni esta verificación de integración.

La imagen final reconstruida con el frontend completo se comprobó en un contenedor temporal: `/`, `/registro` y `/restablecer-password` devolvieron HTML 200; `/api/v1/health` devolvió JSON 200; una ruta API y un recurso inexistentes devolvieron 404. El contenedor de comprobación y el PostgreSQL temporal se detuvieron al finalizar.

## 7.2 — Sesión real a través del proxy

El 2026-11-05 se ejecutó una prueba con un cliente HTTP real contra Vite en `127.0.0.1:15173`, configurado para reenviar `/api` a una API FastAPI en un contenedor Docker, con PostgreSQL real y una base y usuario descartables. La base temporal se migró a `head` con Alembic y se inicializó con la semilla del proyecto. El cliente llamó exclusivamente al origen Vite y guardó las cookies en memoria; no se registraron valores de tokens ni credenciales.

- `POST /api/v1/auth/login`: 200; la cookie de refresh incluyó `HttpOnly`, `SameSite=Strict` y `Path=/api/v1/auth`.
- `GET /api/v1/auth/me`: 200 con el access token obtenido en login.
- `POST /api/v1/auth/refresh`: 200 y cookie distinta de la anterior.
- Se simuló una recarga con un cliente HTTP sin access token previo y con solo la cookie rotada: refresh 200, nueva rotación y `/auth/me` 200 con el nuevo access token.
- `POST /api/v1/auth/logout`: 200 y cookie de eliminación con `Max-Age=0`; reutilizar la última cookie de refresh devolvió 401.

La recarga se simuló mediante un cliente HTTP, no con la interfaz de un navegador; esta prueba verifica las cabeceras de cookie y el contrato real de la API a través del proxy, sin afirmar que el navegador haya ejecutado el flujo.

## 7.3 — Revisión visual parcial

El 2026-11-05 se comparó la implementación con los mockups aprobados y el sistema visual revisión 2. Se usó Edge mediante Chrome DevTools Protocol con vistas reales de 1440×900 y 390×844, Vite y API contra PostgreSQL aislado. Las capturas están en `mockups/verify/`: las terminadas en `-cdp.png` corresponden al primer recorrido y las terminadas en `-final.png` a las vistas recapturadas después de las correcciones. Los datos y cuentas utilizados fueron temporales.

- **Inspeccionados en ambos tamaños:** ingreso, registro con aviso obtenido de la API, recuperación, reenvío, verificación y confirmación sin token, restablecimiento sin token, página inexistente, redirección a ingreso sin sesión, espacios autenticados de paciente, recepción, profesional, administrador y administrativo, y cuenta de paciente y administrador. No se detectó desborde horizontal en las vistas medidas.
- **Diferencias corregidas durante la revisión:** la cuenta carecía de tarjeta y espaciado; la página inexistente carecía de márgenes; el aviso mostraba marcadores Markdown y una casilla textual junto a la casilla real. Se revisaron las capturas finales de esas tres vistas después de los ajustes.
- **Diferencia menor restante:** `GET /favicon.ico` responde 404 en el navegador. Las respuestas 401 de `/auth/refresh` al visitar sin cookie son esperadas. Una primera navegación rápida registró excepciones de promesas; al repetir las rutas con espera estable no se reprodujeron. No se verificaron todas las rutas y estados con consola limpia bajo todas las condiciones.
- **No inspeccionados visualmente:** estados de error de campo y credenciales, correo sin verificar, límite de intentos, servicio demorado, aviso no disponible o actualizado, enlaces válidos/usados/vencidos, resultado de cambio de contraseña/contacto, acceso denegado por rol y cierre no confirmado. Esos estados requieren revisión adicional en navegador; las pruebas automatizadas de comportamiento no sustituyen esa comparación visual.

Resultado: **diferencias / revisión visual parcial**. No se afirma coincidencia completa con todos los mockups ni verificación integral de accesibilidad.
