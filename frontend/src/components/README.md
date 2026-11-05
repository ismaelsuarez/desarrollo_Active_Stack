# Componentes de presentación

Los contenedores o páginas se ocupan de solicitar datos, decidir estados y manejar acciones. Los componentes de este directorio reciben contenido y callbacks por props: no consultan la API ni conservan sesiones. Así pueden reutilizarse y probarse por interacción visible.

- `Button` acepta las props nativas de un botón y `variant="primary" | "secondary"`; por defecto es `type="button"`. Un formulario debe usar `type="submit"` explícitamente.
- `TextField` acepta props nativas de `input`, `label` obligatorio y `hint` o `error` opcionales. Asocia etiqueta y descripción, combina `aria-describedby` externo y marca los errores con `aria-invalid`.
- `Notice` recibe `kind` (`info`, `success`, `warning` o `error`) y `children`; los errores son alertas y los demás mensajes se anuncian como estado.
- `PageTemplate` recibe `title`, `description` opcional y `children` y proporciona el área principal. Se usa una vez por página, evitando `main` anidados.

La presentación usa el acento aprobado `#2A9D8F` y controles nativos accesibles. Los nombres y mensajes los define el contenedor; no se deben transmitir tokens ni datos sensibles a mensajes o logs. Se deben contrastar las páginas finales con los mockups y comprobar teclado, foco y tamaños en navegador.
