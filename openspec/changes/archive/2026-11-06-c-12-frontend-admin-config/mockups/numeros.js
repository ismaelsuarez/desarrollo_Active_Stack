// Los campos de ejemplo representan cantidades enteras, no notación científica.
document.querySelectorAll('input[type="number"]').forEach((input) => {
  input.addEventListener('keydown', (event) => {
    if (!event.ctrlKey && !event.metaKey && !event.altKey && (event.key === 'e' || event.key === 'E')) event.preventDefault();
  });
  input.addEventListener('paste', (event) => {
    if (!/^\d*$/.test(event.clipboardData.getData('text'))) event.preventDefault();
  });
  input.addEventListener('input', () => {
    if (/[eE]/.test(input.value)) input.value = '';
  });
});
