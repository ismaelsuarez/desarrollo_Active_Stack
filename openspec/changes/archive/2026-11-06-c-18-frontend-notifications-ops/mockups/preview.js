document.addEventListener('click', (event) => {
  const target = event.target.closest('button');
  if (!target || target.disabled) return;
  const feedback = document.getElementById('feedback');
  if (target.hasAttribute('data-open')) {
    feedback.hidden = false;
    feedback.textContent = 'Ejemplo: en la aplicación se abrirá el enlace seguro devuelto por el servidor. Esta vista no abre WhatsApp.';
  } else if (target.hasAttribute('data-mark')) {
    feedback.hidden = false;
    feedback.textContent = 'Ejemplo: la marca se confirmará en el servidor. Esta vista no guarda cambios.';
  } else if (target.hasAttribute('data-demo')) {
    alert('Vista previa: esta acción es ilustrativa y no modifica datos.');
  }
});
